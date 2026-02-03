"""
对话生成服务快速测试脚本
"""

import asyncio
import sys
sys.path.append('.')

from backend.app.services.chat.chat_service import chat_service
from backend.app.models.chat import ChatRequest

async def test_chat_service():
    """测试对话服务"""
    print("=" * 80)
    print("对话生成服务测试")
    print("=" * 80)
    print()

    # 生成有效的测试用户ID
    test_user_id = '624b3876-b421-4908-9553-5f99170797d2'
    print(f"测试用户ID: {test_user_id}")
    print()

    # 测试用例
    test_cases = [
        {
            "query": "离婚时财产如何分配？",
            "description": "婚姻家庭法律问题"
        },
        {
            "query": "劳动合同解除需要支付经济补偿吗？",
            "description": "劳动法问题"
        },
        {
            "query": "什么是知识产权？",
            "description": "知识产权问题"
        },
        {
            "query": "今天天气怎么样？",
            "description": "非法律问题（测试拒绝回复）"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        description = test_case["description"]

        print(f"测试 {i}: {description}")
        print(f"问题: {query}")
        print("-" * 80)

        try:
            # 构建请求
            request = ChatRequest(
                content=query,
                include_thinking=True,  # 包含思考过程
                top_k=5
            )

            # 生成回复
            response = await chat_service.generate_response(
                request=request,
                user_id=test_user_id  # 测试用户ID
            )

            # 打印结果
            print(f"✅ 成功生成回复")
            print()
            print(f"【基本信息】")
            print(f"  消息ID: {response.message_id}")
            print(f"  对话ID: {response.conversation_id}")
            print(f"  创建时间: {response.created_at}")
            print()
            print(f"【意图识别】")
            print(f"  是否法律相关: {response.intent.is_legal_related}")
            print(f"  法律领域: {response.intent.legal_category}")
            print(f"  置信度: {response.intent.confidence:.2%}")
            print(f"  建议话题: {', '.join(response.intent.suggested_topics)}")
            print()
            print(f"【问题分析】")
            print(f"  核心问题: {response.analysis.core_issue}")
            print(f"  法律要素: {', '.join(response.analysis.legal_elements)}")
            print(f"  关键实体: {', '.join(response.analysis.key_entities)}")
            print(f"  缺失信息: {', '.join(response.analysis.missing_info) if response.analysis.missing_info else '无'}")
            print()
            print(f"【检索结果】")
            print(f"  检索文档数: {len(response.retrieved_docs)}")
            for j, doc in enumerate(response.retrieved_docs[:3], 1):
                print(f"  文档{j}: {doc.document_title} (相似度: {doc.score:.2%})")
            print()
            print(f"【AI回复】")
            print(f"  内容预览: {response.content[:200]}...")
            print(f"  Token使用: {response.tokens_used}")
            print()
            print(f"【思考过程】")
            if response.thinking_process:
                print(response.thinking_process)
            else:
                print("  （未启用）")
            print()
            print(f"【完整回复】")
            print(response.content)
            print()

        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            print()

        print("=" * 80)
        print()

    print("✅ 所有测试完成！")

if __name__ == "__main__":
    asyncio.run(test_chat_service())
