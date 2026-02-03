"""
RAG检索诊断脚本
排查检索结果为0的原因
"""
import sys

sys.path.append('.')

from backend.app.services.chat.rag_service import rag_service
from backend.app.services.vector_store.milvus_service import milvus_store
from backend.app.core.config import settings

print("=" * 80)
print("RAG检索诊断")
print("=" * 80)
print()

# 1. 检查Milvus集合信息
print("【1】检查Milvus集合信息")
print("-" * 80)
try:
    milvus_store.initialize()
    collection = milvus_store.collection

    print(f"集合名称: {collection.name}")
    print(f"集合状态: {collection.description}")
    print(f"集合中的实体数量: {collection.num_entities}")

    # 检查schema
    schema = collection.schema
    print(f"\n集合Schema:")
    for field in schema.fields:
        if field.dtype.name == "FLOAT_VECTOR":
            print(f"  {field.name}: {field.dtype.name} (维度={field.dim})")
        else:
            print(f"  {field.name}: {field.dtype.name}")

    # 检查索引
    indexes = collection.indexes
    if indexes:
        print(f"\n集合索引:")
        for index in indexes:
            print(f"  字段: {index.field_name}")
            print(f"  类型: {index.index_type}")
            print(f"  参数: {index.params}")
    else:
        print(f"\n⚠️  未找到索引")

    print()

except Exception as e:
    print(f"❌ 检查Milvus集合失败: {e}")
    print()

# 2. 测试生成embedding的维度
print("【2】测试生成embedding的维度")
print("-" * 80)
try:
    test_text = "离婚时财产如何分配？"
    print(f"测试文本: {test_text}")

    # 生成embedding
    embedding = rag_service._get_embedding_from_llm(test_text)
    print(f"Embedding维度: {len(embedding)}")
    print(f"Embedding前5个值: {embedding[:5]}")
    print(f"配置的MILVUS_DIMENSION: {settings.MILVUS_DIMENSION}")

    if len(embedding) != settings.MILVUS_DIMENSION:
        print(f"❌ 维度不匹配！实际: {len(embedding)}, 配置: {settings.MILVUS_DIMENSION}")
    else:
        print(f"✅ 维度匹配")

    print()

except Exception as e:
    print(f"❌ 生成embedding失败: {e}")
    import traceback

    traceback.print_exc()
    print()

# 3. 直接使用Milvus搜索（不经过RAG服务）
print("【3】直接使用Milvus搜索（绕过阈值过滤）")
print("-" * 80)
try:
    test_query = "离婚时财产如何分配？"
    print(f"查询文本: {test_query}")

    # 生成查询向量
    query_embedding = rag_service._get_embedding_from_llm(test_query)
    print(f"查询向量维度: {len(query_embedding)}")

    # 直接搜索，不设置阈值
    raw_results = milvus_store.search_similar(
        query_embedding=query_embedding,
        top_k=10
    )

    print(f"\n原始搜索结果数（未过滤）: {len(raw_results)}")
    print()

    if raw_results:
        print("前5个结果:")
        for i, result in enumerate(raw_results[:5], 1):
            print(f"  结果{i}:")
            print(f"    分数: {result['score']:.6f}")
            print(f"    文档ID: {result['document_id']}")
            print(f"    内容预览: {result['content'][:100]}...")
            print()
    else:
        print("❌ Milvus直接搜索也没有结果")
        print("可能原因:")
        print("  1. 向量维度不匹配")
        print("  2. Milvus集合为空")
        print("  3. 索引配置错误")
        print("  4. 查询向量生成失败")

    print()

except Exception as e:
    print(f"❌ Milvus搜索失败: {e}")
    import traceback

    traceback.print_exc()
    print()

# 4. 测试不同阈值
print("【4】测试不同阈值的效果")
print("-" * 80)
try:
    test_query = "离婚时财产如何分配？"

    # 先获取原始搜索结果
    query_embedding = rag_service._get_embedding_from_llm(test_query)
    raw_results = milvus_store.search_similar(
        query_embedding=query_embedding,
        top_k=20
    )

    if raw_results:
        print(f"原始结果数: {len(raw_results)}")
        print(f"分数范围: {min(r['score'] for r in raw_results):.6f} ~ {max(r['score'] for r in raw_results):.6f}")
        print()

        # 测试不同阈值
        thresholds = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        print("不同阈值下的结果数:")
        for threshold in thresholds:
            filtered = [r for r in raw_results if r['score'] >= threshold]
            print(f"  阈值={threshold:.1f}: {len(filtered)} 个结果")

        print()
    else:
        print("❌ 没有原始结果，无法测试阈值")
        print()

except Exception as e:
    print(f"❌ 测试阈值失败: {e}")
    print()

# 5. 测试RAG检索（带详细日志）
print("【5】测试RAG检索服务（关闭缓存和去重）")
print("-" * 80)
try:
    test_queries = [
        "离婚时财产如何分配？",
        "什么是不动产？"
    ]

    for query in test_queries:
        print(f"\n查询: {query}")

        # 使用不同的阈值进行测试
        for threshold in [0.0, 0.1, 0.3, 0.5, 0.7]:
            try:
                results = rag_service.retrieve_relevant_docs(
                    query=query,
                    top_k=5,
                    threshold=threshold,
                    use_cache=False,
                    enable_rerank=False,
                    enable_deduplication=False  # 关闭去重
                )
                print(f"  阈值={threshold:.1f}: {len(results)} 个结果")
            except Exception as e:
                print(f"  阈值={threshold:.1f}: ❌ 错误 - {e}")

    print()

except Exception as e:
    print(f"❌ RAG检索测试失败: {e}")
    print()

# 6. 检查embedding生成方式一致性
print("【6】检查embedding生成方式一致性")
print("-" * 80)
try:
    # 检查统一处理器的embedding生成方式
    from backend.app.services.langchain_processor.unified_processor import UnifiedDocumentProcessor

    processor = UnifiedDocumentProcessor()
    test_text = "离婚时财产如何分配？"

    # 使用处理器生成embedding
    text_input = {"text": test_text, "type": "text"}
    inputs = [text_input]

    resp = processor.ark_client.multimodal_embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=inputs
    )
    embedding1 = resp.data.embedding
    print(f"统一处理器生成embedding维度: {len(embedding1)}")

    # 使用RAG服务生成embedding
    embedding2 = rag_service._get_embedding_from_llm(test_text)
    print(f"RAG服务生成embedding维度: {len(embedding2)}")

    # 比较两者
    if len(embedding1) == len(embedding2):
        # 计算两个向量的相似度
        similarity = rag_service._cosine_similarity(embedding1, embedding2)
        print(f"✅ 两个向量维度相同")
        print(f"   两者余弦相似度: {similarity:.6f}")

        if similarity > 0.999:
            print(f"   ✅ 两个向量几乎完全相同，生成方式一致")
        else:
            print(f"   ⚠️  两个向量有差异，可能生成方式不同")
    else:
        print(f"❌ 两个向量维度不同！")

    print()

except Exception as e:
    print(f"❌ 检查embedding生成方式失败: {e}")
    import traceback

    traceback.print_exc()
    print()

print("=" * 80)
print("✅ 诊断完成！")
print("=" * 80)
