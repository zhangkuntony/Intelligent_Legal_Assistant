"""
意图识别服务
用于判断用户输入是否为法律相关问题，并识别具体法律领域
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from volcenginesdkarkruntime import Ark
from ...core.config import settings
from ...models.intent import IntentClassification, LEGAL_CATEGORIES

import json
import logging

logger = logging.getLogger(__name__)

class IntentService:
    """意图识别服务类"""

    def __init__(self):
        """初始化意图识别服务"""
        # 初始化豆包LLM客户端
        self.client = Ark(api_key=settings.LLM_API_KEY)
        self.model = settings.LLM_MODEL

        # 意图缓存（简单的内存缓存，生产环境可改用Redis）
        self._cache: Dict[str, tuple] = {}

        logger.info(f"意图识别初始化完成，使用模型：{self.model}")

    def _get_cache_key(self, query: str) -> str:
        """
        生成缓存键

        Args:
            query: 用户查询

        Returns:
            缓存键
        """
        return f"intent:{hash(query.strip().lower())}"

    def _get_from_cache(self, cache_key: str) -> Optional[IntentClassification]:
        """
        从缓存获取结果

        Args:
            cache_key: 缓存键

        Returns:
            缓存的意图分类结果，如果不存在则返回None
        """
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            # 缓存有效期一小时
            if datetime.now() - timestamp < timedelta(hours=1):
                logger.debug(f"从缓存获取意图识别结果：{cache_key}")
                return result
            else:
                # 缓存过期，删除
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, result: IntentClassification):
        """
        设置缓存

        Args:
            cache_key: 缓存键
            result: 意图分类结果
        """
        self._cache[cache_key] = (result, datetime.now())

    def _build_intent_prompt(self, query: str) -> str:
        """
        构建意图识别提示词

        Args:
            query: 用户查询

        Returns:
            提示词
        """
        # 法律领域列表
        categories_desc = "\n".join([
            f"- {code}: {name}"
            for code, name in LEGAL_CATEGORIES.items()
        ])

        prompt = f"""你是一个专业的法律领域分类专家。你的任务是判断用户的输入是否为法律相关问题，并识别具体的法律领域。
        ## 法律领域分类：
        {categories_desc}
        
        ## 任务要求：
        1. 判断用户输入是否与法律相关
        2. 如果是法律相关问题，识别具体的法律领域
        3. 提供你的判断置信度（0-1之间的小数）
        4. 推荐3-5个相关的法律话题
        
        ## 用户输入：
        {query}
        
        ## 输出格式要求：
        请严格按照以下JSON格式输出，不要包含任何其他内容：
        {{
            "is_legal_related": true/false,
            "legal_category": "法律领域代码（如civil、criminal等），如果不是法律问题则为null",
            "confidence": 0.0-1.0之间的数字,
            "reasoning": "简要说明你的判断理由",
            "suggested_topics": ["话题1", "话题2", "话题3", "话题4", "话题5"]
        }}
        
        ## 示例：
        用户输入: "我想咨询劳动合同解除的相关法律规定"
        输出:
        {{
            "is_legal_related": true,
            "legal_category": "labor",
            "confidence": 0.95,
            "reasoning": "用户明确咨询劳动合同解除的法律规定，属于劳动法领域",
            "suggested_topics": ["劳动合同解除", "经济补偿", "工作年限", "违法解除", "法律后果"]
        }}
        
        现在请判断以下用户输入：
        """
        return prompt

    def _parse_llm_response(self, response_text: str, query: str) -> IntentClassification:
        """
        解析LLM响应

        Args:
            response_text: LLM返回的文本
            query: 原始查询

        Returns:
            意图分类结果
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
            is_legal_related = bool(result_dict.get('is_legal_related', False))
            legal_category_code = result_dict.get('legal_category')

            # 映射法律领域代码到中文名称
            legal_category = None
            if legal_category_code and legal_category_code in LEGAL_CATEGORIES:
                legal_category = LEGAL_CATEGORIES[legal_category_code]

            confidence = float(result_dict.get('confidence', 0.0))

            # 确保置信度在合理范围内
            confidence = max(0.0, min(1.0, confidence))

            suggested_topics = result_dict.get('suggested_topics', [])
            if not isinstance(suggested_topics, list):
                suggested_topics = []

            # 限制话题数量
            suggested_topics = suggested_topics[:5]

            # 记录推理过程（用于调试）
            reasoning = result_dict.get('reasoning', '')
            logger.debug(f"意图识别推理过程：{reasoning}")

            return IntentClassification(
                is_legal_related=is_legal_related,
                legal_category=legal_category,
                confidence=confidence,
                suggested_topics=suggested_topics
            )

        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应JSON失败：{e}，原始响应：{response_text}")
            # 返回默认值
            return self._create_default_result(query)
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}")
            return self._create_default_result(query)

    def _create_default_result(self, query: str) -> IntentClassification:
        """
        创建默认的意图分类结果

        Args:
            query: 用户查询

        Returns:
            默认的意图分类结果
        """
        logger.warning(f"使用默认意图分类结果：{query}")
        return IntentClassification(
            is_legal_related=True,
            legal_category="other",
            confidence=0.5,
            suggested_topics=[]
        )

    def classify_intent(self, query: str, use_cache: bool = True) -> IntentClassification:
        """
        分类用户查询的意图

        Args:
            query: 用户查询文本
            use_cache: 是否使用缓存（默认为True）

        Returns:
            意图分类结果
        """
        if not query or not query.strip():
            raise ValueError("查询内容不能为空")

        # 检查缓存
        if use_cache:
            cache_key = self._get_cache_key(query)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result

        try:
            # 构建提示词
            prompt = self._build_intent_prompt(query)
            logger.info(f"开始意图识别：{query}")

            # 调用豆包LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],         # type: ignore
                temperature=0.3,
                max_tokens=500,
                top_p=0.9
            )

            # 提取响应文本
            response_text = response.choices[0].message.content
            logger.debug(f"LLM原始响应：{response_text}")

            # 解析响应
            result = self._parse_llm_response(response_text, query)

            # 缓存结果
            if use_cache:
                cache_key = self._get_cache_key(query)
                self._set_cache(cache_key, result)

            logger.info(
                f"意图识别完成: is_legal_related={result.is_legal_related}, "
                f"legal_category={result.legal_category}, "
                f"confidence={result.confidence}"
            )

            return result

        except Exception as e:
            logger.error(f"意图识别失败：{e}")
            raise

    def batch_classify_intents(self, queries: List[str]) -> List[IntentClassification]:
        """
        批量分类意图

        Args:
            queries: 查询列表

        Returns:
            意图分类结果列表
        """
        results = []
        for query in queries:
            try:
                result = self.classify_intent(query)
                results.append(result)
            except Exception as e:
                logger.error(f"批量意图识别失败：query={query}, error={e}")
                # 使用默认结果
                results.append(self._create_default_result(query))
        return results

    def is_legal_query(self, query: str, threshold: float = 0.7) -> bool:
        """
        快速判断是否为法律查询

        Args:
            query: 用户查询
            threshold: 置信度阈值，默认0.7

        Returns:
            是否为法律查询
        """
        try:
            result = self.classify_intent(query)
            return result.is_legal_related and result.confidence > threshold
        except Exception as e:
            logger.error(f"判断法律查询失败: {e}")
            return True  # 出错时默认认为是法律查询

    def get_legal_categories(self) -> Dict[str, str]:
        """
        获取所有法律领域

        Returns:
            法律领域字典 {代码: 名称}
        """
        return LEGAL_CATEGORIES.copy()

# 创建全局实例
intent_service = IntentService()