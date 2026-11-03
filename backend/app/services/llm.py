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


# 去掉模型可能包裹的 ```json 代码块
def _loads(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?|```$", "", content).strip()
    return json.loads(content)


# Mock 标注：用关键词、缩写、专有名词模拟 LLM 结果
class MockProvider:
    name = "mock"

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

    # Mock 二轮判断：关键词命中摘要或图谱实体即通过
    def judge(self, keywords: list[str], abstract: str, entities: list[str]) -> dict:
        text = f"{abstract} {' '.join(entities)}".lower()
        hits = [keyword for keyword in keywords if keyword in text]
        if hits:
            score = min(1.0, 0.6 + 0.1 * (len(hits) - 1))
            return {
                "relevant": True,
                "score": round(score, 2),
                "reason": "命中关键词：" + "、".join(hits),
            }
        return {"relevant": False, "score": 0.1, "reason": "未命中任何关键词"}


ANNOTATE_PROMPT = (
    "你是文献信息抽取助手。只输出 JSON，格式为 "
    '{"entities":[{"name":"","type":""}],'
    '"relations":[{"source":"","target":"","type":"","confidence":0.0}]}。'
    "实体类型限定 CONCEPT/ACRONYM/METHOD/DATASET/PERSON/ORG。"
)

JUDGE_PROMPT = (
    "你是文献筛选助手。根据研究关键词、论文摘要和知识图谱实体，判断论文是否相关。"
    '只输出 JSON：{"relevant":true,"score":0.0,"reason":""}。'
    "score 取 0 到 1，reason 用一句中文说明。"
)


# 真实 DeepSeek 接口（配置 key 后启用）
class DeepSeekProvider:
    name = settings.deepseek_model

    def _request(self, system: str, user: str) -> dict:
        resp = httpx.post(
            f"{settings.deepseek_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": settings.deepseek_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _loads(content)

    def annotate(self, text: str) -> dict:
        return self._request(ANNOTATE_PROMPT, text[:6000])

    def judge(self, keywords: list[str], abstract: str, entities: list[str]) -> dict:
        context = (
            f"研究关键词：{', '.join(keywords)}\n"
            f"论文摘要：{abstract[:3000]}\n"
            f"图谱实体：{', '.join(entities[:30])}"
        )
        return self._request(JUDGE_PROMPT, context)


# 有 key 用 DeepSeek，否则用 Mock
def get_provider():
    return DeepSeekProvider() if settings.deepseek_api_key else MockProvider()
