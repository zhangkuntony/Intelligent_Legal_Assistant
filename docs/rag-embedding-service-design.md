# 智能法律助手 - 向量化服务设计文档

## 概述

向量化服务是RAG系统的核心组件，负责将文本内容转换为高维向量表示，为后续的语义搜索和相似度计算提供基础。本服务集成OpenAI Embedding API，并支持多种向量化策略和优化技术。

## 设计目标

- **高性能向量化**：支持批量处理和异步操作
- **多模型支持**：可配置不同的嵌入模型
- **缓存优化**：减少重复计算，提高响应速度
- **错误容错**：完善的错误处理和重试机制
- **监控统计**：详细的性能监控和使用统计

## 架构设计

### 模块结构

```
backend/app/services/embedding_service/
├── __init__.py              # 模块初始化
├── base_embedder.py         # 抽象基类
├── openai_embedder.py       # OpenAI嵌入服务
├── local_embedder.py        # 本地嵌入模型
├── batch_processor.py       # 批量处理
├── cache_manager.py         # 缓存管理
├── model_registry.py        # 模型注册表
├── exceptions.py            # 异常定义
└── utils.py                 # 工具函数
```

### 核心接口设计

```python
# 嵌入器基类接口
class BaseEmbedder(ABC):
    """嵌入器基类"""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """将单个文本转换为向量"""
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量转换文本为向量"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """获取模型信息"""
        pass

# 向量化结果数据结构
@dataclass
class EmbeddingResult:
    """向量化结果"""
    text: str
    embedding: List[float]
    model_name: str
    dimensions: int
    processing_time: float
    token_count: int

@dataclass
class BatchEmbeddingResult:
    """批量向量化结果"""
    results: List[EmbeddingResult]
    total_tokens: int
    total_time: float
    success_count: int
    failed_count: int
```

## 嵌入模型集成

### OpenAI嵌入服务

```python
class OpenAIEmbedder(BaseEmbedder):
    """OpenAI嵌入服务实现"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self.dimensions = self._get_model_dimensions(model)
    
    async def embed_text(self, text: str) -> List[float]:
        """使用OpenAI API生成嵌入向量"""
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except openai.APIError as e:
            raise EmbeddingError(f"OpenAI API错误: {e}")
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量处理文本嵌入"""
        # OpenAI API支持批量处理
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [item.embedding for item in response.data]
    
    def _get_model_dimensions(self, model: str) -> int:
        """获取模型维度信息"""
        model_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072
        }
        return model_dimensions.get(model, 1536)
```

### 本地嵌入模型（备选方案）

```python
class LocalEmbedder(BaseEmbedder):
    """本地嵌入模型实现"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.dimensions = self.model.get_sentence_embedding_dimension()
    
    async def embed_text(self, text: str) -> List[float]:
        """使用本地模型生成嵌入"""
        embedding = self.model.encode([text])[0]
        return embedding.tolist()
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量处理"""
        embeddings = self.model.encode(texts)
        return [embedding.tolist() for embedding in embeddings]
```

## 批量处理优化

### 智能批处理

```python
class BatchEmbeddingProcessor:
    """批量嵌入处理器"""
    
    def __init__(self, embedder: BaseEmbedder, max_batch_size: int = 100):
        self.embedder = embedder
        self.max_batch_size = max_batch_size
    
    async def process_large_batch(self, texts: List[str]) -> BatchEmbeddingResult:
        """处理大批量文本"""
        batches = self._split_into_batches(texts)
        results = []
        total_tokens = 0
        
        for batch in batches:
            batch_result = await self.embedder.embed_batch(batch)
            results.extend(batch_result)
            total_tokens += sum(len(text) for text in batch)
        
        return BatchEmbeddingResult(
            results=results,
            total_tokens=total_tokens,
            total_time=0,  # 实际计算
            success_count=len(results),
            failed_count=0
        )
    
    def _split_into_batches(self, texts: List[str]) -> List[List[str]]:
        """将文本列表分割成批次"""
        return [texts[i:i + self.max_batch_size] 
                for i in range(0, len(texts), self.max_batch_size)]
```

