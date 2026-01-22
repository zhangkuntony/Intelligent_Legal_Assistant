"""
LangChain配置管理
"""
from dataclasses import dataclass
from typing import Dict, Any
import os
from .config import settings

@dataclass
class LangChainConfig:
    """LangChain配置类"""

    # 嵌入配置
    embedding_dimension: int = 2048

    # 分块配置
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # 检索配置
    similarity_top_k: int = 5
    similarity_threshold: float = 0.6

    # 策略配置
    default_strategy: str = "hybrid"                # hybrid, legal_only, langchain_only
    enable_cache: bool = True
    cache_ttl: int = 3600

    # 向量数据库配置
    vector_store_type: str = "pgvector"             # pgvector, chromadb, milvus
    collection_name: str = "legal_documents"

    def __post_init__(self):
        """初始化后处理"""

        self.api_key = settings.LLM_API_KEY if hasattr(settings, "LLM_API_KEY") else os.getenv("LLM_API_KEY")
        self.embedding_model = settings.EMBEDDING_MODEL if hasattr(settings, "EMBEDDING_MODEL") else "doubao-embedding-text-240715"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'embedding_model': self.embedding_model,
            'embedding_dimension': self.embedding_dimension,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'similarity_top_k': self.similarity_top_k,
            'similarity_threshold': self.similarity_threshold,
            'default_strategy': self.default_strategy,
            'enable_cache': self.enable_cache,
            'cache_ttl': self.cache_ttl,
            'vector_store_type': self.vector_store_type,
            'collection_name': self.collection_name,
        }

# 默认配置实例
default_langchain_config = LangChainConfig()