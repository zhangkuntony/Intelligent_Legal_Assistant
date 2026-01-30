"""
RAG检索服务快速测试脚本
"""

from backend.app.services.chat.rag_service import rag_service

# 测试用例
test_queries = [
    ("离婚时财产如何分配？", 5, 0.5),
    ("什么是不动产？", 3, 0.5),
    # ("社保缴纳的标准是什么？", 5, 0.6),
    # ("劳动合同法关于解除合同的规定", 5, 0.65),
    # ("工伤认定的条件和程序", 4, 0.7)
]

print("=" * 80)
print("RAG检索服务测试")
print("=" * 80)
print()

for i, (query, top_k, threshold) in enumerate(test_queries, 1):
    print(f"测试 {i}: {query}")
    print("-" * 80)

    try:
        results = rag_service.retrieve_relevant_docs(
            query=query,
            top_k=top_k,
            threshold=threshold,
            enable_rerank=True,
            enable_deduplication=True
        )

        print(f"检索到 {len(results)} 个相关文档:")
        print()

        for j, doc in enumerate(results, 1):
            print(f"  【结果 {j}】")
            print(f"    文档标题: {doc.document_title}")
            print(f"    文档ID: {doc.document_id}")
            print(f"    分块索引: {doc.chunk_index}")
            print(f"    相似度分数: {doc.score:.3f}")
            print(f"    内容预览: {doc.chunk_content[:100]}...")
            if doc.metadata:
                print(f"    元数据: {list(doc.metadata.keys())}")
            print()

    except Exception as e:
        print(f"  ❌ 检索失败: {e}")
        print()

    print()

print("=" * 80)
print("✅ 测试完成！")
print("=" * 80)
