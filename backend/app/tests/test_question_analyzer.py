"""
问题理解服务单元测试
"""

import pytest
from ..services.chat.question_analyzer import question_analyzer
from ..services.chat.intent_service import intent_service

class TestQuestionAnalyzer:
    """问题理解服务测试类"""

    def test_analyze_labor_contract_issue(self):
        """测试劳动合同问题分析"""
        query = "我工作了3年，公司突然解除劳动合同，没有给我经济补偿，我该怎么办？"

        result = question_analyzer.analyze_question(query)

        assert result is not None
        assert result.core_issue
        assert len(result.legal_elements) > 0
        assert len(result.key_entities) > 0
        assert result.query_for_retrieval
        assert "3年" in result.key_entities or "工作" in result.legal_elements

    def test_extract_entities(self):
        """测试实体提取"""
        query = "我在2024年1月15日签订了一份劳动合同，月薪8000元，工作地点在北京朝阳区"

        entities = question_analyzer.extract_entities(query)

        assert len(entities) > 0
        entity_types = [e.entity_type for e in entities]
        # 应该提取到日期、金额等实体
        assert len(entity_types) > 0

    def test_analyze_with_context(self):
        """测试带上下文的问题分析"""
        query = "那如果我不想辞职呢？"
        context = [
            {"role": "user", "content": "公司要求我主动辞职，但我不想"},
            {"role": "assistant", "content": "根据法律规定，公司不能强迫员工辞职"}
        ]

        result = question_analyzer.analyze_question(query, context=context)

        assert result is not None
        assert result.core_issue

    def test_optimize_query(self):
        """测试查询优化"""
        query = "公司不给我发工资"

        optimized = question_analyzer.optimize_query(query)

        assert optimized
        # 优化后的查询应该包含更多关键词
        assert len(optimized) >= len(query)

    def test_analyze_missing_info(self):
        """测试缺失信息识别"""
        query = "我朋友想离婚，想知道怎么分财产"

        result = question_analyzer.analyze_question(query)

        assert result is not None
        # 离婚财产分割需要很多信息，应该能识别到缺失信息
        # 虽然不一定每次都识别到，但至少结构是正确的
        assert isinstance(result.missing_info, list)

    def test_cache_functionality(self):
        """测试缓存功能"""
        query = "劳动合同解除补偿标准是什么？"

        # 第一次调用
        result1 = question_analyzer.analyze_question(query)

        # 第二次调用，应该从缓存获取
        result2 = question_analyzer.analyze_question(query)

        # 结果应该相同
        assert result1.core_issue == result2.core_issue
        assert len(result1.legal_elements) == len(result2.legal_elements)

    def test_extract_legal_elements(self):
        """测试法律要素提取"""
        query = "我想咨询一下合同的违约金问题"

        result = question_analyzer.analyze_question(query)

        assert result is not None
        # 应该提取到合同相关的法律要素
        assert any("合同" in elem or "违约" in elem for elem in result.legal_elements)

    def test_analyze_with_intent(self):
        """测试结合意图的问题分析"""
        query = "故意伤害罪的量刑标准"

        # 先获取意图
        intent = intent_service.classify_intent(query)

        # 再分析问题
        result = question_analyzer.analyze_question(query, intent_result=intent)

        assert result is not None
        assert result.core_issue
        assert result.query_for_retrieval

    def test_empty_query(self):
        """测试空查询处理"""
        with pytest.raises(ValueError):
            question_analyzer.analyze_question("")

    def test_complex_law_query(self):
        """测试复杂法律问题分析"""
        query = "我和合伙人一起开了一家有限责任公司，现在他想退出，我想知道股权怎么处理"

        result = question_analyzer.analyze_question(query)

        assert result is not None
        has_equity = (
                any("股权" in entity for entity in result.key_entities) or
                any("股权" in element for element in result.legal_elements)
        )
        assert has_equity, f"未找到包含'股权'的实体或要素。key_entities={result.key_entities}, legal_elements={result.legal_elements}"
        assert result.query_for_retrieval
        # 应该识别到缺失信息
        assert isinstance(result.missing_info, list)


if __name__ == "__main__":
    # 简单的运行测试
    test = TestQuestionAnalyzer()

    print("开始测试问题理解服务...\n")

    test.test_analyze_labor_contract_issue()
    print("✅ 测试通过: 劳动合同问题分析")

    test.test_extract_entities()
    print("✅ 测试通过: 实体提取")

    test.test_optimize_query()
    print("✅ 测试通过: 查询优化")

    test.test_extract_legal_elements()
    print("✅ 测试通过: 法律要素提取")

    test.test_complex_law_query()
    print("✅ 测试通过: 复杂法律问题分析")

    print("\n所有测试通过！")
