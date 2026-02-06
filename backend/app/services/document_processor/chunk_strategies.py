"""
分块策略模块
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .base_processor import DocumentChunk


class ChunkingStrategy(ABC):
    """分块策略基类"""

    @abstractmethod
    def chunk_text(self, text: str, document_metadata: Dict[str, Any], **kwargs) -> List[DocumentChunk]:
        """将文本分割成块

        Args:
            text: 待分块的文本
            document_metadata: 文档级别的metadata（包含document_title等）
            **kwargs: 其他参数

        Returns:
            分块列表
        """
        pass


class FixedSizeChunker(ChunkingStrategy):
    """固定大小分块器"""

    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, document_metadata: Dict[str, Any], **kwargs) -> List[DocumentChunk]:
        """固定大小分块"""
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size

            # 如果超过文本长度，则取到文本末尾
            if end > len(text):
                end = len(text)

            # 获取分块内容
            chunk_content = text[start:end]

            # 创建分块
            chunk = DocumentChunk(
                chunk_id=f"fixed_chunk_{chunk_index}",
                content=chunk_content,
                chunk_index=chunk_index,
                metadata={
                    'strategy': 'fixed_size',
                    'chunk_size': self.chunk_size,
                    'overlap': self.overlap,
                    'start_pos': start,
                    'end_pos': end,
                    'content_length': len(chunk_content),
                    **(document_metadata or {})                 # 添加文档级别的metadata
                }
            )

            chunks.append(chunk)
            chunk_index += 1

            # 移动到下一个分块起始位置（考虑重叠）
            start = end - self.overlap

            # 如果已经处理完所有文本，则退出循环
            if start >= len(text):
                break

        return chunks


class SemanticChunker(ChunkingStrategy):
    """语义分块器（基于句子边界）"""

    def __init__(self, max_chunk_size: int = 1000, min_chunk_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, document_metadata: Dict[str, Any], **kwargs) -> List[DocumentChunk]:
        """语义分块"""
        chunks = []
        chunk_index = 0

        # 分割成句子
        sentences = self._split_sentences(text)

        current_chunk = ""

        for sentence in sentences:
            # 如果添加当前句子后不超过最大限制
            if len(current_chunk) + len(sentence) + 1 <= self.max_chunk_size:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
            else:
                # 当前块已满，检查是否满足最小大小要求
                if len(current_chunk) >= self.min_chunk_size:
                    chunk = DocumentChunk(
                        chunk_id=f"semantic_chunk_{chunk_index}",
                        content=current_chunk,
                        chunk_index=chunk_index,
                        metadata={
                            'strategy': 'semantic',
                            'max_chunk_size': self.max_chunk_size,
                            'min_chunk_size': self.min_chunk_size,
                            'content_length': len(current_chunk),
                            **(document_metadata or {})                     # 添加文档级别的metadata
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk = sentence
                else:
                    # 当前块太小，继续添加句子
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence

        # 处理最后一个块
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunk = DocumentChunk(
                chunk_id=f"semantic_chunk_{chunk_index}",
                content=current_chunk,
                chunk_index=chunk_index,
                metadata={
                    'strategy': 'semantic',
                    'max_chunk_size': self.max_chunk_size,
                    'min_chunk_size': self.min_chunk_size,
                    'content_length': len(current_chunk),
                    **(document_metadata or {})                 # 添加文档级别的metadata
                }
            )
            chunks.append(chunk)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """分割文本成句子"""
        # 使用正则表达式分割句子
        sentence_endings = r'[。！？!?\n]'
        sentences = re.split(sentence_endings, text)

        # 清理空句子和空格
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences


class LegalDocumentChunker(ChunkingStrategy):
    """法律文档专用分块器"""

    def __init__(self, max_chunk_size: int = 1200):
        self.max_chunk_size = max_chunk_size
        self.legal_patterns = [
            r'第[一二三四五六七八九十]+条',  # 法律条款
            r'第[0-9]+条',  # 数字条款
            r'^[一二三四五六七八九十]、',  # 中文序号
            r'^[0-9]+\.',  # 数字序号
            r'^[一二三四五六七八九十]\s',  # 中文序号加空格
            r'^第[一二三四五六七八九十]+章',  # 章节
            r'^第[0-9]+章',  # 数字章节
        ]
        self.current_chapter = ""

    def chunk_text(self, text: str, document_metadata: Dict[str, Any], **kwargs) -> List[DocumentChunk]:
        """法律文档分块

        Args:
            text: 待分块的文本
            document_metadata: 文档级别的metadata（包含document_title等）
            **kwargs: 其他参数

        Returns:
            分块列表
        """

        logger = logging.getLogger(__name__)

        """法律文档分块"""
        chunks = []
        chunk_index = 0

        logger.info(f"切片文本：{text}")

        # 按行分割
        lines = text.split('\n')
        current_clause = ""
        current_title = ""
        current_chapter = ""

        logger.info(f"开始分块，共{len(lines)}行文本")

        for line_num, line in enumerate(lines):
            original_line = line        # 保留原始行
            line = line.strip()

            if not line:
                continue

            # 检查是否是章节标题
            is_chapter = self._is_chapter_title(line)
            if is_chapter:
                logger.info(f"检测到章节标题(第{line_num}行): {line}")
                # 更新当前章节，但不创建独立分块
                current_chapter = line
                # 如果当前有条款内容，先保存
                if current_clause:
                    logger.info(f"保存上一个条款（章节{current_chapter}），长度: {len(current_clause)}")

                    if len(current_clause) > self.max_chunk_size:
                        sub_chunks = self._split_long_clause(current_clause, current_title, chunk_index)
                        for sub_chunk in sub_chunks:
                            if 'chapter' not in sub_chunk.metadata:
                                sub_chunk.metadata['chapter'] = current_chapter
                        chunks.extend(sub_chunks)
                        chunk_index += len(sub_chunks)
                        logger.info(f"长条款分割为 {len(sub_chunks)} 个子块")
                    else:
                        chunk = DocumentChunk(
                            chunk_id=f"legal_chunk_{chunk_index}",
                            content=current_clause,
                            chunk_index=chunk_index,
                            metadata={
                                'strategy': 'legal_document',
                                'clause_type': 'legal_clause',
                                'clause_title': current_title,
                                'chapter': current_chapter,
                                'content_length': len(current_clause),
                                **(document_metadata or {})
                            },
                            section_title=current_title
                        )
                        chunks.append(chunk)
                        chunk_index += 1
                    current_clause = ""
                continue

            # 检查是否是法律条款开始(但排除章节标题)
            is_clause_start = self._is_legal_clause_start(line)

            if is_clause_start and not is_chapter:
                logger.info(f"检测到条款开始（第{line_num}行）: {line[:50]}...")
                # 保存上一个条款
                if current_clause:
                    logger.info(f"保存上一个条款，长度: {len(current_clause)}")
                    if len(current_clause) > self.max_chunk_size:
                        sub_chunks = self._split_long_clause(current_clause, current_title, chunk_index)
                        for sub_chunk in sub_chunks:
                            if 'chapter' not in sub_chunk.metadata:
                                sub_chunk.metadata['chapter'] = current_chapter
                        chunks.extend(sub_chunks)
                        chunk_index += len(sub_chunks)
                        logger.info(f"长条款分割为 {len(sub_chunks)} 个子块")
                    else:
                        chunk = DocumentChunk(
                            chunk_id=f"legal_clause_{chunk_index}",
                            content=current_clause,
                            chunk_index=chunk_index,
                            metadata={
                                'strategy': 'legal_document',
                                'clause_type': 'legal_clause',
                                'clause_title': current_title,
                                'chapter': current_chapter,
                                'content_length': len(current_clause),
                                **(document_metadata or {})
                            },
                            section_title=current_title
                        )
                        chunks.append(chunk)
                        chunk_index += 1

                # 开始新条款
                current_clause = line
                current_title = line

            else:
                # 继续当前条款
                if current_clause:
                    current_clause += "\n" + line
                else:
                    current_clause = line
                    current_title = "前言" if not current_clause else current_clause
                    logger.info(f"开始新的{current_title}（第{line_num}行）")

        logger.info(f"循环结束，准备处理最后一个条款，长度: {len(current_clause)} if current_clause else 'None'")

        # 处理最后一个条款
        if current_clause:
            logger.info(f"处理最后一个条款: {current_title[:50]}..., 长度: {len(current_clause)}")
            # 检查条款是否过长
            if len(current_clause) > self.max_chunk_size:
                sub_chunks = self._split_long_clause(current_clause, current_title, chunk_index)
                # 为每个子块添加章节信息
                for sub_chunk in sub_chunks:
                    if 'chapter' not in sub_chunk.metadata:
                        sub_chunk.metadata['chapter'] = current_chapter
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                logger.info(f"最后条款分割为 {len(sub_chunks)} 个子块")
            else:
                chunk = DocumentChunk(
                    chunk_id=f"legal_clause_{chunk_index}",
                    content=current_clause,
                    chunk_index=chunk_index,
                    metadata={
                        'strategy': 'legal_document',
                        'clause_type': 'legal_clause',
                        'clause_title': current_title,
                        'chapter': current_chapter,
                        'content_length': len(current_clause),
                        **(document_metadata or {})
                    },
                    section_title=current_title
                )
                chunks.append(chunk)

        logger.info(f"分块完成，共生成 {len(chunks)} 个分块")
        return chunks

    def _is_legal_clause_start(self, line: str) -> bool:
        logger = logging.getLogger(__name__)

        """判断是否是法律条款开始"""
        for pattern in self.legal_patterns:
            if re.match(pattern, line):
                logger.debug(f"匹配到条款模式: {pattern}, 行: {line[:30]}")
                return True

        # 检查是否是章节标题
        if self._is_chapter_title(line):
            logger.debug(f"这是章节标题，不是条款开始: {line[:30]}")
            return True

        return False

    def _is_chapter_title(self, line: str) -> bool:
        """判断是否是章节标题"""
        chapter_patterns = [
            r'^第[一二三四五六七八九十]+章',
            r'^第[0-9]+章',
            r'^CHAPTER\s+[IVXLCDM]+',  # 罗马数字章节
            r'^Chapter\s+[0-9]+',  # 英文章节
        ]

        for pattern in chapter_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True

        return False

    def _split_long_clause(self, clause_text: str, clause_title: str, start_index: int) -> List[DocumentChunk]:
        """分割过长的条款"""
        sub_chunks = []
        chunk_index = start_index

        # 按段落分割
        paragraphs = clause_text.split('\n')
        current_sub_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # 如果当前子块加上新段落不超过限制
            if len(current_sub_chunk) + len(paragraph) + 2 <= self.max_chunk_size:
                if current_sub_chunk:
                    current_sub_chunk += "\n\n" + paragraph
                else:
                    current_sub_chunk = paragraph
            else:
                # 当前子块已满，保存
                if current_sub_chunk:
                    chunk = DocumentChunk(
                        chunk_id=f"legal_subclause_{chunk_index}",
                        content=current_sub_chunk,
                        chunk_index=chunk_index,
                        metadata={
                            'strategy': 'legal_document',
                            'clause_type': 'sub_clause',
                            'parent_clause': clause_title,
                            'content_length': len(current_sub_chunk),
                            'chapter': self.current_chapter
                        },
                        section_title=f"{clause_title} - 分段{chunk_index - start_index + 1}"
                    )
                    sub_chunks.append(chunk)
                    chunk_index += 1
                    current_sub_chunk = paragraph
                else:
                    # 单个段落就超过限制，强制分割
                    sentences = self._split_sentences(paragraph)
                    current_sentence_group = ""

                    for sentence in sentences:
                        if len(current_sentence_group) + len(sentence) + 1 <= self.max_chunk_size:
                            if current_sentence_group:
                                current_sentence_group += " " + sentence
                            else:
                                current_sentence_group = sentence
                        else:
                            # 保存当前句子组
                            if current_sentence_group:
                                chunk = DocumentChunk(
                                    chunk_id=f"legal_subclause_{chunk_index}",
                                    content=current_sentence_group,
                                    chunk_index=chunk_index,
                                    metadata={
                                        'strategy': 'legal_document',
                                        'clause_type': 'sentence_group',
                                        'parent_clause': clause_title,
                                        'content_length': len(current_sentence_group),
                                        'chapter': self.current_chapter
                                    },
                                    section_title=f"{clause_title} - 句子组{chunk_index - start_index + 1}"
                                )
                                sub_chunks.append(chunk)
                                chunk_index += 1

                            current_sentence_group = sentence

                    # 添加最后一个句子组
                    if current_sentence_group:
                        chunk = DocumentChunk(
                            chunk_id=f"legal_subclause_{chunk_index}",
                            content=current_sentence_group,
                            chunk_index=chunk_index,
                            metadata={
                                'strategy': 'legal_document',
                                'clause_type': 'sentence_group',
                                'parent_clause': clause_title,
                                'content_length': len(current_sentence_group),
                                'chapter': self.current_chapter
                            },
                            section_title=f"{clause_title} - 句子组{chunk_index - start_index + 1}"
                        )
                        sub_chunks.append(chunk)
                        chunk_index += 1

        # 添加最后一个子块
        if current_sub_chunk:
            chunk = DocumentChunk(
                chunk_id=f"legal_subclause_{chunk_index}",
                content=current_sub_chunk,
                chunk_index=chunk_index,
                metadata={
                    'strategy': 'legal_document',
                    'clause_type': 'sub_clause',
                    'parent_clause': clause_title,
                    'content_length': len(current_sub_chunk),
                    'chapter': self.current_chapter
                },
                section_title=f"{clause_title} - 分段{chunk_index - start_index + 1}"
            )
            sub_chunks.append(chunk)

        return sub_chunks

    def _split_sentences(self, text: str) -> List[str]:
        """分割文本成句子"""
        sentence_endings = r'[。！？!?]'
        sentences = re.split(sentence_endings, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences