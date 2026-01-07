"""
文档处理器工厂
"""

from typing import Dict, Any, Type, Optional
from pathlib import Path

from .base_processor import BaseDocumentProcessor
from .pdf_processor import PDFProcessor
from .word_processor import WordProcessor
from .text_processor import TextProcessor
from .exceptions import UnsupportedFormatError, DependencyError


class DocumentProcessorFactory:
    """文档处理器工厂类"""

    # 文件扩展名到处理器类的映射
    _processor_registry: Dict[str, Type[BaseDocumentProcessor]] = {
        '.pdf': PDFProcessor,
        '.docx': WordProcessor,
        '.doc': WordProcessor,
        '.txt': TextProcessor,
        '.md': TextProcessor,
        '.markdown': TextProcessor,
        '.rst': TextProcessor,
        '.log': TextProcessor,
    }

    # MIME类型到处理器类的映射
    _mime_type_registry: Dict[str, Type[BaseDocumentProcessor]] = {
        'application/pdf': PDFProcessor,
        'application/msword': WordProcessor,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': WordProcessor,
        'text/plain': TextProcessor,
        'text/markdown': TextProcessor,
        'text/x-rst': TextProcessor,
    }

    @classmethod
    def create_processor(cls, file_path: str = None, mime_type: str = None,
                         config: Dict[str, Any] = None) -> BaseDocumentProcessor:
        """
        创建适合文件类型的处理器

        Args:
            file_path: 文件路径
            mime_type: MIME类型
            config: 处理器配置

        Returns:
            BaseDocumentProcessor: 适合的文档处理器实例

        Raises:
            UnsupportedFormatError: 不支持的文件格式
            DependencyError: 缺少必要依赖
        """
        # 确定文件类型
        file_type = cls._determine_file_type(file_path, mime_type)

        if not file_type:
            raise UnsupportedFormatError(
                file_path or "unknown",
                list(cls._processor_registry.keys())
            )

        # 获取处理器类
        processor_class = cls._get_processor_class(file_type)

        if not processor_class:
            raise UnsupportedFormatError(
                file_path or "unknown",
                list(cls._processor_registry.keys())
            )

        # 创建处理器实例
        try:
            processor = processor_class(config or {})
            return processor

        except ImportError as e:
            # 处理依赖缺失错误
            raise DependencyError(
                str(e).split("'")[1] if "'" in str(e) else "unknown",
                f"pip install {str(e).split(' ')[-1]}" if " " in str(e) else "pip install <package>"
            )

        except Exception as e:
            # 其他初始化错误
            raise RuntimeError(f"处理器初始化失败: {str(e)}")

    @classmethod
    def _determine_file_type(cls, file_path: str = None, mime_type: str = None) -> Optional[str]:
        """确定文件类型"""
        # 优先使用MIME类型
        if mime_type and mime_type in cls._mime_type_registry:
            return mime_type

        # 使用文件扩展名
        if file_path:
            file_ext = Path(file_path).suffix.lower()
            if file_ext in cls._processor_registry:
                return file_ext

        return None

    @classmethod
    def _get_processor_class(cls, file_type: str) -> Optional[Type[BaseDocumentProcessor]]:
        """获取处理器类"""
        # 尝试MIME类型映射
        if file_type in cls._mime_type_registry:
            return cls._mime_type_registry[file_type]

        # 尝试文件扩展名映射
        if file_type in cls._processor_registry:
            return cls._processor_registry[file_type]

        return None

    @classmethod
    def get_supported_formats(cls) -> Dict[str, list]:
        """获取支持的文件格式列表"""
        return {
            'extensions': list(cls._processor_registry.keys()),
            'mime_types': list(cls._mime_type_registry.keys())
        }

    @classmethod
    def is_format_supported(cls, file_path: str = None, mime_type: str = None) -> bool:
        """检查是否支持该文件格式"""
        file_type = cls._determine_file_type(file_path, mime_type)
        return file_type is not None

    @classmethod
    def register_processor(cls, file_ext: str, processor_class: Type[BaseDocumentProcessor],
                           mime_type: str = None):
        """注册新的处理器"""
        if not issubclass(processor_class, BaseDocumentProcessor):
            raise ValueError("处理器类必须继承自 BaseDocumentProcessor")

        # 注册文件扩展名
        cls._processor_registry[file_ext.lower()] = processor_class

        # 注册MIME类型（如果提供）
        if mime_type:
            cls._mime_type_registry[mime_type.lower()] = processor_class

    @classmethod
    def unregister_processor(cls, file_ext: str, mime_type: str = None):
        """取消注册处理器"""
        # 取消注册文件扩展名
        if file_ext.lower() in cls._processor_registry:
            del cls._processor_registry[file_ext.lower()]

        # 取消注册MIME类型
        if mime_type and mime_type.lower() in cls._mime_type_registry:
            del cls._mime_type_registry[mime_type.lower()]

    @classmethod
    def get_processor_info(cls, file_type: str) -> Dict[str, Any]:
        """获取处理器信息"""
        processor_class = cls._get_processor_class(file_type)

        if not processor_class:
            return None

        # 创建临时实例来获取信息
        try:
            processor = processor_class({})
            return {
                'class_name': processor_class.__name__,
                'module': processor_class.__module__,
                'supported_formats': getattr(processor, 'supported_formats', []),
                'description': getattr(processor_class, '__doc__', '').strip() if processor_class.__doc__ else ''
            }
        except:
            return {
                'class_name': processor_class.__name__,
                'module': processor_class.__module__,
                'supported_formats': [],
                'description': processor_class.__doc__.strip() if processor_class.__doc__ else ''
            }


