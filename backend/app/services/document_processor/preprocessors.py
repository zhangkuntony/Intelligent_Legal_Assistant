"""
文本预处理器模块
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Citation:
    """法律引用"""
    text: str
    law_name: str
    article_number: str
    position: tuple  # (start, end)


@dataclass
class LegalTerm:
    """法律术语"""
    term: str
    definition: str
    position: tuple  # (start, end)


@dataclass
class DocumentStructure:
    """文档结构"""
    sections: List[Dict[str, Any]]
    total_sections: int
    hierarchy_level: int


class TextPreprocessor:
    """文本预处理器"""
    
    def __init__(self):
        self.noise_patterns = [
            r'第\s*[0-9]+\s*页',  # 页码
            r'共\s*[0-9]+\s*页',  # 总页数
            r'\b页码:\s*[0-9]+',  # 页码标记
            r'\b页眉:.*',  # 页眉
            r'\b页脚:.*',  # 页脚
            r'-{3,}',  # 分隔线
            r'={3,}',  # 等号线
        ]
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余空格和换行符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除噪音模式
        for pattern in self.noise_patterns:
            text = re.sub(pattern, '', text)
        
        # 标准化标点符号
        text = self._normalize_punctuation(text)
        
        # 移除特殊字符
        text = self._remove_special_chars(text)
        
        return text.strip()
    
    def normalize_encoding(self, text: str) -> str:
        """标准化字符编码"""
        # 替换全角字符为半角
        text = text.replace('　', ' ')  # 全角空格
        text = text.replace('＃', '#')  # 全角井号
        text = text.replace('＄', '$')  # 全角美元符号
        text = text.replace('％', '%')  # 全角百分号
        text = text.replace('＆', '&')  # 全角和号
        text = text.replace('（', '(')  # 全角左括号
        text = text.replace('）', ')')  # 全角右括号
        text = text.replace('［', '[')  # 全角左方括号
        text = text.replace('］', ']')  # 全角右方括号
        text = text.replace('｛', '{')  # 全角左花括号
        text = text.replace('｝', '}')  # 全角右花括号
        
        # 标准化引号
        text = text.replace('＂', '"')  # 全角双引号
        text = text.replace('＇', "'")   # 全角单引号
        text = text.replace('“', '"')   # 中文左双引号
        text = text.replace('”', '"')   # 中文右双引号
        text = text.replace('‘', "'")   # 中文左单引号
        text = text.replace('’', "'")   # 中文右单引号
        
        return text
    
    def remove_noise(self, text: str) -> str:
        """移除噪音"""
        # 移除页眉页脚
        text = re.sub(r'^.*[0-9]{1,2}/[0-9]{1,2}.*$', '', text, flags=re.MULTILINE)
        
        # 移除版权信息
        text = re.sub(r'©.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'版权.*$', '', text, flags=re.MULTILINE)
        
        # 移除网址
        text = re.sub(r'https?://\S+', '', text)
        
        # 移除邮箱
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        return text
    
    def _normalize_punctuation(self, text: str) -> str:
        """标准化标点符号"""
        # 中文标点转英文标点
        text = text.replace('。', '.')
        text = text.replace('，', ',')
        text = text.replace('；', ';')
        text = text.replace('：', ':')
        text = text.replace('！', '!')
        text = text.replace('？', '?')
        text = text.replace('（', '(')
        text = text.replace('）', ')')
        text = text.replace('【', '[')
        text = text.replace('】', ']')
        text = text.replace('《', '<')
        text = text.replace('》', '>')
        
        # 标准化空格
        text = re.sub(r'([,.!?;:])\s*', r'\1 ', text)  # 标点后加空格
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)    # 标点前移除空格
        
        return text
    
    def _remove_special_chars(self, text: str) -> str:
        """移除特殊字符"""
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # 移除不可打印字符
        text = re.sub(r'[^\x20-\x7E\u4e00-\u9FFF]', '', text)
        
        return text


class LegalTextProcessor(TextPreprocessor):
    """法律文本专用处理器"""
    
    def __init__(self):
        super().__init__()
        
        # 法律引用模式
        self.citation_patterns = [
            r'《([^》]+)》第([零一二三四五六七八九十百千万0-9]+)条',  # 中文法律引用
            r'《([^》]+)》第([0-9]+)条',  # 数字法律引用
            r'([A-Za-z\s]+)法第([零一二三四五六七八九十百千万0-9]+)条',  # 中文法律名称
            r'([A-Za-z\s]+)法第([0-9]+)条',  # 数字法律名称
        ]
        
        # 常见法律术语
        self.legal_terms = {
            '原告': '在民事诉讼中，向法院提起诉讼的一方',
            '被告': '在民事诉讼中，被提起诉讼的一方',
            '上诉人': '对一审判决不服，向上级法院提起上诉的一方',
            '被上诉人': '在上诉案件中，被上诉的一方',
            '诉讼': '通过法院解决纠纷的法律程序',
            '仲裁': '通过仲裁机构解决争议的方式',
            '合同': '当事人之间设立、变更、终止民事关系的协议',
            '侵权': '侵害他人合法权益的行为',
            '违约责任': '合同当事人不履行合同义务所应承担的责任',
            '刑事责任': '违反刑法规定所应承担的法律责任',
            '行政处罚': '行政机关对违法行为人实施的惩罚',
        }
    
    def extract_citations(self, text: str) -> List[Citation]:
        """提取法律引用"""
        citations = []
        
        for pattern in self.citation_patterns:
            matches = re.finditer(pattern, text)
            
            for match in matches:
                citation = Citation(
                    text=match.group(0),
                    law_name=match.group(1),
                    article_number=match.group(2),
                    position=(match.start(), match.end())
                )
                citations.append(citation)
        
        return citations
    
    def identify_legal_terms(self, text: str) -> List[LegalTerm]:
        """识别法律术语"""
        terms = []
        
        for term, definition in self.legal_terms.items():
            matches = re.finditer(re.escape(term), text)
            
            for match in matches:
                legal_term = LegalTerm(
                    term=term,
                    definition=definition,
                    position=(match.start(), match.end())
                )
                terms.append(legal_term)
        
        return terms
    
    def structure_analysis(self, text: str) -> DocumentStructure:
        """分析文档结构"""
        sections = []
        
        # 分析章节结构
        chapter_patterns = [
            r'^第[一二三四五六七八九十]+章\s*(.+)$',  # 中文章节
            r'^第[0-9]+章\s*(.+)$',  # 数字章节
            r'^CHAPTER\s+[IVXLCDM]+\s*(.+)$',  # 罗马数字章节
            r'^Chapter\s+[0-9]+\s*(.+)$',  # 英文章节
        ]
        
        article_patterns = [
            r'^第[一二三四五六七八九十]+条\s*(.+)$',  # 中文条款
            r'^第[0-9]+条\s*(.+)$',  # 数字条款
            r'^Article\s+[0-9]+\s*(.+)$',  # 英文条款
        ]
        
        lines = text.split('\n')
        current_section = None
        section_level = 0
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是章节
            for pattern in chapter_patterns:
                match = re.match(pattern, line)
                if match:
                    if current_section:
                        sections.append(current_section)
                    
                    current_section = {
                        'type': 'chapter',
                        'title': match.group(1).strip(),
                        'level': 1,
                        'start_line': line_num,
                        'end_line': line_num,
                        'articles': []
                    }
                    section_level = 1
                    break
            
            # 检查是否是条款
            for pattern in article_patterns:
                match = re.match(pattern, line)
                if match:
                    if current_section and current_section['type'] == 'chapter':
                        article = {
                            'type': 'article',
                            'title': match.group(1).strip(),
                            'level': 2,
                            'start_line': line_num,
                            'end_line': line_num,
                            'content': line
                        }
                        current_section['articles'].append(article)
                    else:
                        # 独立条款
                        if current_section:
                            sections.append(current_section)
                        
                        current_section = {
                            'type': 'article',
                            'title': match.group(1).strip(),
                            'level': 1,
                            'start_line': line_num,
                            'end_line': line_num,
                            'content': line
                        }
                        section_level = 1
                    break
        
        # 添加最后一个章节
        if current_section:
            sections.append(current_section)
        
        # 计算层次级别
        hierarchy_level = max([s['level'] for s in sections]) if sections else 0
        
        return DocumentStructure(
            sections=sections,
            total_sections=len(sections),
            hierarchy_level=hierarchy_level
        )
    
    def clean_legal_text(self, text: str) -> str:
        """法律文本专用清理"""
        # 基础清理
        text = self.clean_text(text)
        
        # 保留法律特有的格式
        # 不移除条款编号等法律特有标记
        
        # 标准化法律术语格式
        text = self._standardize_legal_terms(text)
        
        return text
    
    def _standardize_legal_terms(self, text: str) -> str:
        """标准化法律术语格式"""
        # 标准化法律名称引用
        text = re.sub(r'《([^》]+)法》', r'《\1法》', text)
        
        # 标准化条款引用
        text = re.sub(r'第\s*([零一二三四五六七八九十百千万0-9]+)\s*条', r'第\1条', text)
        text = re.sub(r'第\s*([0-9]+)\s*条', r'第\1条', text)
        
        return text
    
    def extract_key_phrases(self, text: str) -> List[str]:
        """提取关键短语"""
        key_phrases = []
        
        # 法律行为短语
        action_patterns = [
            r'应当[^。]*',
            r'不得[^。]*',
            r'可以[^。]*',
            r'必须[^。]*',
            r'禁止[^。]*',
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text)
            key_phrases.extend(matches)
        
        # 法律后果短语
        consequence_patterns = [
            r'承担[^。]*责任',
            r'处以[^。]*处罚',
            r'赔偿[^。]*损失',
            r'追究[^。]*责任',
        ]
        
        for pattern in consequence_patterns:
            matches = re.findall(pattern, text)
            key_phrases.extend(matches)
        
        return key_phrases