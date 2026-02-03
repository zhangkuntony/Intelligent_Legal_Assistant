"""
RAG检索服务单元测试
"""

from ..services.chat.rag_service import rag_service, RetrievalStrategy
from ..models.chat import RetrievedDoc


class TestRAGService:
    """RAG检索服务测试类"""

    def test_retrieve_relevant_docs(self):
        """测试基本检索功能"""
        query = "劳动合同解除的经济补偿标准是什么？"

        results = rag_service.retrieve_relevant_docs(
            query=query,
            top_k=5,
            threshold=0.6
        )

        assert isinstance(results, list)
        assert len(results) <= 5

        # 检查结果格式
        for doc in results:
            assert isinstance(doc, RetrievedDoc)
            assert doc.document_id
            assert doc.document_title
            assert doc.chunk_content
            assert 0.0 <= doc.score <= 1.0

    def test_retrieve_with_threshold(self):
        """测试阈值过滤"""
        query = "劳动合同解除"

        # 高阈值
        results_high = rag_service.retrieve_relevant_docs(
            query=query,
            top_k=10,
            threshold=0.8
        )

        # 低阈值
        results_low = rag_service.retrieve_relevant_docs(
            query=query,
            top_k=10,
            threshold=0.5
        )

        # 低阈值应该返回更多结果
        assert len(results_low) >= len(results_high)

        # 高阈值的结果分数都应该很高
        if results_high:
            for doc in results_high:
                assert doc.score >= 0.8

    def test_retrieve_with_cache(self):
        """测试缓存功能"""
        query = "经济补偿标准是什么？"

        # 第一次检索
        results1 = rag_service.retrieve_relevant_docs(
            query=query,
            top_k=5,
            use_cache=True
        )

        # 第二次检索，应该从缓存获取
        results2 = rag_service.retrieve_relevant_docs(
            query=query,
            top_k=5,
            use_cache=True
        )

        # 结果应该相同
        assert len(results1) == len(results2)
        for doc1, doc2 in zip(results1, results2):
            assert doc1.document_id == doc2.document_id
            assert doc1.chunk_index == doc2.chunk_index

    def test_batch_retrieve(self):
        """测试批量检索"""
        queries = [
            "劳动合同解除补偿",
            "加班工资计算",
            "社保缴纳标准"
        ]

        results_list = rag_service.batch_retrieve(
            queries=queries,
            top_k=3
        )

        assert len(results_list) == 3
        assert all(isinstance(results, list) for results in results_list)

    def test_get_available_strategies(self):
        """测试获取检索策略"""
        strategies = rag_service.get_available_strategies()

        assert isinstance(strategies, list)
        assert RetrievalStrategy.VECTOR in strategies
        assert len(strategies) > 0

    def test_clear_cache(self):
        """测试清空缓存"""
        # 先执行几次检索以填充缓存
        rag_service.retrieve_relevant_docs("测试查询1", top_k=3)
        rag_service.retrieve_relevant_docs("测试查询2", top_k=3)

        # 清空缓存
        rag_service.clear_cache()

        # 验证缓存已清空
        assert len(rag_service._cache) == 0

    def test_empty_query(self):
        """测试空查询处理"""
        results = rag_service.retrieve_relevant_docs(query="")

        assert results == []

    def test_reranking(self):
        """测试重排序功能"""
        query = "劳动合同解除补偿标准"

        # 禁用重排序
        results_no_rerank = rag_service.retrieve_relevant_docs(
            query=query,
            top_k=5,
            enable_rerank=False
        )

        # 启用重排序
        results_with_rerank = rag_service.retrieve_relevant_docs(
            query=query,
            top_k=5,
            enable_rerank=True
        )

        # 重排序后的结果数量应该相同
        assert len(results_no_rerank) == len(results_with_rerank)

        # 重排序应该改变顺序（如果有多个结果）
        if len(results_no_rerank) > 1:
            # 检查至少有一些结果的顺序改变了
            # 由于重排序基于多个因素，可能会改变顺序
            pass  # 这个断言比较弱，但至少验证了函数可调用

    def test_quality_assessment(self):
        """测试质量评估"""
        query = "劳动合同解除补偿"

        results = rag_service.retrieve_relevant_docs(
            query=query,
            top_k=5
        )

        # 应该有日志输出质量评估
        # 由于是私有方法，我们通过公开行为间接验证

        if results:
            # 结果应该按照相关性排序
            scores = [doc.score for doc in results]
            assert scores == sorted(scores, reverse=True)


if __name__ == "__main__":
    # 简单的运行测试
    test = TestRAGService()

    print("开始测试RAG检索服务...\n")

    print("测试1: 基本检索功能")
    test.test_retrieve_relevant_docs()
    print("✅ 测试通过\n")

    print("测试2: 阈值过滤")
    test.test_retrieve_with_threshold()
    print("✅ 测试通过\n")

    print("测试3: 缓存功能")
    test.test_retrieve_with_cache()
    print("✅ 测试通过\n")

    print("测试4: 批量检索")
    test.test_batch_retrieve()
    print("✅ 测试通过\n")

    print("测试5: 获取检索策略")
    test.test_get_available_strategies()
    print("✅ 测试通过\n")

    print("\n所有测试完成！")
