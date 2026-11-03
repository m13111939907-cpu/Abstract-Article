import html
import re
from collections import Counter

import jieba
import jieba.analyse

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
EN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]{1,}")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# RSS 摘要常见的 "Nature, Published online: ...; doi:..." 前缀
FEED_META_RE = re.compile(
    r"^.*?Published online:[^;]*;\s*doi:\S+\s*", re.IGNORECASE
)

# 中英文停用词（精简版，够首轮筛选用）
EN_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "nor", "so", "yet", "if", "as",
    "at", "by", "in", "on", "of", "to", "from", "into", "over", "under",
    "about", "with", "without", "for", "than", "then", "that", "this",
    "these", "those", "there", "here", "it", "its", "is", "are", "be",
    "been", "being", "was", "were", "am", "do", "does", "did", "doing",
    "have", "has", "had", "having", "can", "could", "will", "would",
    "shall", "should", "may", "might", "must", "not", "no", "yes",
    "you", "your", "yours", "we", "our", "ours", "they", "their",
    "them", "he", "him", "his", "she", "her", "hers", "i", "me", "my",
    "who", "whom", "whose", "which", "what", "when", "where", "why",
    "how", "all", "any", "both", "each", "few", "more", "most", "less",
    "least", "other", "some", "such", "only", "own", "same", "too",
    "very", "just", "even", "still", "back", "now", "out", "up", "down",
    "off", "again", "one", "two", "first", "last", "many", "much",
    "make", "makes", "made", "take", "takes", "took", "taken", "give",
    "gives", "given", "find", "finds", "found", "show", "shows",
    "showed", "shown", "use", "uses", "used", "using", "study",
    "studies", "report", "reports", "reported", "new", "news", "year",
    "years", "day", "days", "time", "times", "way", "ways", "part",
    "parts", "like", "another", "people", "person", "researchers",
}
ZH_STOPWORDS = {
    "的", "了", "和", "是", "在", "我", "有", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
    "看", "好", "自己", "这", "那", "与", "及", "等", "对", "为", "中",
}


# 去 HTML 标签、反转义、压缩空白
def clean_text(raw: str | None) -> str:
    if not raw:
        return ""
    text = html.unescape(raw)
    text = TAG_RE.sub(" ", text)
    text = text.replace("\xa0", " ")
    return SPACE_RE.sub(" ", text).strip()


# 去掉 RSS 摘要里的出版元信息前缀
def strip_feed_metadata(text: str) -> str:
    return FEED_META_RE.sub("", text, count=1).strip()


# 英文分词并过滤停用词
def english_words(text: str) -> list[str]:
    words = [w.lower() for w in EN_WORD_RE.findall(text)]
    return [w for w in words if w not in EN_STOPWORDS and len(w) > 2]


# 中文分词结果（只保留含中文的词，长度 > 1，过滤停用词）
def chinese_words(text: str) -> list[str]:
    return [
        w.strip()
        for w in jieba.cut(text)
        if len(w.strip()) > 1 and w.strip() not in ZH_STOPWORDS and CJK_RE.search(w)
    ]


# 从摘要中抽取关键词（中英混合都支持）
def extract_keywords(text: str, top_k: int = 10) -> list[str]:
    text = clean_text(text)
    if not text:
        return []

    result: list[str] = []
    if CJK_RE.search(text):
        result.extend(jieba.analyse.extract_tags(text, topK=top_k))
    for word, _ in Counter(english_words(text)).most_common(top_k):
        result.append(word)

    # 去重保序（英文忽略大小写），截断到 top_k
    seen: set[str] = set()
    unique = []
    for word in result:
        key = word.lower()
        if key not in seen:
            seen.add(key)
            unique.append(word)
    return unique[:top_k]


# 全文高频词（中英词频合并）
def top_words(text: str, top_k: int = 10) -> list[str]:
    text = clean_text(text)
    if not text:
        return []

    counter = Counter(chinese_words(text))
    counter.update(english_words(text))
    return [word for word, _ in counter.most_common(top_k)]
