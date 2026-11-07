import re
from datetime import datetime

import httpx

from app.services.rss import content_hash
from app.services.text import clean_text, extract_keywords, top_words

OPENALEX_URL = "https://api.openalex.org/works"
MAILTO = "article-abstract-demo@example.com"
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


# 把 OpenAlex 的倒排索引还原成摘要
def _abstract(inverted: dict | None) -> str:
    if not inverted:
        return ""
    position: dict[int, str] = {}
    for word, indexes in inverted.items():
        for index in indexes:
            position[index] = word
    return " ".join(position[i] for i in sorted(position))


# 作者名拼接
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


# 按项目关键词在 OpenAlex 检索论文
def search_openalex(keywords: list[str], limit: int = 50) -> list[dict]:
    query = " ".join(keywords).strip()
    if not query:
        return []

    params = {
        "search": query,
        "per-page": min(limit, 200),
        "sort": "relevance_score:desc",
        "mailto": MAILTO,
    }
    # 中文关键词时只返回中文文献
    if CJK_RE.search(query):
        params["filter"] = "language:zh"

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