class ProcessorConfig:
    """处理器配置类"""

    def __init__(self, **kwargs):
        # 分块配置
        self.default_chunk_size = kwargs.get('default_chunk_size', 1000)
        self.default_overlap = kwargs.get('default_overlap', 100)
        self.max_chunk_size = kwargs.get('max_chunk_size', 2000)

        # 处理配置
        self.max_file_size = kwargs.get('max_file_size', 50 * 1024 * 1024)  # 50MB
        self.timeout_seconds = kwargs.get('timeout_seconds', 300)

        # 性能配置
        self.max_workers = kwargs.get('max_workers', 4)
        self.batch_size = kwargs.get('batch_size', 10)

        # 缓存配置
        self.enable_cache = kwargs.get('enable_cache', True)
        self.cache_ttl = kwargs.get('cache_ttl', 3600)  # 1小时

        # PDF特定配置
        self.allow_encrypted = kwargs.get('allow_encrypted', False)
        self.pdf_password = kwargs.get('pdf_password', None)

        # 严格模式
        self.strict_mode = kwargs.get('strict_mode', False)

        # 输出配置
        self.enable_metadata_extraction = kwargs.get('enable_metadata_extraction', True)
        self.enable_text_cleaning = kwargs.get('enable_text_cleaning', True)
        self.enable_chunking = kwargs.get('enable_chunking', True)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'default_chunk_size': self.default_chunk_size,
            'default_overlap': self.default_overlap,
            'max_chunk_size': self.max_chunk_size,
            'max_file_size': self.max_file_size,
            'timeout_seconds': self.timeout_seconds,
            'max_workers': self.max_workers,
            'batch_size': self.batch_size,
            'enable_cache': self.enable_cache,
            'cache_ttl': self.cache_ttl,
            'allow_encrypted': self.allow_encrypted,
            'pdf_password': self.pdf_password,
            'strict_mode': self.strict_mode,
            'enable_metadata_extraction': self.enable_metadata_extraction,
            'enable_text_cleaning': self.enable_text_cleaning,
            'enable_chunking': self.enable_chunking,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ProcessorConfig':
        """从字典创建配置"""
        return cls(**config_dict)

    def validate(self) -> bool:
        """验证配置"""
        # 检查基本配置
        if self.default_chunk_size <= 0:
            raise ValueError("分块大小必须大于0")

        if self.default_overlap < 0:
            raise ValueError("重叠大小不能为负数")

        if self.max_chunk_size < self.default_chunk_size:
            raise ValueError("最大分块大小不能小于默认分块大小")

        if self.max_file_size <= 0:
            raise ValueError("最大文件大小必须大于0")

        if self.timeout_seconds <= 0:
            raise ValueError("超时时间必须大于0")

        if self.max_workers <= 0:
            raise ValueError("最大工作线程数必须大于0")

        if self.batch_size <= 0:
            raise ValueError("批处理大小必须大于0")

        if self.cache_ttl < 0:
            raise ValueError("缓存TTL不能为负数")

        return True