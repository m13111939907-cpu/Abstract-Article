import re

CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# 常见研究词的中英映射；未收录的词会尝试用已配置的 LLM 翻译
DICT = {
    "珊瑚": "coral",
    "珊瑚礁": "coral reef",
    "人工智能": "artificial intelligence",
    "机器学习": "machine learning",
    "深度学习": "deep learning",
    "强化学习": "reinforcement learning",
    "神经网络": "neural network",
    "大模型": "large language model",
    "大语言模型": "large language model",
    "自然语言处理": "natural language processing",
    "计算机视觉": "computer vision",
    "知识图谱": "knowledge graph",
    "数据挖掘": "data mining",
    "数据分析": "data analysis",
    "推荐系统": "recommender system",
    "多模态": "multimodal",
    "图像处理": "image processing",
    "语音识别": "speech recognition",
    "网络安全": "cybersecurity",
    "区块链": "blockchain",
    "云计算": "cloud computing",
    "物联网": "internet of things",
    "边缘计算": "edge computing",
    "碳中和": "carbon neutrality",
    "碳排放": "carbon emission",
    "气候变化": "climate change",
    "免疫": "immune",
    "航天": "aerospace",
    "机器人": "robot",
    "自动化": "automation",
    "控制": "control",
    "电子信息": "electronic information",
    "通信": "communication",
    "计算机": "computer",
    "软件工程": "software engineering",
    "算法": "algorithm",
    "数据库": "database",
    "操作系统": "operating system",
    "医学": "medicine",
    "生物": "biology",
    "材料": "material",
    "能源": "energy",
}

_cache: dict[str, str] = {}


# 使用已配置的真实模型翻译单个关键词
def _llm_translate(word: str) -> str:
    from app.services.llm import get_provider

    provider = get_provider()
    if getattr(provider, "name", "mock") == "mock":
        return ""
    try:
        return provider.translate(word).strip()
    except Exception:  # noqa: BLE001
        return ""


def translate_word(word: str) -> str:
    if word in _cache:
        return _cache[word]

    mapped = DICT.get(word) or _llm_translate(word)
    if mapped:
        _cache[word] = mapped
    return mapped or ""


# 把关键词扩展成「中文 + 英文」两组
def expand_keywords(keywords: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()

    for keyword in keywords:
        for value in (keyword, translate_word(keyword) if CJK_RE.search(keyword) else ""):
            if not value:
                continue
            key = value.lower()
            if key not in seen:
                seen.add(key)
                expanded.append(value)

    return expanded
