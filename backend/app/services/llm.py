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

# 运行时模型配置（由设置接口写入，重启后端后恢复环境变量默认值）
_runtime: dict = {}


def _clean_name(name: str) -> str:
    return name.strip().strip(".,;:()[]{}")


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

    def translate(self, text: str) -> str:
        return ""

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

TRANSLATE_PROMPT = (
    "把输入的中文研究关键词翻译成英文。只输出 JSON："
    '{"translation":"english keywords"}。'
)

JUDGE_PROMPT = (
    "你是文献筛选助手。根据研究关键词、论文摘要和知识图谱实体，判断论文是否相关。"
    '只输出 JSON：{"relevant":true,"score":0.0,"reason":""}。'
    "score 取 0 到 1，reason 用一句中文说明。"
)


# OpenAI 兼容接口：DeepSeek、Hugging Face TGI、自定义服务都能用
class OpenAICompatProvider:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.name = model or "openai-compatible"
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _request(self, system: str, user: str) -> dict:
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
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

    def translate(self, text: str) -> str:
        result = self._request(TRANSLATE_PROMPT, text[:500])
        if isinstance(result, dict):
            return str(result.get("translation") or "")
        return ""

    def judge(self, keywords: list[str], abstract: str, entities: list[str]) -> dict:
        context = (
            f"研究关键词：{', '.join(keywords)}\n"
            f"论文摘要：{abstract[:3000]}\n"
            f"图谱实体：{', '.join(entities[:30])}"
        )
        return self._request(JUDGE_PROMPT, context)


# 设置接口写入运行时配置
def set_runtime_config(config: dict) -> None:
    _runtime.clear()
    _runtime.update(config)


# 把运行时配置写入数据库，后端重启后仍可恢复
def persist_runtime_config() -> None:
    from app.core.mysql import SessionLocal
    from app.models.setting import AppSetting

    with SessionLocal() as db:
        row = db.get(AppSetting, "llm")
        value = json.dumps(_runtime, ensure_ascii=False)
        if row:
            row.value = value
        else:
            db.add(AppSetting(key="llm", value=value))
        db.commit()


# 启动时从数据库恢复模型配置
def load_runtime_config() -> None:
    from app.core.mysql import SessionLocal
    from app.models.setting import AppSetting

    with SessionLocal() as db:
        row = db.get(AppSetting, "llm")
        if not row or not row.value:
            return
        try:
            data = json.loads(row.value)
        except ValueError:
            return
        if isinstance(data, dict):
            _runtime.update(data)


def get_runtime_config() -> dict:
    provider = _runtime.get("provider") or (
        "deepseek" if settings.deepseek_api_key else "mock"
    )
    return {
        "provider": provider,
        "model": _runtime.get("model") or settings.deepseek_model,
        "base_url": _runtime.get("base_url") or settings.deepseek_base_url,
        "has_key": bool(_runtime.get("api_key") or settings.deepseek_api_key),
    }


# 有可用 key 用真实接口，否则用 Mock
def get_provider():
    config = get_runtime_config()
    if config["provider"] == "mock" or not config["has_key"]:
        return MockProvider()

    api_key = _runtime.get("api_key") or settings.deepseek_api_key
    return OpenAICompatProvider(api_key, config["base_url"], config["model"])
