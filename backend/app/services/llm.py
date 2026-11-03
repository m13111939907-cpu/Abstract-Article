import json
import re

import httpx

from app.core.config import settings
from app.services.text import extract_keywords

ACRONYM_RE = re.compile(r"\b[A-Z]{2,8}\b")
CAPITALIZED_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
SKIP_WORDS = {
    "The", "This", "That", "These", "Those", "Abstract", "Introduction",
    "Results", "Conclusion", "Nature", "Published", "Online",
}


# 清理实体名
def _clean_name(name: str) -> str:
    return name.strip().strip(".,;:()[]{}")


# Mock 标注：用关键词、缩写、专有名词模拟 LLM 结果
class MockProvider:
    def annotate(self, text: str) -> dict:
        entities: dict[str, dict] = {}

        for word in extract_keywords(text, top_k=8):
            name = _clean_name(word)
            if len(name) > 1:
                entities.setdefault(name.lower(), {"name": name, "type": "CONCEPT"})

        for acronym in ACRONYM_RE.findall(text)[:5]:
            entities.setdefault(acronym.lower(), {"name": acronym, "type": "ACRONYM"})

        for word in CAPITALIZED_RE.findall(text)[:6]:
            if word not in SKIP_WORDS:
                entities.setdefault(word.lower(), {"name": word, "type": "METHOD"})

        entity_list = list(entities.values())[:12]

        # 前几个实体两两建立关联，模拟关系抽取
        relations = []
        base = entity_list[:6]
        for i in range(len(base)):
            for j in range(i + 1, len(base)):
                if len(relations) >= 8:
                    break
                relations.append(
                    {
                        "source": base[i]["name"],
                        "target": base[j]["name"],
                        "type": "RELATED_TO",
                        "confidence": round(0.6 + (i + j) % 3 * 0.1, 2),
                    }
                )

        return {"entities": entity_list, "relations": relations}


SYSTEM_PROMPT = (
    "你是文献信息抽取助手。只输出 JSON，格式为 "
    '{"entities":[{"name":"","type":""}],'
    '"relations":[{"source":"","target":"","type":"","confidence":0.0}]}。'
    "实体类型限定 CONCEPT/ACRONYM/METHOD/DATASET/PERSON/ORG。"
)


# 真实 DeepSeek 接口（配置 key 后启用）
class DeepSeekProvider:
    def annotate(self, text: str) -> dict:
        resp = httpx.post(
            f"{settings.deepseek_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": settings.deepseek_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text[:6000]},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)


# 有 key 用 DeepSeek，否则用 Mock
def get_provider():
    return DeepSeekProvider() if settings.deepseek_api_key else MockProvider()
