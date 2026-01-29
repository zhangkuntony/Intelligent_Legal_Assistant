"""
问题理解与分析服务
深度分析用户问题，提取关键信息、法律要素，生成优化的检索查询
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from volcenginesdkarkruntime import Ark

from ...core.config import settings
from ...models.question import QuestionAnalysis, EntityExtraction
from .intent_service import IntentService

import json
import logging
import re

logger = logging.getLogger(__name__)

class QuestionAnalyzer:
    """问题理解与分析服务类"""

    def __init__(self, intent_service: IntentService = None):
        """
        初始化问题理解服务

        Args:
            intent_service: 意图识别服务实例（可选，默认使用全局实例）
        """
        # 初始化豆包LLM客户端
        self.client = Ark(api_key=settings.LLM_API_KEY)
        self.model = settings.LLM_MODEL

        # 意图识别服务（延迟导入以避免循环依赖）
        if intent_service is None:
            from .intent_service import intent_service as default_intent_service
            self.intent_service = default_intent_service
        else:
            self.intent_service = intent_service

        # 实体提取缓存
        self._entity_cache: Dict[str, tuple] = {}

        # 分析结果缓存
        self._analysis_cache: Dict[str, tuple] = {}

        # 法律关键词字典
        self._legal_keywords = self._load_legal_keywords()

        # 实体类型模式
        self._entity_patterns = self._load_entity_patterns()

        logger.info(f"问题理解服务初始化完成，使用模型：{self.model}")

    def _load_legal_keywords(self) -> Dict[str, List[str]]:
        """
        加载法律关键词字典

        Returns:
            关键词字典 {类别: [关键词列表]}
        """
        return {
            "主体": ["公司", "企业", "个人", "自然人", "法人", "用人单位", "劳动者", "雇主", "员工"],
            "客体": ["财产", "房屋", "土地", "货物", "服务", "知识产权", "股权", "债券"],
            "行为": ["签订", "解除", "违约", "侵权", "欺诈", "拖欠", "拒绝", "逃避"],
            "权利": ["赔偿", "补偿", "支付", "履行", "违约金", "利息", "分红"],
            "义务": ["支付", "交付", "保密", "竞业禁止", "通知"],
            "法律关系": ["劳动关系", "合同关系", "买卖关系", "租赁关系", "合作关系"],
            "法律文书": ["合同", "协议", "遗嘱", "委托书", "授权书", "通知书"],
        }

    def _load_entity_patterns(self) -> Dict[str, re.Pattern]:
        """
        加载实体识别正则表达式模式

        Returns:
            实体模式字典 {类型: 正则表达式}
        """
        return {
            "date": re.compile(
                r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?|'
                r'\d{1,2}[-/]\d{1,2}[-/]\d{4}|'
                r'今年|前年|本月|上个月|去年|明天|后天|下周'
            ),
            "money": re.compile(
                r'\d+(\.\d+)?[万元千]|'
                r'¥\d+(\.\d+)?|'
                r'\$\d+(\.\d+)?|'
                r'\d+元'
            ),
            "phone": re.compile(r'1[3-9]\d{9}'),
            "email": re.compile(r'\w+@\w+\.\w+'),
            "id_card": re.compile(r'\d{17}[\dXx]'),
            "company": re.compile(r'\S{2,20}(公司|集团|有限公司|股份有限公司|企业)'),
        }

    def _get_cache_key(self, query: str, context: List[Dict] = None) -> str:
        """
        生成缓存键

        Args:
            query: 用户查询
            context: 对话上下文

        Returns:
            缓存键
        """
        # 如果有上下文，将上下文也纳入缓存键
        if context:
            context_hash = hash(str(context[-2:]))          # 只使用最近2轮对话
            return f"analysis:{hash(query.strip().lower())}:{context_hash}"
        return f"analysis:{hash(query.strip().lower())}"

    def _get_from_cache(self, cache_key: str) -> Optional[QuestionAnalysis]:
        """
        从缓存获取分析结果

        Args:
            cache_key: 缓存键

        Returns:
            缓存的分析结果，如果不存在则返回None
        """
        if cache_key in self._analysis_cache:
            result, timestamp = self._analysis_cache[cache_key]
            # 缓存有效期1小时
            if datetime.now() - timestamp < timedelta(hours=1):
                logger.debug(f"从缓存获取问题分析结果：{cache_key}")
                return result
            else:
                # 缓存过期，删除
                del self._analysis_cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, result: QuestionAnalysis):
        """
        设置缓存

        Args:
            cache_key: 缓存键
            result: 问题分析结果
        """
        self._analysis_cache[cache_key] = (result, datetime.now())

    def _extract_entities_nlp(self, query: str) -> List[EntityExtraction]:
        """
        使用NLP规则提取实体

        Args:
            query: 用户查询

        Returns:
            实体提取结果列表
        """
        entities = []

        # 尝试匹配各种实体类型
        for entity_type, pattern in self._entity_patterns.items():
            for match in pattern.finditer(query):
                entity_value = match.group()

                if entity_value:
                    entities.append(EntityExtraction(
                        entity_type=entity_type,
                        entity_value=entity_value,
                        confidence=0.8
                    ))

        logger.debug(f"NLP规则提取到{len(entities)}个实体")
        return entities

    def _extract_legal_elements(self, query: str) -> List[str]:
        """
        提取法律要素

        Args:
            query: 用户查询

        Returns:
            法律要素列表
        """
        elements = []

        # 查找匹配的法律关键词
        for category, keywords in self._legal_keywords.items():
            for keyword in keywords:
                if keyword in query:
                    if keyword not in elements:
                        elements.append(keyword)

        # 添加类别
        categories_found = [
            category for category, keywords in self._legal_keywords.items()
            if any(kw in query for kw in keywords)
        ]
        elements.extend(categories_found)

        logger.debug(f"提取到{len(elements)}个法律要素：{elements}")
        return elements

    def _build_analysis_prompt(self, query: str, context: List[Dict] = None, intent: str = None) -> str:
        """
        构建问题分析提示词

        Args:
            query: 用户查询
            context: 对话上下文
            intent: 意图识别结果

        Returns:
            提示词
        """
        context_str = ""
        if context and len(context) > 0:
            context_str = "\n## 对话上下文：\n"
            for msg in context[-3:]:            # 只使用最近3轮对话
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                role_zh = "用户" if role == 'user' else "助手"
                context_str += f"- {role_zh}: {content}\n"
            context_str += "\n"

        intent_str = ""
        if intent:
            intent_str = f"\n## 意图识别：\n{intent}\n\n"

        prompt = f"""
        你是一个专业的法律问题分析专家。你的任务是深度分析用户的问题，提取核心信息、法律要素，并生成优化的检索查询。
        
        {context_str}{intent_str}
        ## 当前用户输入：
        {query}
        
        ## 任务要求：
        1. 识别用户问题的核心诉求（用简洁的一句话概括）
        2. 提取法律要素（如：主体、客体、法律行为、权利义务等）
        3. 提取关键实体（人名、机构名、时间、金额等）
        4. 生成优化的检索查询（用于在法律文档库中检索相关信息，应该包含多个相关关键词）
        5. 识别缺失的关键信息（哪些信息对于完整回答问题是必要的，但用户没有提供）
        
        ## 分析思路：
        - 首先理解用户想要解决什么问题
        - 识别涉及的法律关系和法律概念
        - 提取具体的主体、客体、行为、时间、地点等要素
        - 思考需要补充哪些信息才能给出准确的法律建议
        
        ## 输出格式要求：
        请严格按照以下JSON格式输出，不要包含任何其他内容：
        {{
            "core_issue": "核心问题（一句话概括）",
            "legal_elements": ["法律要素1", "法律要素2", "法律要素3"],
            "key_entities": ["实体1", "实体2", "实体3"],
            "query_for_retrieval": "优化的检索查询，包含多个关键词，用空格分隔",
            "missing_info": ["缺失信息1", "缺失信息2"],
            "reasoning": "简要说明你的分析过程"
        }}
        
        ## 示例：
        用户输入: "我工作了3年，公司突然解除劳动合同，没有给我经济补偿，我该怎么办？"
        输出:
        {{
            "core_issue": "公司违法解除劳动合同，劳动者寻求经济补偿",
            "legal_elements": ["劳动合同", "解除", "经济补偿", "违法解除", "工作年限", "劳动者权利"],
            "key_entities": ["3年", "公司", "经济补偿"],
            "query_for_retrieval": "劳动合同解除 经济补偿 工作年限 违法解除 法律后果 维权途径",
            "missing_info": ["解除合同的具体原因和理由", "是否签订了书面劳动合同", "月工资标准"],
            "reasoning": "用户提到工作了3年（工作年限），公司突然解除劳动合同（行为），没有经济补偿（争议点）。需要确认解除原因、劳动合同情况、工资标准等才能给出完整建议。"
        }}
        
        现在请分析以下用户输入：
        """
        return prompt

    def _parse_llm_analysis(self, response_text: str, query: str) -> QuestionAnalysis:
        """
        解析LLM分析结果

        Args:
            response_text: LLM返回的文本
            query: 原始查询

        Returns:
            问题分析结果
        """
        try:
            # 清理响应文本，提取JSON部分
            cleaned_text = response_text.strip()

            # 尝试找到JSON部分的起始和结束位置
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}') + 1

            if 0 <= json_start < json_end:
                json_str = cleaned_text[json_start:json_end]
                result_dict = json.loads(json_str)
            else:
                # 如果找不到JSON，尝试直接解析整个响应
                result_dict = json.loads(cleaned_text)

            # 提取字段
            core_issue = str(result_dict.get('core_issue', query))

            legal_elements = result_dict.get('legal_elements', [])
            if not isinstance(legal_elements, list):
                legal_elements = []

            key_entities = result_dict.get('key_entities', [])
            if not isinstance(key_entities, list):
                key_entities = []

            query_for_retrieval = str(result_dict.get('query_for_retrieval', query))

            missing_info = result_dict.get('missing_info', [])
            if not isinstance(missing_info, list):
                missing_info = []

            # 记录推理过程（用于调试）
            reasoning = result_dict.get('reasoning', '')
            logger.debug(f"问题分析推理过程：{reasoning}")

            return QuestionAnalysis(
                core_issue=core_issue,
                legal_elements=legal_elements,
                key_entities=key_entities,
                query_for_retrieval=query_for_retrieval,
                missing_info=missing_info
            )

        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应JSON失败: {e}, 原始响应: {response_text}")
            # 返回默认值
            return self._create_default_result(query)
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}")
            return self._create_default_result(query)

    def _create_default_result(self, query: str) -> QuestionAnalysis:
        """
        创建默认的问题分析结果

        Args:
            query: 用户查询

        Returns:
            默认的问题分析结果
        """
        logger.warning(f"使用默认问题分析结果：{query}")

        # 使用规则提取一些基本信息
        legal_elements = self._extract_legal_elements(query)

        return QuestionAnalysis(
            core_issue=query,
            legal_elements=legal_elements,
            key_entities=[],
            query_for_retrieval=query,
            missing_info=[]
        )

    def analyze_question(
            self,
            query: str,
            context: List[Dict] = None,
            intent_result = None,
            use_cache: bool = True
    ) -> QuestionAnalysis:
        """
        分析用户问题

        Args:
            query: 用户查询文本
            context: 对话上下文（最近的消息列表）
            intent_result: 意图识别结果（可选，如果不提供则自动识别）
            use_cache: 是否使用缓存（默认为True）

        Returns:
            问题分析结果
        """
        if not query or not query.strip():
            raise ValueError("查询内容不能为空")

        # 检查缓存
        if use_cache:
            cache_key = self._get_cache_key(query, context)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result

        # 如果没有提供意图结果，先进行意图识别
        if intent_result is None:
            try:
                intent_result = self.intent_service.classify_intent(query)
            except Exception as e:
                logger.error(f"意图识别失败：{e}")
                intent_result = None

        #格式化意图信息
        intent_str = None
        if intent_result:
            intent_str = (
                f"是否法律问题：{intent_result.is_legal_related},"
                f"法律领域：{intent_result.legal_category}"
            )

        try:
            # 构建提示词
            prompt = self._build_analysis_prompt(query, context, intent_str)
            logger.info(f"开始问题分析：{query}")

            # 调用豆包LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],              # type: ignore
                temperature=0.4,
                max_tokens=800,
                top_p=0.9
            )

            # 提取响应文本
            response_text = response.choices[0].message.content
            logger.debug(f"LLM原始分析响应：{response_text}")

            # 解析响应
            result = self._parse_llm_analysis(response_text, query)

            # 补充NLP规则提取的结果
            nlp_entities = self._extract_entities_nlp(query)
            if nlp_entities:
                for entity in nlp_entities:
                    entity_str = entity.entity_value
                    if entity_str not in result.key_entities:
                        result.key_entities.append(entity_str)

            # 缓存结果
            if use_cache:
                cache_key = self._get_cache_key(query, context)
                self._set_cache(cache_key, result)

            logger.info(
                f"问题分析完成: core_issue={result.core_issue[:50]}..., "
                f"legal_elements={len(result.legal_elements)}, "
                f"key_entities={len(result.key_entities)}, "
                f"missing_info={len(result.missing_info)}"
            )

            return result

        except Exception as e:
            logger.error(f"问题分析失败：{e}")
            # 返回默认值
            return self._create_default_result(query)

    def extract_entities(self, query: str) -> List[EntityExtraction]:
        """
        仅提取实体（不进行完整分析）

        Args:
            query: 用户查询

        Returns:
            实体提取结果列表
        """
        # 检查缓存
        cache_key = f"entities:{hash(query)}"
        if cache_key in self._entity_cache:
            cached, timestamp = self._entity_cache[cache_key]
            if datetime.now() - timestamp < timedelta(hours=1):
                return cached

        # 使用NLP规则提取
        entities = self._extract_entities_nlp(query)

        # 缓存结果
        self._entity_cache[cache_key] = (entities, datetime.now())

        return entities

    def optimize_query(self, query: str, intent_result = None) -> str:
        """
        优化检索查询

        Args:
            query: 原始查询
            intent_result: 意图识别结果（可选）

        Returns:
            优化的查询字符串
        """
        try:
            # 简单的查询优化
            analysis = self.analyze_question(query, intent_result)
            return analysis.query_for_retrieval
        except Exception as e:
            logger.error(f"查询优化失败：{e}")
            return query        # 失败时返回原始查询

# 创建全局实例
question_analyzer = QuestionAnalyzer()