# 智能法律助手 - 向量检索服务设计文档

## 概述

向量检索服务是RAG系统的核心检索组件，负责基于向量相似度的语义搜索，为法律问答提供相关的知识库内容。本服务利用PostgreSQL的pgvector扩展，实现高效的相似度计算和检索优化。

## 设计目标

- **高精度检索**：确保检索结果与查询高度相关
- **高性能搜索**：支持毫秒级响应时间
- **多维度过滤**：支持按用户、文档类型等多维度过滤
- **智能排序**：结合多种因素进行结果重排序
- **可扩展架构**：支持大规模向量数据的高效检索

## 架构设计

### 模块结构

```
backend/app/services/vector_search/
├── __init__.py              # 模块初始化
├── base_searcher.py         # 抽象基类
├── pgvector_searcher.py     # PostgreSQL向量搜索
├── similarity_calculator.py # 相似度计算
├── result_ranker.py         # 结果排序器
├── query_optimizer.py       # 查询优化器
├── cache_manager.py         # 缓存管理
├── exceptions.py            # 异常定义
└── utils.py                 # 工具函数
```

### 核心接口设计

```python
# 搜索器基类接口
class BaseVectorSearcher(ABC):
    """向量搜索器基类"""
    
    @abstractmethod
    async def search_similar(self, query_embedding: List[float], 
                           top_k: int = 5, **filters) -> List[SearchResult]:
        """搜索相似向量"""
        pass
    
    @abstractmethod
    async def batch_search(self, query_embeddings: List[List[float]], 
                         top_k: int = 5) -> List[List[SearchResult]]:
        """批量搜索"""
        pass
    
    @abstractmethod
    async def get_index_info(self) -> Dict[str, Any]:
        """获取索引信息"""
        pass

# 搜索结果数据结构
@dataclass
class SearchResult:
    """搜索结果"""
    embedding_id: str
    document_id: str
    chunk_content: str
    similarity_score: float
    metadata: Dict[str, Any]
    chunk_index: int
    document_title: str

@dataclass
class SearchResponse:
    """搜索响应"""
    results: List[SearchResult]
    total_count: int
    search_time: float
    query_info: Dict[str, Any]
```

## PostgreSQL向量搜索实现

### pgvector集成

```python
# pgvector_searcher.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..models.document import DocumentEmbedding

class PgVectorSearcher(BaseVectorSearcher):
    """PostgreSQL向量搜索器"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def search_similar(self, query_embedding: List[float], 
                           top_k: int = 5, **filters) -> List[SearchResult]:
        """基于pgvector的相似度搜索"""
        
        # 构建过滤条件
        filter_conditions = self._build_filter_conditions(filters)
        
        # 构建SQL查询
        sql = f"""
        SELECT 
            de.id as embedding_id,
            de.document_id,
            de.chunk_content,
            de.chunk_index,
            de.metadata,
            d.title as document_title,
            1 - (de.embedding <=> :query_embedding) as similarity_score
        FROM document_embeddings de
        JOIN documents d ON de.document_id = d.id
        WHERE {filter_conditions}
        ORDER BY de.embedding <=> :query_embedding
        LIMIT :top_k
        """
        
        # 执行查询
        result = await self.db.execute(
            text(sql),
            {
                'query_embedding': query_embedding,
                'top_k': top_k,
                **filters
            }
        )
        
        rows = result.fetchall()
        
        return [
            SearchResult(
                embedding_id=str(row.embedding_id),
                document_id=str(row.document_id),
                chunk_content=row.chunk_content,
                similarity_score=float(row.similarity_score),
                metadata=row.metadata or {},
                chunk_index=row.chunk_index,
                document_title=row.document_title
            )
            for row in rows
        ]
    
    def _build_filter_conditions(self, filters: Dict) -> str:
        """构建过滤条件"""
        conditions = []
        
        if 'user_id' in filters:
            conditions.append("d.user_id = :user_id")
        
        if 'document_id' in filters:
            conditions.append("de.document_id = :document_id")
        
        if 'min_similarity' in filters:
            conditions.append("1 - (de.embedding <=> :query_embedding) >= :min_similarity")
        
        return " AND ".join(conditions) if conditions else "1=1"
```

### 索引优化策略