### 令牌计数和限制

```python
class TokenCounter:
    """令牌计数器（用于OpenAI API限制）"""
    
    def __init__(self, max_tokens_per_request: int = 8191):
        self.max_tokens = max_tokens_per_request
    
    def count_tokens(self, text: str) -> int:
        """估算文本的令牌数量"""
        # 使用tiktoken进行精确计数
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    
    def validate_batch(self, texts: List[str]) -> bool:
        """验证批次是否超过令牌限制"""
        total_tokens = sum(self.count_tokens(text) for text in texts)
        return total_tokens <= self.max_tokens
```

## 缓存机制

### 向量缓存设计

```python
class EmbeddingCache:
    """嵌入向量缓存管理器"""
    
    def __init__(self, redis_client=None, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl  # 缓存过期时间（秒）
        self.local_cache = {}  # 本地内存缓存
    
    async def get_cached_embedding(self, text_hash: str) -> Optional[List[float]]:
        """获取缓存的嵌入向量"""
        # 先检查本地缓存
        if text_hash in self.local_cache:
            return self.local_cache[text_hash]
        
        # 再检查Redis缓存
        if self.redis:
            cached = await self.redis.get(f"embedding:{text_hash}")
            if cached:
                embedding = json.loads(cached)
                self.local_cache[text_hash] = embedding
                return embedding
        
        return None
    
    async def cache_embedding(self, text_hash: str, embedding: List[float]):
        """缓存嵌入向量"""
        # 更新本地缓存
        self.local_cache[text_hash] = embedding
        
        # 更新Redis缓存
        if self.redis:
            await self.redis.setex(
                f"embedding:{text_hash}",
                self.ttl,
                json.dumps(embedding)
            )
    
    def generate_text_hash(self, text: str) -> str:
        """生成文本哈希（用于缓存键）"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
```

### 缓存策略配置

```python
@dataclass
class CacheConfig:
    """缓存配置"""
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1小时
    max_local_cache_size: int = 10000  # 本地缓存最大条目
    use_redis: bool = True
    redis_prefix: str = "embedding"
```

## 错误处理和重试机制

### 异常定义

```python
class EmbeddingError(Exception):
    """嵌入处理异常基类"""
    pass

class APIQuotaExceededError(EmbeddingError):
    """API配额超限异常"""
    pass

class ModelNotAvailableError(EmbeddingError):
    """模型不可用异常"""
    pass

class TokenLimitExceededError(EmbeddingError):
    """令牌限制超限异常"""
    pass
```

### 智能重试机制

```python
class RetryManager:
    """重试管理器"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.5):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs):
        """带重试的执行"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except (APIQuotaExceededError, TokenLimitExceededError) as e:
                # 这些错误不应该重试
                raise e
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_factor ** attempt)
                else:
                    raise last_exception
```

## 性能监控和统计

### 监控指标

```python
@dataclass
class EmbeddingMetrics:
    """嵌入服务指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_processed: int = 0
    average_processing_time: float = 0.0
    cache_hit_rate: float = 0.0

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics = EmbeddingMetrics()
        self.request_times: List[float] = []
    
    def record_request(self, success: bool, tokens: int, processing_time: float):
        """记录请求指标"""
        self.metrics.total_requests += 1
        
        if success:
            self.metrics.successful_requests += 1
            self.metrics.total_tokens_processed += tokens
            self.request_times.append(processing_time)
            
            # 更新平均处理时间
            if self.request_times:
                self.metrics.average_processing_time = (
                    sum(self.request_times) / len(self.request_times)
                )
        else:
            self.metrics.failed_requests += 1
    
    def record_cache_hit(self, hit: bool):
        """记录缓存命中"""
        # 计算缓存命中率
        pass
```

## 配置管理

### 服务配置

```python
@dataclass
class EmbeddingServiceConfig:
    """嵌入服务配置"""
    # API配置
    openai_api_key: str
    default_model: str = "text-embedding-ada-002"
    
    # 性能配置
    max_batch_size: int = 100
    max_tokens_per_request: int = 8191
    request_timeout: int = 30
    
    # 重试配置
    max_retries: int = 3
    backoff_factor: float = 1.5
    
    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 3600
    
    # 监控配置
    enable_metrics: bool = True
    metrics_retention_days: int = 30
```

