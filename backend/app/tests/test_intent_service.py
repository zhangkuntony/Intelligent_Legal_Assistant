"""
意图识别服务单元测试
"""

import pytest
from ..services.chat.intent_service import intent_service
from ..models.intent import IntentClassification


class TestIntentService:
    """意图识别服务测试类"""

    def test_classify_legal_query(self):
        """测试法律问题识别"""
        query = "我想咨询劳动合同解除的相关法律规定"
        result = intent_service.classify_intent(query)

        assert result is not None
        assert result.is_legal_related == True
        assert result.confidence > 0.7
        assert result.legal_category is not None
        assert len(result.suggested_topics) > 0

    def test_classify_non_legal_query(self):
        """测试非法律问题识别"""
        query = "今天天气怎么样？"
        result = intent_service.classify_intent(query)

        assert result is not None
        # 应该识别为非法律相关或低置信度
        assert result.confidence < 0.5 or result.is_legal_related == False

    def test_classify_labor_law_query(self):
        """测试劳动法领域识别"""
        query = "用人单位不支付加班费怎么办？"
        result = intent_service.classify_intent(query)

        assert result is not None
        assert result.is_legal_related == True
        assert result.legal_category == "劳动"
        assert any("加班" in topic for topic in result.suggested_topics)

    def test_classify_criminal_law_query(self):
        """测试刑法领域识别"""
        query = "故意伤害罪的量刑标准是什么？"
        result = intent_service.classify_intent(query)

        assert result is not None
        assert result.is_legal_related == True
        assert result.legal_category == "刑事"

    def test_cache_functionality(self):
        """测试缓存功能"""
        query = "合同违约如何赔偿？"

        # 第一次调用
        result1 = intent_service.classify_intent(query)

        # 第二次调用，应该从缓存获取
        result2 = intent_service.classify_intent(query)

        # 结果应该相同
        assert result1.is_legal_related == result2.is_legal_related
        assert result1.legal_category == result2.legal_category
        assert abs(result1.confidence - result2.confidence) < 0.01

    def test_get_legal_categories(self):
        """测试获取法律领域列表"""
        categories = intent_service.get_legal_categories()

        assert isinstance(categories, dict)
        assert len(categories) > 0
        assert "civil" in categories
        assert "criminal" in categories

    def test_empty_query(self):
        """测试空查询处理"""
        with pytest.raises(ValueError):
            intent_service.classify_intent("")

    def test_batch_classify(self):
        """测试批量意图识别"""
        queries = [
            "劳动合同解除的补偿标准是什么？",
            "今天天气怎么样？",
            "故意伤害罪的量刑标准？"
        ]

        results = intent_service.batch_classify_intents(queries)

        assert len(results) == 3
        assert all(isinstance(r, IntentClassification) for r in results)


if __name__ == "__main__":
    # 简单的运行测试
    test = TestIntentService()
    test.test_classify_legal_query()
    print("✅ 测试通过: 法律问题识别")

    test.test_classify_non_legal_query()
    print("✅ 测试通过: 非法律问题识别")

    test.test_classify_labor_law_query()
    print("✅ 测试通过: 劳动法领域识别")

    print("\n所有测试通过！")
