"""
文档处理器基类定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
import os

class ProcessingStatus(Enum):
    """处理状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingStats:
    """处理统计信息"""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_chars: int = 0
    total_chunks: int = 0
    processing_time: float = 0.0
    memory_usage: float = 0.0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def calculate_processing_time(self):
        """计算处理时间"""
        if self.end_time:
            self.processing_time = (self.end_time - self.start_time).total_seconds()


@dataclass
class DocumentChunk:
    """文档分块"""
    chunk_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any]
    page_number: Optional[int] = None
    section_title: Optional[str] = None

    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = f"chunk_{self.chunk_index}_{hashlib.md5(self.content.encode()).hexdigest()[:8]}"


@dataclass
class ProcessedDocument:
    """处理后的文档结果"""
    original_path: str
    extracted_text: str
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    processing_stats: ProcessingStats
    status: ProcessingStatus

    def __post_init__(self):
        if self.processing_stats is None:
            self.processing_stats = ProcessingStats(start_time=datetime.now())

        # 自动计算统计信息
        self.processing_stats.total_chars = len(self.extracted_text)
        self.processing_stats.total_chunks = len(self.chunks)
        self.processing_stats.calculate_processing_time()


class BaseDocumentProcessor(ABC):
    """文档处理器基类"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.supported_formats = []

    async def process_file(self, file_path: str, **kwargs) -> ProcessedDocument:
        """处理单个文件"""
        start_time = datetime.now()

        try:
            # 验证文件
            if not await self.validate_file(file_path):
                raise ValueError(f"文件验证失败: {file_path}")

            # 提取文本
            extracted_text = await self.extract_text(file_path)

            # 提取元数据
            metadata = await self.extract_metadata(file_path)

            # 预处理文本
            preprocessed_text = await self.preprocess_text(extracted_text)

            # 分块处理
            chunks = await self.chunk_text(preprocessed_text, **kwargs)

            # 创建处理结果
            processing_stats = ProcessingStats(start_time=start_time, end_time=datetime.now())

            result = ProcessedDocument(
                original_path=file_path,
                extracted_text=extracted_text,
                chunks=chunks,
                metadata=metadata,
                processing_stats=processing_stats,
                status=ProcessingStatus.COMPLETED
            )

            return result

        except Exception as e:
            processing_stats = ProcessingStats(
                start_time=start_time,
                end_time=datetime.now(),
                errors=[str(e)]
            )

            return ProcessedDocument(
                original_path=file_path,
                extracted_text="",
                chunks=[],
                metadata={},
                processing_stats=processing_stats,
                status=ProcessingStatus.FAILED
            )

    @abstractmethod
    async def extract_text(self, file_path: str) -> str:
        """提取文本内容"""
        pass

    async def validate_file(self, file_path: str) -> bool:
        """验证文件格式和完整性"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False

            # 检查文件大小
            file_size = os.path.getsize(file_path)
            max_size = self.config.get('max_file_size', 50 * 1024 * 1024)  # 默认50MB
            if file_size > max_size:
                return False

            # 检查文件扩展名
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                return False

            return True

        except Exception:
            return False

    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取文件元数据"""
        try:
            file_stat = os.stat(file_path)
            return {
                'file_size': file_stat.st_size,
                'created_time': datetime.fromtimestamp(file_stat.st_ctime),
                'modified_time': datetime.fromtimestamp(file_stat.st_mtime),
                'file_extension': Path(file_path).suffix.lower()
            }
        except Exception:
            return {}

    async def preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 1. 移除首尾空白
        text = text.strip()

        # 2. 标准化换行符（将 \r\n 和 \r 统一为 \n）
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 3. 处理每行，移除多余空格
        lines = text.split('\n')
        processed_lines = []

        for line in lines:
            # 移除每行的首尾空格，但保留内部空格
            line = line.strip()
            # 移除行内的连续多个空格
            line = ' '.join(line.split())
            processed_lines.append(line)

        # 4. 重新组合，保留换行符
        text = '\n'.join(processed_lines)

        # 5. 移除空行（连续的多个换行符）
        # 保留段落结构（单个换行），移除多余空行
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)  # 3个以上换行符 → 2个（保留一个空行）

        # 6. 标准化标点符号（可选）
        text = text.replace('。', '.').replace('，', ',').replace('；', ';')

        # 7. 移除首尾多余空行
        text = text.strip()

        return text

    async def chunk_text(self, text: str, **kwargs) -> List[DocumentChunk]:
        """将文本分割成块"""
        chunk_size = kwargs.get('chunk_size', self.config.get('default_chunk_size', 1000))
        overlap = kwargs.get('overlap', self.config.get('default_overlap', 100))

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size

            # 如果超过文本长度，则取到文本末尾
            if end > len(text):
                end = len(text)

            # 获取分块内容
            chunk_content = text[start:end]

            # 创建分块
            chunk = DocumentChunk(
                chunk_id=f"chunk_{chunk_index}",
                content=chunk_content,
                chunk_index=chunk_index,
                metadata={
                    'start_pos': start,
                    'end_pos': end,
                    'chunk_size': len(chunk_content)
                }
            )

            chunks.append(chunk)
            chunk_index += 1

            # 移动到下一个分块起始位置（考虑重叠）
            start = end - overlap

            # 如果已经处理完所有文本，则退出循环
            if start >= len(text):
                break

        return chunks

    def supports_format(self, file_path: str) -> bool:
        """检查是否支持该文件格式"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_formats