```python
# query_optimizer.py
class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        self.index_strategies = {
            'ivfflat': self._optimize_ivfflat,
            'hnsw': self._optimize_hnsw,
            'brute_force': self._optimize_brute_force
        }
    
    async def optimize_search(self, query_embedding: List[float], 
                            expected_results: int = 10) -> Dict[str, Any]:
        """优化搜索查询"""
        
        # 根据查询特征选择最优策略
        strategy = self._select_strategy(query_embedding, expected_results)
        
        return await self.index_strategies[strategy](query_embedding, expected_results)
    
    def _select_strategy(self, query_embedding: List[float], 
                        expected_results: int) -> str:
        """选择搜索策略"""
        
        # 简单的策略选择逻辑
        if expected_results <= 10:
            return 'ivfflat'
        elif expected_results <= 100:
            return 'hnsw'
        else:
            return 'brute_force'
    
    async def _optimize_ivfflat(self, query_embedding: List[float], 
                              expected_results: int) -> Dict[str, Any]:
        """IVFFLAT索引优化"""
        
        # 计算最佳probes参数
        probes = max(1, expected_results // 10)
        
        return {
            'index_type': 'ivfflat',
            'probes': probes,
            'sql_hint': f"SET ivfflat.probes = {probes};"
        }
```

## 相似度计算算法

### 多种相似度度量

```python
# similarity_calculator.py
import numpy as np
from scipy.spatial.distance import cosine

class SimilarityCalculator:
    """相似度计算器"""
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """余弦相似度"""
        return 1 - cosine(vec1, vec2)
    
    @staticmethod
    def euclidean_similarity(vec1: List[float], vec2: List[float]) -> float:
        """欧氏距离相似度（转换为相似度）"""
        distance = np.linalg.norm(np.array(vec1) - np.array(vec2))
        return 1 / (1 + distance)  # 转换为相似度
    
    @staticmethod
    def dot_product_similarity(vec1: List[float], vec2: List[float]) -> float:
        """点积相似度"""
        return np.dot(vec1, vec2)
    
    @staticmethod
    def hybrid_similarity(vec1: List[float], vec2: List[float], 
                         weights: Dict[str, float] = None) -> float:
        """混合相似度"""
        
        if weights is None:
            weights = {'cosine': 0.7, 'euclidean': 0.3}
        
        cosine_sim = SimilarityCalculator.cosine_similarity(vec1, vec2)
        euclidean_sim = SimilarityCalculator.euclidean_similarity(vec1, vec2)
        
        return (weights['cosine'] * cosine_sim + 
                weights['euclidean'] * euclidean_sim)
```

### 法律文档特定相似度

```python
class LegalSimilarityCalculator(SimilarityCalculator):
    """法律文档专用相似度计算器"""
    
    def __init__(self):
        self.legal_terms = self._load_legal_terms()
    
    def legal_semantic_similarity(self, vec1: List[float], vec2: List[float],
                                text1: str, text2: str) -> float:
        """法律语义相似度"""
        
        # 基础向量相似度
        base_similarity = self.cosine_similarity(vec1, vec2)
        
        # 法律术语权重
        term_weight = self._calculate_legal_term_weight(text1, text2)
        
        # 结合法律特征的相似度计算
        return base_similarity * (1 + term_weight)
    
    def _calculate_legal_term_weight(self, text1: str, text2: str) -> float:
        """计算法律术语权重"""
        
        terms1 = self._extract_legal_terms(text1)
        terms2 = self._extract_legal_terms(text2)
        
        if not terms1 or not terms2:
            return 0.0
        
        # 计算术语重叠度
        overlap = len(set(terms1) & set(terms2)) / len(set(terms1) | set(terms2))
        
        return overlap * 0.3  # 最大增加30%权重
```

## 结果排序和重排序

### 多因素排序算法

