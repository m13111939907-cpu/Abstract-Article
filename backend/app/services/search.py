import re
from datetime import datetime

import httpx

from app.services.rss import content_hash
from app.services.text import clean_text, extract_keywords, top_words

OPENALEX_URL = "https://api.openalex.org/works"
MAILTO = "article-abstract-demo@example.com"
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _abstract(inverted: dict | None) -> str:
    if not inverted:
        return ""
    position: dict[int, str] = {}
    for word, indexes in inverted.items():
        for index in indexes:
            position[index] = word
    return " ".join(position[i] for i in sorted(position))


def _authors(work: dict) -> str:
    names = [
        item.get("author", {}).get("display_name", "")
        for item in work.get("authorships", [])[:20]
    ]
    return ", ".join(name for name in names if name)


def _published(work: dict) -> datetime | None:
    value = work.get("publication_date")
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _query(query: str, limit: int, language: str | None = None) -> list[dict]:
    params = {
        "search": query,
        "per-page": min(limit, 200),
        "sort": "relevance_score:desc",
        "mailto": MAILTO,
    }
    if language:
        params["filter"] = f"language:{language}"

    response = httpx.get(
        OPENALEX_URL,
        params=params,
        headers={"User-Agent": f"ArticleAbstract/1.0 (mailto:{MAILTO})"},
        timeout=40,
        follow_redirects=True,
    )
    response.raise_for_status()

    items: list[dict] = []
    for work in response.json().get("results", []):
        title = clean_text(work.get("title") or "")[:512]
        if not title:
            continue

        abstract = clean_text(_abstract(work.get("abstract_inverted_index")))[:5000]
        doi = (work.get("doi") or "").replace("https://doi.org/", "")[:255]
        url = (
            (work.get("primary_location") or {}).get("landing_page_url")
            or work.get("doi")
            or ""
        )[:1024]

        items.append(
            {
                "title": title,
                "authors": _authors(work)[:2000],
                "abstract": abstract,
                "keywords": extract_keywords(abstract),
                "top_words": top_words(abstract),
                "url": url,
                "doi": doi,
                "content_hash": content_hash(title, url, doi),
                "published_at": _published(work),
            }
        )
    return items


# 按关键词检索：中文词查中文库，英文词查英文库，最后合并去重
def search_openalex(keywords: list[str], limit: int = 100) -> list[dict]:
    zh_terms = [item for item in keywords if CJK_RE.search(item)]
    en_terms = [item for item in keywords if not CJK_RE.search(item)]

    items: list[dict] = []
    if zh_terms:
        items.extend(_query(" ".join(zh_terms), limit, "zh"))
    if en_terms:
        items.extend(_query(" ".join(en_terms), limit, "en"))
    if not zh_terms and not en_terms:
        items = _query(" ".join(keywords), limit)

    unique: dict[str, dict] = {}
    for item in items:
        unique.setdefault(item["content_hash"], item)

    return list(unique.values())[: limit * 2]
