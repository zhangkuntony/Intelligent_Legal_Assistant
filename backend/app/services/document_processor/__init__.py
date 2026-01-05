"""智能法律助手 - 文件处理模块。提供多格式文档处理、智能分块和预处理功能"""

from .base_processor import BaseDocumentProcessor, ProcessedDocument, DocumentChunk, ProcessingStatus, ProcessingStats
from .pdf_processor import PDFProcessor
from .word_processor import WordProcessor  
from .text_processor import TextProcessor
from .chunk_strategies import (
    ChunkingStrategy, 
    FixedSizeChunker, 
    SemanticChunker, 
    LegalDocumentChunker
)
from .preprocessors import TextPreprocessor, LegalTextProcessor
from .exceptions import (
    DocumentProcessingError,
    UnsupportedFormatError,
    CorruptedFileError,
    ExtractionError
)
from .processor_factory import DocumentProcessorFactory
from .batch_processor import BatchProcessor
from .document_cache import DocumentCache
from .processing_monitor import ProcessingMonitor

__all__ = [
    # 基础类
    "BaseDocumentProcessor", "ProcessedDocument", "DocumentChunk", 
    "ProcessingStatus", "ProcessingStats",
    
    # 处理器
    "PDFProcessor", "WordProcessor", "TextProcessor",
    
    # 分块策略
    "ChunkingStrategy", "FixedSizeChunker", "SemanticChunker", "LegalDocumentChunker",
    
    # 预处理器
    "TextPreprocessor", "LegalTextProcessor",
    
    # 异常类
    "DocumentProcessingError", "UnsupportedFormatError", "CorruptedFileError", "ExtractionError",
    
    # 工厂和工具类
    "DocumentProcessorFactory", "BatchProcessor", "DocumentCache", "ProcessingMonitor"
]