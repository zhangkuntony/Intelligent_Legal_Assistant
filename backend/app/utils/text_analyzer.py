"""
文本分析工具类
提供中文文本处理、关键词提取等功能
"""
from collections import Counter
from typing import List, Dict, Set

import logging
import re

logger = logging.getLogger(__name__)

try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba未安装，将使用基础的关键词提取方法")

class TextAnalyzer:
    """文本分析工具类"""

    # 中文停用词列表（基础版）
    STOP_WORDS: Set[str] = {
        # 代词
        '我', '你', '他', '她', '它', '我们', '你们', '他们', '她们', '它们',
        '这', '那', '这个', '那个', '这些', '那些', '这里', '那里', '哪里',
        '什么', '怎么', '如何', '为什么', '谁', '哪', '几', '多少',

        # 连词
        '和', '与', '及', '或', '但是', '然而', '不过', '而且', '并且', '或者',
        '如果', '要是', '假如', '虽然', '尽管', '可是', '但是', '因此', '所以',
        '因为', '由于', '为了', '于是', '接着', '然后', '最后',

        # 助词
        '的', '地', '得', '着', '了', '过', '呢', '吗', '吧', '啊', '呀', '哦',
        '啦', '呗', '嘛', '哇', '呢', '嗯',

        # 动词
        '是', '有', '在', '说', '做', '去', '来', '看', '想', '要', '会', '能',
        '可以', '应该', '需要', '必须', '可能', '希望', '觉得', '认为', '觉得',
        '感觉', '发现', '表示', '说明', '显示', '证明', '认为', '以为', '以为',

        # 形容词
        '很', '非常', '特别', '十分', '比较', '稍微', '一点', '一些', '好', '多',
        '少', '大', '小', '新', '旧', '快', '慢', '高', '低', '长', '短',

        # 常用词
        '问题', '情况', '事情', '方面', '相关', '有关', '涉及', '包括', '包含',
        '其他', '另外', '此外', '除此之外', '同时', '同样', '此外',

        # 对话相关
        '请问', '请问一下', '我想知道', '我想了解', '我想问问', '帮我', '帮我看看',
        '帮我分析', '帮我查询', '能否', '可否', '是否', '有无', '有没有',

        # 无意义词
        '那个', '哪个', '某', '某位', '某些', '等等', '之类', '之类的',
    }

    # 法律领域停用词
    LEGAL_STOP_WORDS: Set[str] = {
        '根据', '依据', '按照', '依照', '参照', '本着', '鉴于',
        '关于', '对于', '至于', '针对', '面对',
        '以及', '及其', '以下', '以上', '如下', '如上',
        '所谓', '所', '将', '予', '予以', '加以', '进行',
        '通过', '经由', '经过', '经由',
    }

    @classmethod
    def extract_keywords_from_texts(
            cls,
            texts: List[str],
            top_k: int = 10,
            min_word_length: int = 2,
            max_word_length: int = 4,
            use_stop_words: bool = True,
            domain: str = 'general'
    ) -> List[Dict[str, int]]:
        """
        从多个文本中提取关键词

        Args:
            texts: 文本列表
            top_k: 返回的关键词数量
            min_word_length: 最小词长度
            max_word_length: 最大词长度
            use_stop_words: 是否使用停用词过滤
            domain: 领域（general-通用, legal-法律）

        Returns:
            关键词列表，每个元素为 {"topic": word, "count": count}
        """
        if not texts:
            return []

        # 合并所有文本
        all_words = []

        for text in texts:
            words = cls._extract_words_from_text(
                text,
                min_word_length,
                max_word_length,
                use_stop_words,
                domain
            )
            all_words.extend(words)

        # 统计词频
        word_counter = Counter(all_words)

        # 如果使用jieba，可以使用TF-IDF算法
        if JIEBA_AVAILABLE and len(texts) > 1:
            try:
                return cls._extract_with_tfidf(texts, top_k, min_word_length, max_word_length, domain)
            except Exception as e:
                logger.warning(f"TF-IDF提取失败，使用词频统计: {e}")

        # 使用词频统计
        hot_topics = [
            {"topic": word, "count": count}
            for word, count in word_counter.most_common(top_k)
        ]

        return hot_topics


    @classmethod
    def _extract_words_from_text(
            cls,
            text: str,
            min_word_length: int = 2,
            max_word_length: int = 4,
            use_stop_words: bool = True,
            domain: str = 'general'
    ) -> List[str]:
        """从单个文本中提取词语"""
        if not text:
            return []

        # 清理文本
        text = cls._clean_text(text)

        # 分词
        if JIEBA_AVAILABLE:
            words = list(jieba.cut(text))
        else:
            # 基础分词：提取连续的中文字符
            words = re.findall(r'[\u4e00-\u9fa5]+', text)

        # 过滤
        filtered_words = []
        stop_words = cls.STOP_WORDS
        if domain == 'legal':
            stop_words = stop_words.union(cls.LEGAL_STOP_WORDS)

        for word in words:
            # 过滤长度
            if len(word) < min_word_length or len(word) > max_word_length:
                continue

            # 过滤停用词
            if use_stop_words and word in stop_words:
                continue

            # 过滤数字
            if word.isdigit():
                continue

            # 过滤单个字符（如"第"、"个"等）
            if len(word) == 1 and word in '第个位项款条章':
                continue

            filtered_words.append(word)

        return filtered_words

    @classmethod
    def _extract_with_tfidf(
            cls,
            texts: List[str],
            top_k: int,
            min_word_length: int,
            max_word_length: int,
            domain: str
    ) -> List[Dict[str, int]]:
        """
        使用TF-IDF算法提取关键词

        jieba.analyse.extract_tags使用TF-IDF算法
        """
        all_keywords = []

        for text in texts:
            try:
                # 使用jieba的TF-IDF算法提取关键词
                # withWeight=True返回关键词及其权重
                keywords_with_weights = jieba.analyse.extract_tags(
                    text,
                    topK=top_k * 2,  # 提取更多，后续去重
                    withWeight=True,
                    allowPOS=('n', 'nr', 'ns', 'nt', 'nz')  # 名词相关词性
                )

                for word, weight in keywords_with_weights:
                    # 过滤长度
                    if len(word) < min_word_length or len(word) > max_word_length:
                        continue

                    # 过滤停用词
                    stop_words = cls.STOP_WORDS
                    if domain == 'legal':
                        stop_words = stop_words.union(cls.LEGAL_STOP_WORDS)

                    if word in stop_words:
                        continue

                    all_keywords.append(word)

            except Exception as e:
                logger.warning(f"TF-IDF提取关键词失败: {e}")

        # 统计出现频率
        word_counter = Counter(all_keywords)

        hot_topics = [
            {"topic": word, "count": count}
            for word, count in word_counter.most_common(top_k)
        ]

        return hot_topics

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """清理文本，移除特殊字符"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        # 移除特殊字符和标点（保留中文）
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', text)

        # 移除多余空格
        text = ' '.join(text.split())

        return text.strip()

    @classmethod
    def add_user_dictionary(cls, dict_path: str) -> bool:
        """
        添加用户自定义词典

        Args:
            dict_path: 词典文件路径

        Returns:
            是否成功
        """
        if not JIEBA_AVAILABLE:
            logger.warning("jieba未安装，无法加载自定义词典")
            return False

        try:
            jieba.load_userdict(dict_path)
            logger.info(f"成功加载自定义词典: {dict_path}")
            return True
        except Exception as e:
            logger.error(f"加载自定义词典失败: {e}")
            return False

    @classmethod
    def extract_single_text_keywords(
            cls,
            text: str,
            top_k: int = 10,
            min_word_length: int = 2,
            max_word_length: int = 4,
            domain: str = 'general'
    ) -> List[str]:
        """
        从单个文本中提取关键词

        Args:
            text: 文本内容
            top_k: 返回的关键词数量
            min_word_length: 最小词长度
            max_word_length: 最大词长度
            domain: 领域

        Returns:
            关键词列表
        """
        if not text:
            return []

        # 清理文本
        text = cls._clean_text(text)

        if JIEBA_AVAILABLE:
            # 使用jieba.analyse提取关键词
            try:
                keywords = jieba.analyse.extract_tags(
                    text,
                    topK=top_k,
                    withWeight=False,
                    allowPOS=('n', 'nr', 'ns', 'nt', 'nz')
                )

                # 过滤长度和停用词
                result = []
                stop_words = cls.STOP_WORDS
                if domain == 'legal':
                    stop_words = stop_words.union(cls.LEGAL_STOP_WORDS)

                for word in keywords:
                    if min_word_length <= len(word) <= max_word_length and word not in stop_words:
                        result.append(word)

                return result
            except Exception as e:
                logger.warning(f"jieba提取关键词失败，使用基础方法: {e}")

        # 基础方法：分词后统计词频
        words = cls._extract_words_from_text(text, min_word_length, max_word_length, domain)

        word_counter = Counter(words)
        return [word for word, _ in word_counter.most_common(top_k)]

# 单例实例
text_analyzer = TextAnalyzer()