```python
# result_ranker.py
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class RankingFactors:
    """排序因素"""
    similarity_score: float = 0.0
    document_freshness: float = 0.0  # 文档新鲜度
    document_quality: float = 0.0    # 文档质量
    user_relevance: float = 0.0      # 用户相关性
    legal_importance: float = 0.0    # 法律重要性

class ResultRanker:
    """结果排序器"""
    
    def __init__(self, weights: Dict[str, float] = None):
        if weights is None:
            self.weights = {
                'similarity': 0.5,
                'freshness': 0.2,
                'quality': 0.15,
                'user_relevance': 0.1,
                'legal_importance': 0.05
            }
        else:
            self.weights = weights
    
    async def rerank_results(self, results: List[SearchResult], 
                           query_context: Dict[str, Any]) -> List[SearchResult]:
        """重排序结果"""
        
        ranked_results = []
        
        for result in results:
            factors = await self._calculate_ranking_factors(result, query_context)
            final_score = self._calculate_final_score(factors)
            
            # 创建新的结果对象（带排序分数）
            ranked_result = SearchResult(
                **result.__dict__,
                rerank_score=final_score
            )
            ranked_results.append(ranked_result)
        
        # 按最终分数排序
        ranked_results.sort(key=lambda x: x.rerank_score, reverse=True)
        
        return ranked_results
    
    async def _calculate_ranking_factors(self, result: SearchResult, 
                                       context: Dict[str, Any]) -> RankingFactors:
        """计算排序因素"""
        
        factors = RankingFactors()
        
        # 相似度分数
        factors.similarity_score = result.similarity_score
        
        # 文档新鲜度（基于创建时间）
        factors.document_freshness = await self._calculate_freshness(result)
        
        # 文档质量（基于元数据）
        factors.document_quality = await self._calculate_quality(result)
        
        # 用户相关性
        factors.user_relevance = await self._calculate_user_relevance(result, context)
        
        # 法律重要性
        factors.legal_importance = await self._calculate_legal_importance(result)
        
        return factors
    
    def _calculate_final_score(self, factors: RankingFactors) -> float:
        """计算最终分数"""
        
        return (
            self.weights['similarity'] * factors.similarity_score +
            self.weights['freshness'] * factors.document_freshness +
            self.weights['quality'] * factors.document_quality +
            self.weights['user_relevance'] * factors.user_relevance +
            self.weights['legal_importance'] * factors.legal_importance
        )
```

### 法律特定排序策略

```python
class LegalResultRanker(ResultRanker):
    """法律结果排序器"""
    
    def __init__(self):
        # 法律场景的特殊权重
        super().__init__({
            'similarity': 0.4,
            'freshness': 0.15,
            'quality': 0.2,
            'user_relevance': 0.1,
            'legal_importance': 0.15
        })
    
    async def _calculate_legal_importance(self, result: SearchResult) -> float:
        """计算法律重要性"""
        
        importance_score = 0.0
        
        # 基于法律条款类型的重要性
        content = result.chunk_content.lower()
        
        if any(keyword in content for keyword in ['宪法', '基本法']):
            importance_score += 0.3
        
        if any(keyword in content for keyword in ['刑法', '刑事诉讼法']):
            importance_score += 0.2
        
        if any(keyword in content for keyword in ['民法典', '合同法']):
            importance_score += 0.15
        
        # 基于条款编号的重要性（如第一条通常更重要）
        if '第一条' in content or '第1条' in content:
            importance_score += 0.1
        
        return min(importance_score, 1.0)
```

## 缓存和性能优化

### 查询结果缓存

```python
# cache_manager.py
import hashlib
import json

class SearchCache:
    """搜索缓存管理器"""
    
    def __init__(self, redis_client, ttl: int = 300):  # 5分钟
        self.redis = redis_client
        self.ttl = ttl
    
    async def get_cached_results(self, query_embedding: List[float], 
                               filters: Dict) -> Optional[List[SearchResult]]:
        """获取缓存的搜索结果"""
        
        cache_key = self._generate_cache_key(query_embedding, filters)
        cached = await self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        return None
    
    async def cache_results(self, query_embedding: List[float], 
                          filters: Dict, results: List[SearchResult]):
        """缓存搜索结果"""
        
        cache_key = self._generate_cache_key(query_embedding, filters)
        await self.redis.setex(
            cache_key,
            self.ttl,
            json.dumps([r.__dict__ for r in results])
        )
    
    def _generate_cache_key(self, query_embedding: List[float], 
                          filters: Dict) -> str:
        """生成缓存键"""
        
        # 使用嵌入向量的哈希和过滤条件生成唯一键
        embedding_hash = hashlib.md5(
            json.dumps(query_embedding).encode()
        ).hexdigest()
        
        filter_hash = hashlib.md5(
            json.dumps(filters, sort_keys=True).encode()
        ).hexdigest()
        
        return f"search:{embedding_hash}:{filter_hash}"
```

### 性能监控

```python
# performance_monitor.py
import time
from prometheus_client import Histogram, Counter

class SearchPerformanceMonitor:
    """搜索性能监控器"""
    
    search_duration = Histogram('search_duration_seconds', '搜索耗时')
    search_requests = Counter('search_requests_total', '搜索请求总数')
    cache_hits = Counter('search_cache_hits_total', '缓存命中次数')
    
    def __init__(self):
        self.metrics = {}
    
    async def track_search(self, search_func, *args, **kwargs):
        """跟踪搜索性能"""
        
        self.search_requests.inc()
        start_time = time.time()
        
        try:
            result = await search_func(*args, **kwargs)
            duration = time.time() - start_time
            
            self.search_duration.observe(duration)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.search_duration.observe(duration)
            raise e
    
    def record_cache_hit(self):
        """记录缓存命中"""
        self.cache_hits.inc()
```

