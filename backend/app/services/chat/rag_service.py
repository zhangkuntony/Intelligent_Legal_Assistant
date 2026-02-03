"""
RAG检索服务
协调整个检索流程，支持多种检索策略和结果优化
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from volcenginesdkarkruntime import Ark

from ...core.config import settings
from ...models.chat import RetrievedDoc
from ..langchain_processor.unified_processor import UnifiedDocumentProcessor
from ..vector_store.milvus_service import MilvusVectorStore, milvus_store

import difflib
import logging
import numpy as np

logger = logging.getLogger(__name__)

class RetrievalStrategy:
    """检索策略枚举"""
    VECTOR = "vector"           # 纯向量检索
    BM25 = "bm25"               # 纯BM25检索（暂不支持）
    HYBRID = "hybrid"           # 混合检索（向量+BM25，暂不支持）
    SEMANTIC = "semantic"       # 语义检索（向量检索的别名）

class RAGService:
    """RAG检索服务类"""

    def __init__(
            self,
            processor: UnifiedDocumentProcessor = None,
            vector_store: MilvusVectorStore = None
    ):
        """
        初始化RAG检索服务

        Args:
            processor: 统一文档处理器（可选）
            vector_store: Milvus向量存储（可选）
        """
        # 延迟导入以避免循环依赖
        if processor is None:
            from ..langchain_processor.unified_processor import UnifiedDocumentProcessor
            self.processor = UnifiedDocumentProcessor()
        else:
            self.processor = processor

        self.vector_store = vector_store or milvus_store

        # 初始化豆包客户端（用于查询嵌入）
        self.client = Ark(api_key=settings.LLM_API_KEY)

        # 检索结果缓存
        self._cache: Dict[str, Tuple[List[RetrievedDoc], datetime]] = {}

        # 默认配置
        self.default_top_k = settings.VECTOR_SEARCH_TOP_K if hasattr(settings, "VECTOR_SEARCH_TOP_K") else 5
        self.default_threshold = settings.SIMILARITY_THRESHOLD if hasattr(settings, "SIMILARITY_THRESHOLD") else 0.6

        logger.info(f"RAG检索服务初始化完成，默认top_k={self.default_top_k}, threshold={self.default_threshold}")

    def _get_cache_key(
            self,
            query: str,
            top_k: int,
            threshold: float,
            strategy: str,
            document_id: Optional[str] = None
    ) -> str:
        """
        生成缓存键

        Args:
            query: 查询文本
            top_k: 返回数量
            threshold: 相似度阈值
            strategy: 检索策略
            document_id: 限制的文档ID

        Returns:
            缓存键
        """
        key_parts = [
            f"query:{hash(query.strip().lower())}",
            f"top_k:{top_k}",
            f"threshold:{threshold}",
            f"strategy:{strategy}"
        ]
        if document_id:
            key_parts.append(f"doc:{document_id}")

        return ":".join(key_parts)

    def _get_from_cache(self, cache_key: str) -> Optional[List[RetrievedDoc]]:
        """
        从缓存获取检索结果

        Args:
            cache_key: 缓存键

        Returns:
            缓存的检索结果，如果不存在则返回None
        """
        if cache_key in self._cache:
            results, timestamp = self._cache[cache_key]
            # 缓存有效期30分钟（检索结果变化较快，缓存时间较短）
            if datetime.now() - timestamp < timedelta(minutes=30):
                logger.debug(f"从缓存获取检索结果：{cache_key}")
                return results
            else:
                # 缓存过期，删除
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, results: List[RetrievedDoc]):
        """
        设置缓存

        Args:
            cache_key: 缓存键
            results: 检索结果
        """
        self._cache[cache_key] = (results, datetime.now())

    def _raw_to_retrieved_docs(self, raw_results: List[Dict[str, Any]]) -> List[RetrievedDoc]:
        """
        将原始检索结果转换为RetrievedDoc对象

        Args:
            raw_results: 原始检索结果列表

        Returns:
            RetrievedDoc对象列表
        """
        retrieved_docs = []

        for result in raw_results:
            try:
                # 提取元数据
                metadata = result.get("metadata", {})

                # 获取文档标题
                document_title = metadata.get("document_title", "未知文档")

                # 获取文档ID
                document_id = result.get("document_id", '')

                # 获取分块索引
                chunk_index = result.get("chunk_index", 0)

                # 获取内容
                chunk_content = result.get('content', '')

                # 获取分数
                score = result.get("score", 0.0)

                # 创建RetrievedDoc对象
                retrieved_doc = RetrievedDoc(
                    document_id=str(document_id),
                    document_title=str(document_title),
                    chunk_index=int(chunk_index),
                    chunk_content=str(chunk_content),
                    score=float(score),
                    metadata=metadata
                )

                retrieved_docs.append(retrieved_doc)

            except Exception as e:
                logger.error(f"转换检索结果失败：{e}， result:{result}")
                continue

        return retrieved_docs

    def _filter_by_threshold(
            self,
            docs: List[RetrievedDoc],
            threshold: float
    ) -> List[RetrievedDoc]:
        """
        按相似度阈值过滤结果

        Args:
            docs: 检索结果列表
            threshold: 相似度阈值

        Returns:
            过滤后的结果列表
        """
        filtered = [doc for doc in docs if doc.score >= threshold]
        logger.debug(f"阈值过滤：原始{len(docs)}个 -> 过滤后{len(filtered)}个")
        return filtered

    def _deduplicate_results(
            self,
            docs: List[RetrievedDoc],
            similarity_threshold: float = 0.85,
            enable_semantic: bool = True
    ) -> List[RetrievedDoc]:
        """
        渐进式语义去重：三层过滤

        1. 快速hash去重（完全相同）
        2. 文本相似度去重（中等相似）
        3. 向量语义去重（高精度）

        Args:
            docs: 检索结果列表
            similarity_threshold: 相似度阈值（用于文本和语义去重）
            enable_semantic: 是否启用语义去重（启用向量相似度计算）

        Returns:
            去重后的结果列表
        """
        if len(docs) <= 1:
            return docs

        logger.debug(f"开始渐进式去重，初始文档数：{len(docs)}")

        # 第一层：hash去重（超快速）
        layer1 = self._hash_deduplicate(docs)
        logger.debug(f"第一层hash去重：{len(docs)} -> {len(layer1)}")

        if len(layer1) <= 1:
            return layer1

        # 第二层：文本相似度去重（快速）
        layer2 = self._text_similarity_deduplicate(layer1, similarity_threshold)
        logger.debug(f"第二层文本去重：{len(layer1)} -> {len(layer2)}")

        if len(layer2) <= 1 or not enable_semantic:
            return layer2

        # 第三层：向量语义去重（高精度，但较慢）
        layer3 = self._semantic_deduplicate(layer2, similarity_threshold)
        logger.debug(f"第三层语义去重：{len(layer2)} -> {len(layer3)}")

        total_removal = len(docs) - len(layer3)
        if total_removal > 0:
            logger.info(
                f"渐进式去重完成：原始{len(docs)}个 -> 最终{len(layer3)}个 "
                f"(去除{total_removal}个重复文档)"
            )

        return layer3

    def _hash_deduplicate(self, docs: List[RetrievedDoc]) -> List[RetrievedDoc]:
        """
        第一层：基于hash的去重（去除完全相同的内容）

        Args:
            docs: 文档列表

        Returns:
            去重后的文档列表
        """
        seen = set()
        deduplicated = []

        for doc in docs:
            # 使用内容的hash作为去重依据
            content_hash = hash(doc.chunk_content)

            if content_hash not in seen:
                seen.add(content_hash)
                deduplicated.append(doc)

        return deduplicated

    def _text_similarity_deduplicate(
            self,
            docs: List[RetrievedDoc],
            threshold: float
    ) -> List[RetrievedDoc]:
        """
        第二层：基于文本相似度的去重

        使用多种相似度指标：
        - SequenceMatcher相似度（适合检测轻微改动）
        - 最大连续重叠比例（适合检测大段复制）
        - Jaccard相似度（基于词汇集合）

        Args:
            docs: 文档列表
            threshold: 相似度阈值

        Returns:
            去重后的文档列表
        """
        deduplicated = []

        for doc in docs:
            is_duplicate = False

            for kept_doc in deduplicated:
                # 方法1：SequenceMatcher相似度
                seq_similarity = difflib.SequenceMatcher(
                    None,
                    doc.chunk_content,
                    kept_doc.chunk_content
                ).ratio()

                # 方法2：最大连续重叠比例
                overlap_ratio = self._calculate_max_overlap(
                    doc.chunk_content,
                    kept_doc.chunk_content
                )

                # 方法3：Jaccard相似度
                jaccard_sim = self._calculate_jaccard_similarity(
                    doc.chunk_content,
                    kept_doc.chunk_content
                )

                # 任一指标超过阈值即视为重复
                if (seq_similarity >= threshold or
                    overlap_ratio >= threshold * 0.8 or
                    jaccard_sim >= threshold):
                    is_duplicate = True
                    logger.debug(
                        f"发现文本重复文档: seq={seq_similarity:.3f}, "
                        f"overlap={overlap_ratio:.3f}, jaccard={jaccard_sim:.3f}"
                    )
                    break

            if not is_duplicate:
                deduplicated.append(doc)

        return deduplicated

    def _calculate_max_overlap(self, text1: str, text2: str) -> float:
        """
        计算最大连续重叠比例

        找出最长公共子串，计算其占较短文本的比例

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            最大重叠比例
        """
        # 找出最长公共子串
        matcher = difflib.SequenceMatcher(None, text1, text2)
        match = matcher.find_longest_match(0, len(text1), 0, len(text2))

        if match.size == 0:
            return 0.0

        max_overlap_len = match.size
        return max_overlap_len / min(len(text1), len(text2))

    def _calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        """
        计算Jaccard相似度（基于词汇集合）

        Jaccard = |A ∩ B| / |A ∪ B|

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            Jaccard相似度
        """
        set1 = set(text1.split())
        set2 = set(text2.split())

        if not set1 and not set2:
            return 1.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _semantic_deduplicate(
            self,
            docs: List[RetrievedDoc],
            threshold: float
    ) -> List[RetrievedDoc]:
        """第三层：基于向量余弦相似度的语义去重"""
        deduplicated = []
        embeddings = []

        for doc in docs:
            # 获取或计算embedding
            try:
                embedding = self._get_or_fetch_embedding(doc)
            except Exception as e:
                logger.warning(f"获取embedding失败，跳过语义去重：{e}")
                # 如果获取失败，保留该文档
                deduplicated.append(doc)
                continue

            # 检查与已见内容的相似度
            is_duplicate = False
            for kept_emb in embeddings:
                similarity = self._cosine_similarity(embedding, kept_emb)
                if similarity >= threshold:
                    is_duplicate = True
                    logger.debug(
                        f"发现语义重复文档: 余弦相似度={similarity:.3f}"
                    )
                    break

            if not is_duplicate:
                deduplicated.append(doc)
                embeddings.append(embedding)

        return deduplicated

    def _cosine_similarity(
            self,
            vec1: List[float],
            vec2: List[float]
    ) -> float:
        """
        计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            余弦相似度（0-1之间）
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))


    def _get_or_fetch_embedding(self, doc: RetrievedDoc) -> List[float]:
        """
        获取文档的embedding向量

        优先从metadata中获取，其次尝试从Milvus查询，
        最后重新计算

        Args:
            doc: 文档对象

        Returns:
            embedding向量
        """
        # 方法1: 从metadata中获取（如果已存储）
        if 'embedding' in doc.metadata:
            return doc.metadata['embedding']

        # 方法2: 从Milvus查询（如果有document_id和chunk_index）
        try:
            # 构建过滤表达式
            filter_expr = f"document_id == '{doc.document_id}' && chunk_index == {doc.chunk_index}"

            # 使用Milvus的query功能
            results = self.vector_store.collection.query(
                expr=filter_expr,
                output_fields=["embedding"],
                limit=1
            )

            if results and len(results) > 0 and 'embedding' in results[0]:
                logger.debug(f"从Milvus获取到embedding: {doc.document_id}")
                return results[0]['embedding']

        except Exception as e:
            logger.warning(f"从Milvus获取embedding失败：{e}")

        # 方法3：重新计算embedding
        logger.debug(f"重新计算embedding: {doc.document_id}")
        embedding = self._get_embedding_from_llm(doc.chunk_content)

        # 缓存到metadata中
        doc.metadata['embedding'] = embedding

        return embedding

    def _get_embedding_from_llm(self, text: str) -> List[float]:
        """
        调用LLM生成embedding

        Args:
            text: 输入文本

        Returns:
            embedding向量
        """
        try:
            # 构造输入对象
            text_input = {
                "text": text,
                "type": "text"
            }
            inputs = [text_input]

            resp = self.client.multimodal_embeddings.create(
                model=settings.EMBEDDING_MODEL if hasattr(settings, 'EMBEDDING_MODEL') else 'doubao-embedding-vision-250615',
                input=inputs
            )
            embedding = resp.data.embedding
            return embedding
        except Exception as e:
            logger.error(f"生成embedding失败：{e}")
            raise

    def _rerank_results(
            self,
            docs: List[RetrievedDoc],
            query: str
    ) -> List[RetrievedDoc]:
        """
        重新排序检索结果

        Args:
            docs: 检索结果列表
            query: 原始查询

        Returns:
            重排序后的结果列表
        """
        if not docs:
            return []

        # 简单的重排序策略：基于多种因素的综合评分
        # 1. 原始相似度分数
        # 2. 内容长度（更长的内容可能包含更多信息）
        # 3. 关键词匹配度

        query_keywords = set(query.split())
        query_keywords_lower = {kw.lower() for kw in query_keywords}

        def calculate_rerank_score(doc: RetrievedDoc) -> float:
            """计算重排序分数"""
            # 基础分数
            base_score = doc.score

            # 长度奖励：适中的长度（100-500字符）
            content_length = len(doc.chunk_content)
            if 100 <= content_length <= 500:
                length_bonus = 0.05
            elif content_length < 100:
                length_bonus = -0.02
            else:
                length_bonus = -0.01

            # 关键词匹配奖励
            doc_content_lower = doc.chunk_content.lower()
            keyword_matches = sum(1 for kw in query_keywords_lower if kw in doc_content_lower)
            keyword_bonus = min(keyword_matches * 0.03, 0.15)

            # 综合分数
            rerank_score = base_score + length_bonus + keyword_bonus

            return rerank_score

        # 计算每个文档的重排序分数
        reranked = docs.copy()
        reranked.sort(key=calculate_rerank_score, reverse=True)

        logger.debug(f"重排序完成：返回{len(reranked)}个结果")
        return reranked

    def _assess_result_quality(
            self,
            docs: List[RetrievedDoc]
    ) -> Dict[str, Any]:
        """
        评估检索结果质量

        Args:
            docs: 检索结果列表

        Returns:
            质量评估字典
        """
        if not docs:
            return {
                'count': 0,
                'avg_score': 0.0,
                'max_score': 0.0,
                'min_score': 0.0,
                'quality': 'poor'
            }

        scores = [doc.score for doc in docs]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)

        # 评估质量
        if avg_score >= 0.8 and len(docs) >= 3:
            quality = 'excellent'
        elif avg_score >= 0.7 and len(docs) >= 2:
            quality = 'good'
        elif avg_score >= 0.5 and len(docs) >= 1:
            quality = 'acceptable'
        else:
            quality = 'poor'

        assessment = {
            'count': len(docs),
            'avg_score': round(avg_score, 3),
            'max_score': round(max_score, 3),
            'min_score': round(min_score, 3),
            'quality': quality
        }

        logger.info(f"检索结果质量评估：{assessment}")
        return assessment

    def retrieve_relevant_docs(
            self,
            query: str,
            top_k: int = None,
            threshold: float = None,
            strategy: str = None,
            document_id: str = None,
            use_cache: bool = True,
            enable_rerank: bool = True,
            enable_deduplication: bool = True,
            dedup_threshold: float = 0.85,          # 去重阈值
            enable_semantic_dedup: bool = True      # 是否启用语义去重
    ) -> List[RetrievedDoc]:
        """
        检索相关文档（核心方法）

        Args:
            query: 查询文本
            top_k: 返回前K个结果
            threshold: 相似度阈值
            strategy: 检索策略（vector, bm25, hybrid）
            document_id: 限制在特定文档中检索
            use_cache: 是否使用缓存
            enable_rerank: 是否启用重排序
            enable_deduplication: 是否启用去重
            dedup_threshold: 去重阈值（0-1之间，越高越严格）
            enable_semantic_dedup: 是否启用语义去重（启用向量相似度计算）

        Returns:
            检索到的相关文档列表
        """
        if not query or not query.strip():
            logger.warning("查询内容为空")
            return []

        # 使用默认值
        top_k = top_k or self.default_top_k
        threshold = threshold or self.default_threshold
        strategy = strategy or RetrievalStrategy.VECTOR

        # 检查缓存
        if use_cache:
            cache_key = self._get_cache_key(query, top_k, threshold, strategy, document_id)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result

        try:
            logger.info(
                f"开始检索: query={query[:50]}..., "
                f"top_k={top_k}, threshold={threshold}, strategy={strategy}"
            )

            # 调用现有的检索方法
            if strategy == RetrievalStrategy.VECTOR or strategy == RetrievalStrategy.SEMANTIC:
                raw_results = self.processor.search_similar_chunks(
                    query=query,
                    top_k=top_k * 2,                # 检索更多，为后续过滤留余地
                    threshold=threshold * 0.8,      # 降低阈值以获取更多候选
                    document_id=document_id
                )
            elif strategy in [RetrievalStrategy.BM25, RetrievalStrategy.HYBRID]:
                logger.warning(f"检索策略'{strategy}'暂不支持，使用向量检索")
                raw_results = self.processor.search_similar_chunks(
                    query=query,
                    top_k=top_k * 2,
                    threshold=threshold * 0.8,
                    document_id=document_id
                )
            else:
                logger.error(f"不支持的检索策略：{strategy}")
                raw_results = []

            if not raw_results:
                logger.warning(f"未检索到任何结果：{query}")
                return []

            # 转换为RetrievedDoc对象
            retrieved_docs = self._raw_to_retrieved_docs(raw_results)

            # 按阈值过滤
            filtered_docs = self._filter_by_threshold(retrieved_docs, threshold)

            # 去重
            if enable_deduplication:
                filtered_docs = self._deduplicate_results(
                    filtered_docs,
                    similarity_threshold=dedup_threshold,
                    enable_semantic=enable_semantic_dedup
                )

            # 重排序
            if enable_rerank:
                filtered_docs = self._rerank_results(filtered_docs, query)

            # 取前K个结果
            final_docs = filtered_docs[:top_k]

            # 评估结果质量
            quality_assessment = self._assess_result_quality(final_docs)

            # 缓存结果
            if use_cache:
                cache_key = self._get_cache_key(query, top_k, threshold, strategy, document_id)
                self._set_cache(cache_key, final_docs)

            logger.info(
                f"检索完成: 原始{len(raw_results)}个 -> "
                f"过滤后{len(filtered_docs)}个 -> 最终{len(final_docs)}个, "
                f"质量={quality_assessment['quality']}, 平均分数={quality_assessment['avg_score']}"
            )

            return final_docs

        except Exception as e:
            logger.error(f"检索失败：{e}", exc_info=True)
            return []

    def batch_retrieve(
            self,
            queries: List[str],
            top_k: int = None,
            threshold: float = None,
    ) -> List[List[RetrievedDoc]]:
        """
        批量检索相关文档

        Args:
            queries: 查询列表
            top_k: 每个查询返回的结果数量
            threshold: 相似度阈值

        Returns:
            每个查询的检索结果列表
        """
        results = []
        for query in queries:
            try:
                result = self.retrieve_relevant_docs(
                    query=query,
                    top_k=top_k,
                    threshold=threshold,
                    use_cache=True
                )
                results.append(result)
            except Exception as e:
                logger.error(f"批量检索失败：query={query}, error={e}")
                results.append([])

        return results

    def get_available_strategies(self) -> List[str]:
        """
        获取可用的检索策略

        Returns:
            检索策略列表
        """
        return [
            RetrievalStrategy.VECTOR,
            RetrievalStrategy.SEMANTIC,
            # RetrievalStrategy.BM25,           # 暂不支持
            # RetrievalStrategy.HYBRID          # 暂不支持
        ]

    def clear_cache(self):
        """清空检索缓存"""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"清空检索缓存：删除了{cache_size}个缓存条目")

# 创建全局实例
rag_service = RAGService()