## 模型注册表

### 多模型管理

```python
class ModelRegistry:
    """模型注册表"""
    
    def __init__(self):
        self._models: Dict[str, BaseEmbedder] = {}
        self._default_model: Optional[str] = None
    
    def register_model(self, name: str, embedder: BaseEmbedder, 
                      is_default: bool = False):
        """注册模型"""
        self._models[name] = embedder
        if is_default:
            self._default_model = name
    
    def get_model(self, name: Optional[str] = None) -> BaseEmbedder:
        """获取模型实例"""
        model_name = name or self._default_model
        if model_name not in self._models:
            raise ModelNotAvailableError(f"模型 {model_name} 未注册")
        return self._models[model_name]
    
    def list_models(self) -> List[str]:
        """列出所有可用模型"""
        return list(self._models.keys())
```

## 集成接口

### 与现有系统集成

```python
class EmbeddingService:
    """嵌入服务主类"""
    
    def __init__(self, config: EmbeddingServiceConfig):
        self.config = config
        self.cache = EmbeddingCache()
        self.metrics = MetricsCollector()
        self.retry_manager = RetryManager()
        
        # 初始化模型
        self.model_registry = ModelRegistry()
        self._initialize_models()
    
    async def embed_document_chunks(self, chunks: List[DocumentChunk]) -> List[EmbeddingResult]:
        """为文档分块生成嵌入向量"""
        texts = [chunk.content for chunk in chunks]
        
        # 检查缓存
        cached_results = await self._get_cached_embeddings(texts)
        uncached_texts = [text for text, cached in zip(texts, cached_results) 
                         if cached is None]
        
        # 处理未缓存的文本
        if uncached_texts:
            new_embeddings = await self._embed_uncached_texts(uncached_texts)
            # 更新缓存
            await self._cache_new_embeddings(uncached_texts, new_embeddings)
        
        # 合并结果
        return self._merge_results(texts, cached_results, new_embeddings)
    
    async def _embed_uncached_texts(self, texts: List[str]) -> List[List[float]]:
        """处理未缓存的文本"""
        embedder = self.model_registry.get_model()
        
        # 使用重试机制
        return await self.retry_manager.execute_with_retry(
            embedder.embed_batch, texts
        )
```

## 测试策略

### 单元测试

```python
class TestEmbeddingService:
    """嵌入服务测试"""
    
    def test_single_embedding(self):
        """测试单个文本嵌入"""
        pass
    
    def test_batch_embedding(self):
        """测试批量嵌入"""
        pass
    
    def test_cache_functionality(self):
        """测试缓存功能"""
        pass
    
    def test_error_handling(self):
        """测试错误处理"""
        pass
```

### 性能测试

```python
class PerformanceTest:
    """性能测试"""
    
    def test_large_batch_processing(self):
        """测试大批量处理性能"""
        pass
    
    def test_cache_performance(self):
        """测试缓存性能"""
        pass
```

## 部署考虑

### 依赖管理

```txt
# requirements.txt 新增依赖
openai>=1.0.0
redis>=4.5.0
sentence-transformers>=2.2.0
tiktoken>=0.5.0
```

### 资源需求

- **API配额**：需要足够的OpenAI API配额
- **网络连接**：稳定的互联网连接访问OpenAI API
- **内存**：本地缓存需要适量内存
- **Redis**：建议使用Redis作为分布式缓存

## 总结

向量化服务是RAG系统的关键技术组件，设计良好的向量化服务能够：

1. **提高系统性能**：通过缓存和批量处理优化性能
2. **增强系统稳定性**：通过重试机制和错误处理确保可靠性
3. **支持业务扩展**：通过多模型支持满足不同需求
4. **提供监控能力**：通过详细指标支持系统运维

该设计为智能法律助手的语义搜索功能提供了强大的向量化基础。