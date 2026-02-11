"""
对话生成服务
协调整个对话流程，整合意图识别、问题理解、RAG检索和LLM生成
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from volcenginesdkarkruntime import Ark

from ...core.config import settings
from ...core.database import AsyncSessionLocal
from ...models.chat import ChatRequest, ChatResponse, RetrievedDoc, MessageRole
from ...models.conversation import Conversation, Message
from ...models.intent import IntentClassification
from ...models.question import QuestionAnalysis

from .intent_service import intent_service
from .question_analyzer import question_analyzer
from .rag_service import rag_service

import logging

logger = logging.getLogger(__name__)

class ChatService:
    """对话生成服务类"""

    def __init__(self):
        """初始化对话服务"""
        # 初始化豆包LLM客户端
        self.client = Ark(api_key=settings.LLM_API_KEY)
        self.model = settings.LLM_MODEL

        # 子服务
        self.intent_service = intent_service
        self.question_analyzer = question_analyzer
        self.rag_service = rag_service

        logger.info(f"对话生成服务初始化完成，使用模型：{self.model}")

    async def generate_response(
            self,
            request: ChatRequest,
            user_id: str = None
    ) -> ChatResponse:
        """
        生成对话回复（核心方法）

        流程：
        1. 获取或创建对话
        2. 保存用户消息到数据库
        3. 意图识别
        4. 问题理解
        5. RAG检索
        6. LLM生成回复
        7. 保存AI消息到数据库
        8. 返回完整响应

        Args:
            request: 聊天请求
            user_id: 用户ID（可选）

        Returns:
            聊天响应
        """
        async with AsyncSessionLocal() as db:
            try:
                # 1. 获取或创建对话
                conversation, is_new_conversation = await self._get_or_create_conversation(
                    db,
                    request.conversation_id,
                    user_id,
                    request.content
                )

                # 2. 保存用户消息
                user_message = await self._save_user_message(
                    db,
                    conversation.id,
                    request.content
                )

                logger.info(
                    f"开始处理对话: conversation_id={conversation.id}, "
                    f"is_new={is_new_conversation}, "
                    f"content={user_message.content[:50]}..."
                )

                # 3. 意图识别
                logger.info("步骤1：意图识别")
                intent_result = self.intent_service.classify_intent(
                    query=request.content,
                    use_cache=True
                )
                logger.info(f"意图识别完成：is_legal={intent_result.is_legal_related}, "
                            f"category={intent_result.legal_category}, "
                            f"confidence={intent_result.confidence}")

                # 4. 问题理解
                logger.info("步骤2：问题理解")
                analysis_result = self.question_analyzer.analyze_question(
                    query=request.content,
                    intent_result=intent_result
                )
                logger.info(f"问题理解完成：core_issue={analysis_result.core_issue[:50]}")

                # 5. RAG检索（仅当是法律相关问题时才检索）
                retrieved_docs = []
                if intent_result.is_legal_related:
                    logger.info("步骤3：RAG检索")
                    # 使用优化后的查询进行检索
                    search_query = analysis_result.query_for_retrieval or request.content
                    retrieved_docs = self.rag_service.retrieve_relevant_docs(
                        query=search_query,
                        top_k=request.top_k,
                        threshold=0.6,                  # 检索阈值
                        enable_rerank=True,
                        enable_deduplication=True
                    )
                    logger.info(f"RAG检索完成：检索到{len(retrieved_docs)}个相关文档")
                else:
                    logger.info("步骤3：跳过RAG检索（非法律问题）")

                # 6. LLM生成回复
                logger.info("步骤4：LLM生成回复")
                # 获取对话历史（用于上下文）
                conversation_history = await self._get_conversation_history(
                    db,
                    conversation.id,
                    max_messages=6,             # 保留最近3轮对话
                    exclude_latest=True         # 排除最新消息
                )

                # 生成回复
                llm_response, tokens_used, thinking_process = await self._generate_llm_response(
                    query=request.content,
                    conversation_history=conversation_history,
                    intent=intent_result,
                    analysis=analysis_result,
                    retrieved_docs=retrieved_docs
                )
                logger.info(f"LLM生成完成：tokens_used={tokens_used}, "
                            f"response_length={len(llm_response)}")

                #7. 保存AI消息
                ai_message = await self._save_assistant_message(
                    db,
                    conversation.id,
                    llm_response,
                    tokens_used,
                    retrieved_docs,
                    intent_result,
                    analysis_result
                )

                # 8. 构建响应
                response = ChatResponse(
                    message_id=str(ai_message.id),
                    conversation_id=str(conversation.id),
                    content=llm_response,
                    intent=intent_result,
                    analysis=analysis_result,
                    retrieved_docs=retrieved_docs,
                    tokens_used=tokens_used,
                    thinking_process=thinking_process if request.include_thinking else None,
                    created_at=ai_message.created_at
                )

                #更新对话的最后更新时间
                conversation.updated_at = datetime.now()
                await db.commit()

                logger.info(f"对话处理完成：message_id={ai_message.id}")
                return response

            except Exception as e:
                logger.error(f"生成回复失败：{e}", exc_info=True)
                await db.rollback()
                raise

    async def _get_or_create_conversation(
            self,
            db: AsyncSessionLocal,
            conversation_id: Optional[str],
            user_id: Optional[str],
            first_message: str
    ) -> tuple[Conversation, bool]:
        """
        获取或创建对话

        Args:
            db: 数据库会话
            conversation_id: 对话ID（可选）
            user_id: 用户ID
            first_message: 首条消息内容（用户生成标题）

        Returns:
            (对话对象，是否为新创建)
        """
        if conversation_id:
            # 获取已有对话
            conversation = await db.get(Conversation, conversation_id)
            if conversation:
                # 如果对话标题是默认值或为空，生成新标题
                if not conversation.title or conversation.title in ['新对话', '新会话']:
                    try:
                        title = await self._generate_conversation_title(first_message)
                        conversation.title = title
                        await db.flush()
                        logger.info(f"更新对话标题：{conversation_id} => {title}")
                    except Exception as e:
                        logger.warning(f"生成对话标题失败：{e}, 保持原标题")

                return conversation, False

        # 生成对话标题
        title = await self._generate_conversation_title(first_message)

        # 创建新对话
        conversation = Conversation(
            user_id=str(uuid4()) if not user_id else user_id,            # 如果没有user_id, 生成临时ID
            title=title,
            description="",
            is_archived=False
        )
        db.add(conversation)
        await db.flush()

        logger.info(f"创建新对话：conversation_id={conversation.id}")
        return conversation, True

    async def _generate_conversation_title(
            self,
            first_message: str
    ) -> str:
        """
        使用LLM生成对话标题

        Args:
            first_message: 首条消息内容

        Returns:
            生成的对话标题（10-30字）
        """
        try:
            # 构建提示词
            prompt = f"""请根据以下用户问题，生成一个简洁的对话标题。
            
            要求：
            1. 标题长度：10-20个汉字
            2. 简洁明了：概括问题的核心内容
            3. 专业准确：使用专业但易懂的表达
            4. 不要标点符号
            
            用户问题：{first_message}
            
            请只输出标题，不要其他内容。
            """

            # 调用LLM
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=50
            )

            # 提取标题
            title = resp.choices[0].message.content.strip()

            # 清理标题（去除多余空格、标点等）
            title = title.replace("\n", "").strip()
            title = title[:30]          # 确保不超过30字

            logger.info(f"LLM生成对话标题：{title}")
            return title

        except Exception as e:
            logger.warning(f"LLM生成标题失败：{e}，使用fallback方案")
            # Fallback：截取前30个字符
            return first_message[:30]

    async def _save_user_message(
            self,
            db: AsyncSessionLocal,
            conversation_id: str,
            content: str
    ) -> Message:
        """
        保存用户消息

        Args:
            db: 数据库会话
            conversation_id: 对话ID
            content: 消息内容

        Returns:
            消息对象
        """
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
            tokens_used=0
        )
        db.add(message)
        await db.flush()

        return message

    async def _save_assistant_message(
            self,
            db: AsyncSessionLocal,
            conversation_id: str,
            content: str,
            tokens_used: int,
            retrieved_docs: List[RetrievedDoc],
            intent: IntentClassification,
            analysis: QuestionAnalysis
    ) -> Message:
        """
        保存AI助手消息

        Args:
            db: 数据库会话
            conversation_id: 对话ID
            content: 消息内容
            tokens_used: 使用的token数
            retrieved_docs: 检索到的文档
            intent: 意图分类结果
            analysis: 问题分析结果

        Returns:
            消息对象
        """
        # 构建元数据
        meta_data = {
            "intent": intent.model_dump(),
            "analysis": analysis.model_dump(),
            "retrieved_docs_count": len(retrieved_docs),
            "retrieved_docs": [doc.model_dump() for doc in retrieved_docs[:5]]      # 只保留前5个
        }

        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            tokens_used=tokens_used,
            meta_data=meta_data
        )
        db.add(message)
        await db.flush()

        return message

    async def _get_conversation_history(
            self,
            db: AsyncSessionLocal,
            conversation_id: str,
            max_messages: int = 10,
            exclude_latest: bool = True
    ) -> List[Dict[str, str]]:
        """
        获取对话历史

        Args:
            db: 数据库会话
            conversation_id: 对话ID
            max_messages: 最大消息数
            exclude_latest: 是否排除最新一条消息（默认排除，因为最新消息会单独处理）

        Returns:
            对话历史列表 [{"role": "user", "content": "..."}, ...]
        """
        # 如果需要排除最新消息，多查一条
        limit = max_messages + 1 if exclude_latest else max_messages

        # 查询对话的消息
        from sqlalchemy import select, desc
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()

        # 转换为列表并反转（按时间正序）
        history = [
            {"role": "user", "content": msg.content} for msg in reversed(messages)
        ]

        # 如果排除最新消息，去掉最后一条（即最新的一条）
        if exclude_latest and history:
            history = history[:-1]

        logger.debug(f"获取对话历史：{len(history)}条消息(exclude_latest={exclude_latest})")
        return history

    async def _generate_llm_response(
            self,
            query: str,
            conversation_history: List[Dict[str, str]],
            intent: IntentClassification,
            analysis: QuestionAnalysis,
            retrieved_docs: List[RetrievedDoc],
            include_thinking: bool = False                  # 暂时不适用这个参数，后续有时间再添加思考过程
    ) -> tuple[str, int, Optional[str]]:
        """
        调用LLM生成回复

        Args:
            query: 用户查询
            conversation_history: 对话历史
            intent: 意图分类结果
            analysis: 问题分析结果
            retrieved_docs: 检索到的文档
            include_thinking: 是否包含思考过程（暂未实现，后续添加思考过程）

        Returns:
            (回复内容, 使用的token数, 思考过程)
        """
        # 如果用户要求思考过程，记录日志说明暂不支持
        if include_thinking:
            logger.warning("当前LLM不支持真实思考链输出")

        # 构建提示词
        system_prompt = self._build_system_prompt(intent, analysis)

        # 构建索引上下文
        context = self._build_retrieval_context(retrieved_docs)

        # 构建完整的消息列表
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # 添加对话历史
        for msg in conversation_history:       # 排除当前用户消息（已单独处理）
            messages.append({"role": msg["role"], "content": msg["content"]})

        # 添加用户查询
        user_prompt = self._build_user_prompt(query, context)
        messages.append({"role": "user", "content": user_prompt})

        # 调用LLM生成回复
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=False
            )

            # 提取回复
            content = resp.choices[0].message.content
            tokens_used = resp.usage.total_tokens if hasattr(resp, "usage") else len(content.split())

            logger.debug(f"LLM回复生成成功：content_length={len(content)}, tokens={tokens_used}")
            return content, tokens_used, None           # 返回None作为thinking_process

        except Exception as e:
            logger.error(f"LLM生成失败：{e}", exc_info=True)
            raise

    def _build_system_prompt(
            self,
            intent: IntentClassification,
            analysis: QuestionAnalysis
    ) -> str:
        """
        构建系统提示词

        Args:
            intent: 意图分类结果
            analysis: 问题分析结果

        Returns:
            系统提示词
        """
        legal_categories = {
            "民事": "民法、婚姻、继承、物权、侵权、合同等民事法律问题",
            "刑事": "刑法、刑事诉讼、刑事辩护等刑事法律问题",
            "商事": "公司法、证券、金融、破产等商事法律问题",
            "行政": "行政处罚、行政复议、行政诉讼等行政法律问题",
            "劳动": "劳动合同、工资福利、工伤、劳动争议等劳动法问题",
            "房产": "房屋买卖、租赁、物业管理、继承等房地产法律问题",
            "知识产权": "专利、商标、著作权、不正当竞争等知识产权问题",
            "婚姻家庭": "结婚、离婚、抚养、赡养、收养等婚姻家庭法律问题",
            "侵权责任": "人身损害、财产损害、环境污染等侵权责任问题",
            "合同纠纷": "合同订立、履行、违约、解除等合同法律问题",
            "其他": "其他法律相关问题"
        }

        category_description = legal_categories.get(
            intent.legal_category,
            "法律相关问题"
        )

        # 构建分析信息部分
        analysis_info = ""
        if analysis:
            # 法律要素
            if analysis.legal_elements:
                elements_text = "、".join(analysis.legal_elements)
                analysis_info += f"\n- 涉及的法律要素：{elements_text}"

            # 关键实体
            if analysis.key_entities:
                entities_text = "、".join(analysis.key_entities)
                analysis_info += f"\n- 关键实体：{entities_text}"

            # 缺失信息
            if analysis.missing_info:
                missing_text = "、".join(analysis.missing_info)
                analysis_info += f"\n- 需要补充的信息：{missing_text}"
                analysis_info += "\n- 提示：如果用户未提供这些信息，请在回答中询问用户"

        prompt = f"""你是一个专业的法律咨询助手，专门为用户提供法律建议和解答
        
        ## 你的角色
        - 专业、准确、客观的法律顾问
        - 熟悉中国法律法规和司法解释
        - 注重引用法律条文和实际案例
        
        ## 当前咨询领域
        - 法律领域：{intent.legal_category}
        - 领域描述：{category_description}
        - 置信度：{intent.confidence:.2%}
        {analysis_info}
        
        ## 回答要求
        1. **针对性**：针对"{analysis.core_issue if analysis else '用户问题'}"进行回答
        2. **专业性**：使用专业的法律术语，避免口语化表达
        3. **准确性**：引用具体的法律条文和条款号
        4. **实用性**：提供可操作的建议和解决方案
        5. **完整性**：全面回答问题，避免遗漏重要信息
        6. **责任性**：在回答中添加免责声明
        7. **引用来源**：明确标注引用的法律条文和检索文档
        
        ## 回答结构建议
        1. 先给出核心结论
        2. 引用相关法律条文
        3. 解释法律条文适用性
        4. 提供具体操作建议
        5. 提醒注意事项
        6. 添加免责声明
        
        ## 免责声明模板
        在回答结尾添加：
        > 注：以上内容仅供参考，不构成法律意见。具体案件请咨询专业律师。
        
        ## 如果用户提问非法律问题
        礼貌地告知用户你只能回答法律相关问题，并引导用户提出法律问题。        
        """
        return prompt

    def _build_user_prompt(
            self,
            query: str,
            context: str
    ) -> str:
        """
        构建用户提示词

        Args:
            query: 用户查询
            context: 检索上下文

        Returns:
            用户提示词
        """
        if context:
            prompt = f"""## 用户问题
            {query}
            
            ## 相关法律资料
            {context}
            
            ## 请根据以上资料回答用户的问题，并：
            1. 引用具体的法律条文
            2. 提供实用的建议
            3. 说明使用的条件
            4. 添加免责声明
            """
        else:
            prompt = f"""## 用户问题
            {query}
            
            ## 请根据你的法律知识回答用户的问题，并：
            1. 引用相关的法律条文
            2. 提供实用的建议
            3. 添加免责声明
            """
        return prompt

    def _build_retrieval_context(
            self,
            retrieved_docs: List[RetrievedDoc]
    ) -> str:
        """
        构建检索上下文

        Args:
            retrieved_docs: 检索到的文档列表

        Returns:
            格式化的上下文字符串
        """
        if not retrieved_docs:
            return "未检索到相关法律资料。"

        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            context_part = f"""
            ### 资料来源{i}
            **文档标题**：{doc.document_title}
            **相似度**：{doc.score:.2%}
            **内容片段**：
            {doc.chunk_content}
            """

            context_parts.append(context_part)

        return "\n".join(context_parts)

    async def get_conversation(
            self,
            conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取对话详情

        Args:
            conversation_id: 对话ID

        Returns:
            对话详情（包含消息列表和用户信息）
        """
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            # 获取对话（预加载用户）
            stmt = (
                select(Conversation)
                .options(selectinload(Conversation.user))  # 预加载用户
            )
            conversation = await db.execute(
                stmt.where(Conversation.id == conversation_id)
            )
            conversation = conversation.scalar_one_or_none()

            if not conversation:
                return None

            # 获取消息列表
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
            )
            result = await db.execute(stmt)
            messages = result.scalars().all()

            # 构建响应
            return {
                "id": str(conversation.id),
                "user_id": str(conversation.user_id),
                "user_name": conversation.user.display_name,
                "title": conversation.title,
                "description": conversation.description,
                "is_archived": conversation.is_archived,
                "message_count": len(messages),
                "last_message_at": messages[-1].created_at if messages else None,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "messages": [
                    {
                        "id": str(msg.id),
                        "role": msg.role,
                        "content": msg.content,
                        "tokens_used": msg.tokens_used,
                        "meta_data": msg.meta_data,
                        "created_at": msg.created_at
                    }
                    for msg in messages
                ]
            }

    async def get_user_conversations(
            self,
            user_id: str = None,
            limit: int = 20,
            offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取用户的对话列表

        如果 user_id 为 None，则返回所有用户的对话；否则返回指定用户的对话

        Args:
            user_id: 用户ID
            limit: 返回数量
            offset: 偏移量

        Returns:
            对话列表
        """
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, desc
            from sqlalchemy.orm import selectinload

            # 查询对话列表，预加载消息关系
            stmt = (
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .options(selectinload(Conversation.user))
                .where(Conversation.is_archived == False)
            )

            # 如果指定了user_id，添加用户过滤条件
            if user_id is not None:
                stmt = stmt.where(Conversation.user_id == user_id)

            # 添加排序和分页
            stmt = stmt.order_by(desc(Conversation.updated_at)).limit(limit).offset(offset)

            result = await db.execute(stmt)
            conversations = result.scalars().all()

            # 构建响应
            return [
                {
                    "id": str(conv.id),
                    "user_id": str(conv.user_id),
                    "user_name": conv.user.display_name,
                    "title": conv.title,
                    "description": conv.description,
                    "is_archived": conv.is_archived,
                    "message_count": len(conv.messages),
                    "last_message_at": conv.messages[-1].created_at if conv.messages else None,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at
                }
                for conv in conversations
            ]

    async def delete_conversation(
            self,
            conversation_id: str
    ) -> bool:
        """
        删除对话

        Args:
            conversation_id: 对话ID

        Returns:
            是否删除成功
        """
        async with AsyncSessionLocal() as db:
            # 获取对话
            conversation = await db.get(Conversation, conversation_id)
            if not conversation:
                return False

            # 删除对话（消息会级联删除）
            await db.delete(conversation)
            await db.commit()

            logger.info(f"删除对话：conversation_id={conversation.id}")
            return True

    async def generate_response_stream(
            self,
            request: ChatRequest,
            user_id: str = None
    ):
        """
         生成对话回复（流式版本）

        流程：
        1. 获取或创建对话
        2. 保存用户消息到数据库
        3. 意图识别
        4. 问题理解
        5. RAG检索
        6. LLM流式生成回复
        7. 保存AI消息到数据库
        8. 流式返回响应

        Args:
            request: 聊天请求
            user_id: 用户ID（可选）

        Yields:
            流式响应数据（JSON字符串）
        """
        async with AsyncSessionLocal() as db:
            import json
            try:
                from asyncio import sleep

                # 1. 获取或创建对话
                conversation, is_new_conversation = await self._get_or_create_conversation(
                    db,
                    request.conversation_id,
                    user_id,
                    request.content
                )

                # 2. 保存用户消息
                user_message = await self._save_user_message(
                    db,
                    conversation.id,
                    request.content
                )

                logger.info(
                    f"开始流式处理对话: conversation_id={conversation.id}, "
                    f"is_new={is_new_conversation}"
                )

                # 3. 意图识别
                logger.info("步骤1：意图识别")
                intent_result = self.intent_service.classify_intent(
                    query=request.content,
                    use_cache=True
                )

                # 发送意图结果
                yield f"data: {json.dumps({'type': 'intent', 'data': intent_result.model_dump()})}\n\n"

                # 4. 问题理解
                logger.info("步骤2：问题理解")
                analysis_result = self.question_analyzer.analyze_question(
                    query=request.content,
                    intent_result=intent_result
                )

                # 发送问题分析结果
                yield f"data: {json.dumps({'type': 'analysis', 'data': analysis_result.model_dump()})}\n\n"

                # 5. RAG检索
                retrieved_docs = []
                if intent_result.is_legal_related:
                    logger.info("步骤3：RAG检索")
                    search_query = analysis_result.query_for_retrieval or request.content
                    retrieved_docs = self.rag_service.retrieve_relevant_docs(
                        query=search_query,
                        top_k=request.top_k,
                        threshold=0.6,
                        enable_rerank=True,
                        enable_deduplication=True
                    )

                    # 发送检索结果
                    yield f"data: {json.dumps({'type': 'retrieved_docs', 'data': [doc.model_dump() for doc in retrieved_docs]})}\n\n"
                else:
                    logger.info("步骤3：跳过RAG检索（非法律问题）")
                    yield f"data: {json.dumps({'type': 'retrieved_docs', 'data': []})}\n\n"

                # 6. LLM流式生成回复
                logger.info("步骤4：LLM流式生成回复")

                # 获取对话历史
                conversation_history = await self._get_conversation_history(
                    db,
                    conversation.id,
                    max_messages=6,
                    exclude_latest=True
                )

                # 构建完整回复内容
                full_response = ""
                tokens_used = 0

                # 构建prompt
                system_prompt = self._build_system_prompt(intent_result, analysis_result)
                context = self._build_retrieval_context(retrieved_docs)
                user_prompt = self._build_user_prompt(request.content, context)

                messages = [
                    {"role": "system", "content": system_prompt}
                ]
                for msg in conversation_history:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": user_prompt})

                # 发送开始标记
                yield f"data: {json.dumps({'type': 'start'})}\n\n"

                # 调用LLM流式生成
                try:
                    resp_stream = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2000,
                        stream=True             # 启用流式
                    )

                    # 逐块返回内容
                    for chunk in resp_stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content

                            # 发送内容块
                            yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"

                    # 获取token使用量
                    tokens_used = len(full_response.split())

                    # 发送结束标记
                    yield f"data: {json.dumps({'type': 'done', 'tokens_used': tokens_used})}\n\n"

                except Exception as e:
                    logger.error(f"LLM流式生成失败：{e}", exc_info=True)
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    raise

                # 7. 保存AI消息到数据库
                logger.info("步骤5：保存AI消息")
                ai_message = await self._save_assistant_message(
                    db,
                    conversation.id,
                    full_response,
                    tokens_used,
                    retrieved_docs,
                    intent_result,
                    analysis_result
                )

                # 更新对话时间
                conversation.updated_at = datetime.now()
                await db.commit()

                logger.info(f"流式对话处理完成：message_id={ai_message.id}")

            except Exception as e:
                logger.error(f"流式生成回复失败{e}", exc_info=True)
                await db.rollback()
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                raise

# 创建全局实例
chat_service = ChatService()