"""
文本文件处理器
"""

import chardet
from typing import Dict, Any, List

from .base_processor import BaseDocumentProcessor, ProcessedDocument, DocumentChunk
from .exceptions import ExtractionError


class TextProcessor(BaseDocumentProcessor):
    """文本文件处理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.supported_formats = ['.txt', '.md', '.markdown', '.rst', '.log']
    
    async def extract_text(self, file_path: str) -> str:
        """提取文本内容"""
        try:
            # 检测文件编码
            encoding = await self.detect_encoding(file_path)
            
            # 使用检测到的编码读取文件
            with open(file_path, 'r', encoding=encoding, errors='replace') as file:
                content = file.read()
            
            return content
            
        except Exception as e:
            raise ExtractionError(f"文本文件读取失败: {str(e)}")
    
    async def detect_encoding(self, file_path: str) -> str:
        """自动检测文件编码"""
        try:
            # 读取文件前部分内容进行编码检测
            with open(file_path, 'rb') as file:
                raw_data = file.read(4096)  # 读取前4KB
            
            # 使用chardet检测编码
            detection_result = chardet.detect(raw_data)
            encoding = detection_result.get('encoding', 'utf-8')
            confidence = detection_result.get('confidence', 0)
            
            # 如果置信度较低，使用常见编码尝试
            if confidence < 0.7:
                # 尝试常见编码
                common_encodings = ['utf-8', 'gbk', 'gb2312', 'latin1', 'ascii']
                
                for enc in common_encodings:
                    try:
                        # 尝试用该编码解码
                        raw_data.decode(enc)
                        encoding = enc
                        break
                    except UnicodeDecodeError:
                        continue
            
            return encoding.lower()
            
        except Exception:
            # 编码检测失败，使用utf-8作为默认
            return 'utf-8'
    
    async def preprocess_text(self, text: str) -> str:
        """文本文件专用预处理"""
        # 基础预处理
        text = await super().preprocess_text(text)
        
        # 处理Markdown文件
        if self._is_markdown_file(text):
            text = self._preprocess_markdown(text)
        
        # 处理代码文件（如果有）
        if self._contains_code_patterns(text):
            text = self._preprocess_code(text)
        
        return text
    
    async def chunk_text(self, text: str, **kwargs) -> List[DocumentChunk]:
        """文本文件专用分块策略"""
        chunks = []
        chunk_index = 0
        
        # 根据文件类型选择分块策略
        file_path = kwargs.get('file_path', '')
        
        if file_path.endswith('.md') or file_path.endswith('.markdown'):
            # Markdown文件：按章节分块
            chunks = self._chunk_markdown(text, chunk_index)
        
        elif self._is_legal_document(text):
            # 法律文档：按条款分块
            chunks = self._chunk_legal_document(text, chunk_index)
        
        else:
            # 普通文本：使用语义分块
            chunks = await self._chunk_semantic(text, chunk_index, **kwargs)
        
        return chunks
    
    def _is_markdown_file(self, text: str) -> bool:
        """判断是否是Markdown文件"""
        markdown_indicators = [
            '# ',  # 标题
            '## ',  # 二级标题
            '```',  # 代码块
            '> ',   # 引用
            '- ',   # 列表
            '* ',   # 列表
        ]
        
        for indicator in markdown_indicators:
            if indicator in text[:1000]:  # 检查前1000字符
                return True
        
        return False
    
    def _preprocess_markdown(self, text: str) -> str:
        """预处理Markdown文本"""
        lines = text.split('\n')
        processed_lines = []
        
        in_code_block = False
        
        for line in lines:
            line = line.strip()
            
            # 处理代码块
            if line.startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                # 代码块内容保持原样
                processed_lines.append(line)
                continue
            
            # 移除Markdown标记但保留内容
            if line.startswith('#'):
                # 标题：移除#标记但保留文本
                line = line.lstrip('#').strip()
                processed_lines.append(f"标题: {line}")
            
            elif line.startswith('> '):
                # 引用：移除>标记
                line = line.lstrip('>').strip()
                processed_lines.append(f"引用: {line}")
            
            elif line.startswith(('- ', '* ')):
                # 列表：移除列表标记
                line = line.lstrip('-*').strip()
                processed_lines.append(f"• {line}")
            
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _contains_code_patterns(self, text: str) -> bool:
        """判断是否包含代码模式"""
        code_indicators = [
            'def ', 'class ', 'import ', 'from ',  # Python
            'function ', 'var ', 'let ', 'const ',  # JavaScript
            'public ', 'private ', 'class ',  # Java/C#
            '#include ', 'int main',  # C/C++
        ]
        
        for indicator in code_indicators:
            if indicator in text[:2000]:  # 检查前2000字符
                return True
        
        return False
    
    def _preprocess_code(self, text: str) -> str:
        """预处理代码文本"""
        # 对于代码文件，保持原样但添加标识
        return f"代码文件内容:\n{text}"
    
    def _is_legal_document(self, text: str) -> bool:
        """判断是否是法律文档"""
        legal_indicators = [
            '第', '条', '款', '项',  # 法律条款
            '中华人民共和国', '最高人民法院', '最高人民检察院',  # 中国法律机构
            '法律', '法规', '条例', '办法', '规定',  # 法律文件类型
            '第一条', '第二条', '第三条',  # 条款编号
        ]
        
        for indicator in legal_indicators:
            if indicator in text[:500]:  # 检查前500字符
                return True
        
        return False
    
    def _chunk_markdown(self, text: str, start_index: int) -> List[DocumentChunk]:
        """Markdown文件分块"""
        chunks = []
        chunk_index = start_index
        
        # 按标题分割
        sections = text.split('\n# ')
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # 处理第一个section（可能没有标题）
            if i == 0:
                section_title = "前言"
                section_content = section
            else:
                # 提取标题和内容
                lines = section.split('\n', 1)
                section_title = lines[0].strip()
                section_content = lines[1] if len(lines) > 1 else ""
            
            if not section_content.strip():
                continue
            
            chunk = DocumentChunk(
                chunk_id=f"md_section_{chunk_index}",
                content=section_content,
                chunk_index=chunk_index,
                metadata={
                    'chunk_type': 'markdown_section',
                    'section_title': section_title,
                    'content_length': len(section_content)
                },
                section_title=section_title
            )
            chunks.append(chunk)
            chunk_index += 1
        
        return chunks
    
    def _chunk_legal_document(self, text: str, start_index: int) -> List[DocumentChunk]:
        """法律文档分块"""
        chunks = []
        chunk_index = start_index
        
        # 按条款分割
        lines = text.split('\n')
        current_clause = ""
        current_title = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是条款开始
            if self._is_legal_clause_start(line):
                # 保存上一个条款
                if current_clause:
                    chunk = DocumentChunk(
                        chunk_id=f"legal_clause_{chunk_index}",
                        content=current_clause,
                        chunk_index=chunk_index,
                        metadata={
                            'chunk_type': 'legal_clause',
                            'clause_title': current_title,
                            'content_length': len(current_clause)
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
                    current_title = "前言"
        
        # 添加最后一个条款
        if current_clause:
            chunk = DocumentChunk(
                chunk_id=f"legal_clause_{chunk_index}",
                content=current_clause,
                chunk_index=chunk_index,
                metadata={
                    'chunk_type': 'legal_clause',
                    'clause_title': current_title,
                    'content_length': len(current_clause)
                },
                section_title=current_title
            )
            chunks.append(chunk)
        
        return chunks
    
    async def _chunk_semantic(self, text: str, start_index: int, **kwargs) -> List[DocumentChunk]:
        """语义分块"""
        # 使用句子边界进行分块
        chunks = []
        chunk_index = start_index
        
        max_chunk_size = kwargs.get('chunk_size', self.config.get('default_chunk_size', 1000))
        
        # 按句子分割（简单实现）
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            
            # 句子结束标志
            if char in ['。', '!', '?', '\n']:
                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                current_sentence = ""
        
        # 添加最后一个句子
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        # 将句子组合成块
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
            else:
                # 当前块已满，保存并开始新块
                if current_chunk:
                    chunk = DocumentChunk(
                        chunk_id=f"text_chunk_{chunk_index}",
                        content=current_chunk,
                        chunk_index=chunk_index,
                        metadata={
                            'chunk_type': 'semantic',
                            'content_length': len(current_chunk)
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk:
            chunk = DocumentChunk(
                chunk_id=f"text_chunk_{chunk_index}",
                content=current_chunk,
                chunk_index=chunk_index,
                metadata={
                    'chunk_type': 'semantic',
                    'content_length': len(current_chunk)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _is_legal_clause_start(self, line: str) -> bool:
        """判断是否是法律条款开始"""
        legal_patterns = [
            r'第[一二三四五六七八九十]+条',
            r'第[0-9]+条',
            r'^[一二三四五六七八九十]、',
            r'^[0-9]+\.',
        ]
        
        import re
        for pattern in legal_patterns:
            if re.match(pattern, line):
                return True
        
        return False