## 高级搜索功能

### 混合搜索

```python
# hybrid_searcher.py
class HybridSearcher:
    """混合搜索器（向量搜索 + 关键词搜索）"""
    
    def __init__(self, vector_searcher: BaseVectorSearcher, 
                 keyword_searcher: Any):
        self.vector_searcher = vector_searcher
        self.keyword_searcher = keyword_searcher
    
    async def hybrid_search(self, query: str, query_embedding: List[float],
                          top_k: int = 10) -> List[SearchResult]:
        """混合搜索"""
        
        # 并行执行两种搜索
        vector_results = await self.vector_searcher.search_similar(
            query_embedding, top_k * 2
        )
        
        keyword_results = await self.keyword_searcher.search(
            query, top_k * 2
        )
        
        # 结果融合
        fused_results = self._fuse_results(
            vector_results, keyword_results, top_k
        )
        
        return fused_results
    
    def _fuse_results(self, vector_results: List[SearchResult],
                     keyword_results: List[SearchResult], 
                     top_k: int) -> List[SearchResult]:
        """融合搜索结果"""
        
        # 简单的加权融合算法
        all_results = {}
        
        # 处理向量搜索结果
        for i, result in enumerate(vector_results):
            score = result.similarity_score * 0.7  # 向量搜索权重
            if result.embedding_id in all_results:
                all_results[result.embedding_id].score += score
            else:
                result.rerank_score = score
                all_results[result.embedding_id] = result
        
        # 处理关键词搜索结果
        for i, result in enumerate(keyword_results):
            score = (1 - i / len(keyword_results)) * 0.3  # 关键词搜索权重
            if result.embedding_id in all_results:
                all_results[result.embedding_id].rerank_score += score
            else:
                result.rerank_score = score
                all_results[result.embedding_id] = result
        
        # 按最终分数排序
        sorted_results = sorted(
            all_results.values(), 
            key=lambda x: x.rerank_score, 
            reverse=True
        )
        
        return sorted_results[:top_k]
```

## 配置和部署

### 数据库索引配置

```sql
-- 创建向量索引
CREATE INDEX IF NOT EXISTS embedding_ivfflat_idx 
ON document_embeddings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 创建HNSW索引（PostgreSQL 14+）
CREATE INDEX IF NOT EXISTS embedding_hnsw_idx 
ON document_embeddings 
USING hnsw (embedding vector_cosine_ops);

-- 创建复合索引
CREATE INDEX IF NOT EXISTS idx_document_embeddings_user_doc 
ON document_embeddings (document_id, chunk_index);
```

### 性能调优参数

```python
# 搜索配置
@dataclass
class SearchConfig:
    """搜索配置"""
    default_top_k: int = 10
    max_top_k: int = 100
    min_similarity_threshold: float = 0.6
    cache_ttl: int = 300
    enable_cache: bool = True
    enable_reranking: bool = True
    hybrid_search_weight: Dict[str, float] = None
    
    def __post_init__(self):
        if self.hybrid_search_weight is None:
            self.hybrid_search_weight = {'vector': 0.7, 'keyword': 0.3}
```

## 测试策略

### 搜索准确性测试

```python
class SearchAccuracyTest:
    """搜索准确性测试"""
    
    def test_semantic_search_accuracy(self):
        """测试语义搜索准确性"""
        # 使用已知的相关文档测试搜索准确性
        pass
    
    def test_ranking_effectiveness(self):
        """测试排序效果"""
        # 验证排序算法是否能将最相关的结果排在前面
        pass
    
    def test_hybrid_search_improvement(self):
        """测试混合搜索改进"""
        # 比较纯向量搜索和混合搜索的效果
        pass
```

### 性能测试

```python
class PerformanceTest:
    """性能测试"""
    
    def test_search_latency(self):
        """测试搜索延迟"""
        # 测试不同规模数据集的搜索响应时间
        pass
    
    def test_concurrent_searches(self):
        """测试并发搜索"""
        # 测试系统在高并发下的表现
        pass
    
    def test_cache_performance(self):
        """测试缓存性能"""
        # 测试缓存对搜索性能的影响
        pass
```

## 总结

向量检索服务为智能法律助手提供了强大的语义搜索能力：

1. **高精度检索**：通过先进的相似度算法确保检索准确性
2. **智能排序**：结合多种因素进行结果重排序
3. **高性能优化**：通过索引优化和缓存机制确保快速响应
4. **法律专业化**：针对法律文档特性进行特殊优化
5. **可扩展架构**：支持大规模向量数据的高效处理

该设计为RAG系统的核心检索功能提供了坚实的技术基础。