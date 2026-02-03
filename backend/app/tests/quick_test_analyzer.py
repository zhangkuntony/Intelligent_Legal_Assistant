"""
问题理解服务快速测试脚本
"""

from backend.app.services.chat.question_analyzer import question_analyzer
from backend.app.services.chat.intent_service import intent_service

# 测试用例
test_queries = [
    "我工作了3年，公司突然解除劳动合同，没有给我经济补偿，我该怎么办？",
    "2024年1月15日签订的劳动合同，月薪8000元，现在公司违法解除",
    "我和朋友合伙开公司，现在他想退出，股权怎么处理？",
    "故意伤害罪的量刑标准是什么？",
    "我想知道离婚财产分割的原则"
]

print("=" * 80)
print("问题理解服务测试")
print("=" * 80)
print()

for i, query in enumerate(test_queries, 1):
    print(f"测试 {i}: {query}")
    print("-" * 80)

    # 意图识别
    print("【意图识别】")
    intent = intent_service.classify_intent(query)
    print(f"  是否法律问题: {intent.is_legal_related}")
    print(f"  法律领域: {intent.legal_category}")
    print(f"  置信度: {intent.confidence:.2f}")
    print()

    # 问题分析
    print("【问题分析】")
    analysis = question_analyzer.analyze_question(query, intent_result=intent)
    print(f"  核心问题: {analysis.core_issue}")
    print(f"  法律要素 ({len(analysis.legal_elements)}个): {', '.join(analysis.legal_elements[:5])}")
    print(f"  关键实体 ({len(analysis.key_entities)}个): {', '.join(analysis.key_entities[:5])}")
    print(f"  优化查询: {analysis.query_for_retrieval}")
    if analysis.missing_info:
        print(f"  缺失信息 ({len(analysis.missing_info)}个): {', '.join(analysis.missing_info)}")
    else:
        print(f"  缺失信息: 无")
    print()
    print()

print("=" * 80)
print("✅ 测试完成！")
print("=" * 80)
