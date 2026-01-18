"""
分块器适配器 - 桥接LangChain和现有分块器
"""
from typing import List, Dict, Any
from abc import ABC, abstractmethod
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..document_processor.base_processor import DocumentChunk
from ..document_processor.chunk_strategies import LegalDocumentChunker

class BaseChunkerAdapter(ABC):
    """分块器适配基类"""

    @abstractmethod
    async def chunk_document(self, text: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """分块文档"""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        pass


class LangChainSplitterAdapter(BaseChunkerAdapter):
    """LangChain TextSpiltter适配器"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化LangChain分块器

        Args:
            chunk_size: 分块大小
            chunk_overlap: 重叠大小
        """

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # 创建LangChain TextSplitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""],
            length_function=len,
        )

    async def chunk_document(self, text: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """
        使用LangChain分块器分割文档

        Args:
            text: 要分割的文本
            metadata: 元数据

        Returns:
            分块列表
        """

        # 使用LangChain分割
        lang_docs = self.splitter.split_text(text)

        # 转换为DocumentChunk对象
        chunks = []
        for idx, lang_doc in enumerate(lang_docs):
            chunk = DocumentChunk(
                chunk_id=f"langchain_chunk_{idx}",
                content=lang_doc,
                chunk_index=idx,
                metadata={
                    'strategy': 'langchain',
                    'chunk_size': len(lang_doc),
                    **(metadata or {})
                }
            )
            chunks.append(chunk)
        return chunks

    def get_strategy_name(self) -> str:
        return "langchain"


class LegalChunkerAdapter(BaseChunkerAdapter):
    """法律分块器适配器"""

    def __init__(self, max_chunk_size: int = 1200):
        """
        初始化法律分块器

        Args:
            max_chunk_size: 最大分块大小
        """
        self.max_chunk_size = max_chunk_size
        self.legal_chunker = LegalDocumentChunker(max_chunk_size=max_chunk_size)

    async def chunk_document(self, text: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """
        使用法律分块器分割文档

        Args:
            text: 要分割的文本
            metadata: 元数据

        Returns:
            分块列表
        """
        # 使用LegalDocumentChunker分割
        chunks = self.legal_chunker.chunk_text(text)

        # 合并元数据（包括图片信息）
        for chunk in chunks:
            if metadata:
                chunk.metadata.update(metadata)

            # 检查是否有图片信息，并关联到分块
            if metadata and metadata.get('has_images'):
                images_by_page = metadata.get('images_by_page', {})
                page_number = chunk.metadata.get('page_number')

                if page_number and page_number in images_by_page:
                    # 将该页面的所有图片URL添加到分块metadata
                    page_images = images_by_page[page_number]
                    image_urls = [img['image_url'] for img in page_images]

                    if image_urls:
                        chunk.metadata['image_urls'] = image_urls
                        chunk.metadata['primary_image-url'] = image_urls[0]     # 主要图片URL

        return chunks

    def get_strategy_name(self) -> str:
        return "legal"


class HybridChunkerAdapter(BaseChunkerAdapter):
    """混合分块器 - 结合LangChain和Legal分块器"""

    def __init__(self, langchain_adapter: LangChainSplitterAdapter,
                 legal_adapter: LegalChunkerAdapter):
        """
        初始化混合分块器

        Args:
            langchain_adapter: LangChain适配器
            legal_adapter: 法律分块器适配器
        """
        self.langchain_adapter = langchain_adapter
        self.legal_adapter = legal_adapter

    async def chunk_document(self, text: str, metadata: Dict[str, Any] = None,
                             primary_strategy: str = "legal") -> List[DocumentChunk]:
        """
        混合分块策略

        Args:
            text: 要分割的文本
            metadata: 元数据
            primary_strategy: 主策略 (legal/langchain)

        Returns:
            分块列表
        """
        # 根据主策略选择分块器
        if primary_strategy == "legal":
            return await self.legal_adapter.chunk_document(text, metadata)
        elif primary_strategy == "langchain":
            return await self.langchain_adapter.chunk_document(text, metadata)
        else:
            # 默认使用法律分块器
            return await self.legal_adapter.chunk_document(text, metadata)

    def get_strategy_name(self) -> str:
        return "hybrid"


class ChunkerAdapter:
    """统一的分块器适配器接口"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化分块器适配器

        Args:
            config: 配置字典
        """
        config = config or {}

        # 创建适配器
        self.langchain_adapter = LangChainSplitterAdapter(
            chunk_size=config.get("chunk_size", 1000),
            chunk_overlap=config.get("chunk_overlap", 200)
        )

        self.legal_adapter = LegalChunkerAdapter(
            max_chunk_size=config.get("max_chunk_size", 1200)
        )

        self.hybrid_adapter = HybridChunkerAdapter(
            self.langchain_adapter,
            self.legal_adapter
        )

        # 默认策略
        self.default_strategy = config.get('default_strategy', "hybrid")

    async def chunk_document(self, text: str, strategy: str = None,
                             metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """
        分块文档

        Args:
            text: 要分割的文本
            strategy: 分块策略
            metadata: 元数据

        Returns:
            分块列表
        """
        strategy = strategy or self.default_strategy

        if strategy == "langchain":
            return await self.langchain_adapter.chunk_document(text, metadata)
        elif strategy == "legal":
            return await self.legal_adapter.chunk_document(text, metadata)
        elif strategy == "hybrid":
            return await self.hybrid_adapter.chunk_document(
                text,
                metadata,
                primary_strategy=metadata.get('primary_strategy', 'legal') if metadata else 'legal'
            )
        else:
            raise ValueError(f"不支持的策略: {strategy}")

    def get_available_strategies(self) -> List[str]:
        """获取可用的策略列表"""
        return ["langchain", "legal", "hybrid"]
