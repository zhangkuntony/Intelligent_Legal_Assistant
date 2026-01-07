"""
PDF文档处理器
"""
from typing import Dict, Any, List
from dataclasses import dataclass

from .base_processor import BaseDocumentProcessor, DocumentChunk
from .exceptions import ExtractionError

try:
    import PyPDF2
    import pdfplumber

    PDF_SUPPORT_AVAILABLE = True
except ImportError:
    PDF_SUPPORT_AVAILABLE = False


@dataclass
class ImageInfo:
    """图像信息"""
    page_num: int
    image_index: int
    image_type: str
    width: int
    height: int
    bbox: tuple  # (x0, y0, x1, y1)


class PDFProcessor(BaseDocumentProcessor):
    """PDF文档处理器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.supported_formats = ['.pdf']

        if not PDF_SUPPORT_AVAILABLE:
            raise ImportError("PDF处理依赖未安装，请安装 PyPDF2 和 pdfplumber")

    async def extract_text(self, file_path: str) -> str:
        """提取PDF文本内容"""
        try:
            # 使用pdfplumber提取文本，保留结构信息
            full_text = ""

            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # 提取页面文本
                        page_text = page.extract_text()
                        if page_text:
                            # 添加页面分隔符
                            full_text += f"\n--- 第{page_num}页 ---\n"
                            full_text += page_text
                            full_text += "\n"

                        # 提取表格数据（如果有）
                        tables = page.extract_tables()
                        if tables:
                            for table_num, table in enumerate(tables, 1):
                                table_text = self._format_table(table)
                                if table_text:
                                    full_text += f"\n--- 第{page_num}页表格{table_num} ---\n"
                                    full_text += table_text
                                    full_text += "\n"

                    except Exception as e:
                        # 单个页面处理失败，继续处理其他页面
                        error_msg = f"第{page_num}页处理失败: {str(e)}"
                        if self.config.get('strict_mode', False):
                            raise ExtractionError(error_msg)
                        else:
                            # 记录错误但继续处理
                            full_text += f"\n--- 第{page_num}页处理失败 ---\n"

            return full_text.strip()

        except Exception as e:
            raise ExtractionError(f"PDF文本提取失败: {str(e)}")

    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取PDF元数据"""
        try:
            metadata = await super().extract_metadata(file_path)

            # 使用PyPDF2提取PDF特定元数据
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                # 基本信息
                pdf_metadata = {
                    'total_pages': len(pdf_reader.pages),
                    'is_encrypted': pdf_reader.is_encrypted,
                }

                # 文档信息
                if pdf_reader.metadata:
                    pdf_metadata.update({
                        'title': pdf_reader.metadata.get('/Title'),
                        'author': pdf_reader.metadata.get('/Author'),
                        'subject': pdf_reader.metadata.get('/Subject'),
                        'creator': pdf_reader.metadata.get('/Creator'),
                        'producer': pdf_reader.metadata.get('/Producer'),
                        'creation_date': pdf_reader.metadata.get('/CreationDate'),
                        'modification_date': pdf_reader.metadata.get('/ModDate'),
                    })

            metadata.update(pdf_metadata)
            return metadata

        except Exception as e:
            # 元数据提取失败不影响主要功能
            return await super().extract_metadata(file_path)

    async def extract_images(self, file_path: str) -> List[ImageInfo]:
        """提取PDF中的图像（可选，用于OCR处理）"""
        images = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 提取页面图像
                    page_images = page.images
                    for img_index, img in enumerate(page_images):
                        image_info = ImageInfo(
                            page_num=page_num,
                            image_index=img_index,
                            image_type=img.get('filter', 'Unknown'),
                            width=img.get('width', 0),
                            height=img.get('height', 0),
                            bbox=img.get('bbox', (0, 0, 0, 0))
                        )
                        images.append(image_info)

        except Exception as e:
            # 图像提取失败不影响主要功能
            pass

        return images

    async def validate_file(self, file_path: str) -> bool:
        """验证PDF文件完整性"""
        # 先进行基本验证
        if not await super().validate_file(file_path):
            return False

        try:
            # 尝试打开PDF文件验证完整性
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                # 检查是否加密
                if pdf_reader.is_encrypted:
                    if self.config.get('allow_encrypted', False):
                        # 尝试解密（如果有密码）
                        password = self.config.get('pdf_password')
                        if password:
                            pdf_reader.decrypt(password)
                        else:
                            return False
                    else:
                        return False

                # 检查是否有页面
                if len(pdf_reader.pages) == 0:
                    return False

                # 尝试读取第一页
                first_page = pdf_reader.pages[0]
                _ = first_page.extract_text()  # 尝试提取文本

                return True

        except Exception:
            return False

    async def chunk_text(self, text: str, **kwargs) -> List[DocumentChunk]:
        """PDF专用分块策略"""
        # 使用页面边界进行分块
        chunks = []
        chunk_index = 0

        # 按页面分割
        pages = text.split('--- 第')

        for page_content in pages:
            if not page_content.strip():
                continue

            # 提取页面号和内容
            lines = page_content.split('\n', 1)
            if len(lines) < 2:
                continue

            page_header = lines[0].strip()
            page_text = lines[1].strip()

            # 提取页面号
            try:
                page_num = int(page_header.replace('页 ---', '').strip())
            except (ValueError, IndexError):
                page_num = chunk_index + 1

            if not page_text:
                continue

            # 如果页面内容过长，进行二次分块
            max_chunk_size = kwargs.get('chunk_size', self.config.get('default_chunk_size', 1000))

            if len(page_text) <= max_chunk_size:
                # 单页内容不超过限制，直接作为一块
                chunk = DocumentChunk(
                    chunk_id=f"pdf_page_{page_num}",
                    content=page_text,
                    chunk_index=chunk_index,
                    metadata={
                        'page_number': page_num,
                        'chunk_type': 'page',
                        'content_length': len(page_text)
                    },
                    page_number=page_num
                )
                chunks.append(chunk)
                chunk_index += 1

            else:
                # 页面内容过长，进行分段处理
                segments = self._split_page_content(page_text, max_chunk_size)

                for seg_index, segment in enumerate(segments):
                    chunk = DocumentChunk(
                        chunk_id=f"pdf_page_{page_num}_seg_{seg_index}",
                        content=segment,
                        chunk_index=chunk_index,
                        metadata={
                            'page_number': page_num,
                            'segment_index': seg_index,
                            'chunk_type': 'page_segment',
                            'content_length': len(segment)
                        },
                        page_number=page_num
                    )
                    chunks.append(chunk)
                    chunk_index += 1

        return chunks

    def _split_page_content(self, page_text: str, max_chunk_size: int) -> List[str]:
        """分割页面内容"""
        segments = []

        # 按段落分割
        paragraphs = page_text.split('\n\n')
        current_segment = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # 如果当前段落加上新段落不超过限制，则合并
            if len(current_segment) + len(paragraph) + 2 <= max_chunk_size:
                if current_segment:
                    current_segment += "\n\n" + paragraph
                else:
                    current_segment = paragraph

            else:
                # 当前段落已满，保存并开始新段落
                if current_segment:
                    segments.append(current_segment)

                # 如果单个段落就超过限制，强制分割
                if len(paragraph) > max_chunk_size:
                    # 按句子分割
                    sentences = paragraph.split('。')
                    current_sentence_group = ""

                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue

                        sentence += '。'  # 添加句号

                        if len(current_sentence_group) + len(sentence) <= max_chunk_size:
                            current_sentence_group += sentence

                        else:
                            if current_sentence_group:
                                segments.append(current_sentence_group)
                            current_sentence_group = sentence

                    if current_sentence_group:
                        segments.append(current_sentence_group)

                else:
                    current_segment = paragraph

        # 添加最后一个段落
        if current_segment:
            segments.append(current_segment)

        return segments

    def _format_table(self, table: List[List[str]]) -> str:
        """格式化表格数据为文本"""
        if not table:
            return ""

        formatted_table = []

        for row in table:
            # 过滤空单元格
            row_data = [cell.strip() if cell else "" for cell in row]
            formatted_row = " | ".join(row_data)
            formatted_table.append(formatted_row)

        return "\n".join(formatted_table)