# backend/app/tests/quick_test_intent.py
from backend.app.services.chat.intent_service import intent_service

# 测试用例
test_queries = [
    "我想咨询劳动合同解除的相关法律规定",
    "今天天气怎么样？",
    "故意伤害罪的量刑标准是什么？",
    "用人单位不支付加班费怎么办？",
    "合同违约如何赔偿？"
]

print("开始测试意图识别服务...\n")

for i, query in enumerate(test_queries, 1):
    print(f"测试 {i}: {query}")
    result = intent_service.classify_intent(query)
    print(f"  - 是否法律相关: {result.is_legal_related}")
    print(f"  - 法律领域: {result.legal_category}")
    print(f"  - 置信度: {result.confidence:.2f}")
    print(f"  - 建议话题: {', '.join(result.suggested_topics[:3])}")
    print()

print("✅ 测试完成！")
