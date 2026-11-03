import hashlib
import time
from datetime import datetime

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.source import Source
from app.services.text import (
    clean_text,
    extract_keywords,
    strip_feed_metadata,
    top_words,
)

USER_AGENT = "Mozilla/5.0 (compatible; ArticleAbstract/1.0)"
MAX_ABSTRACT_LEN = 5000


# 下载 RSS 内容并解析
def fetch_feed(url: str, timeout: int = 20) -> "feedparser.FeedParserDict":
    resp = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    return feedparser.parse(resp.content)


# 取正文：优先 content，其次 summary
def _entry_body(entry) -> str:
    if entry.get("content"):
        return entry.content[0].get("value", "")
    return entry.get("summary", "") or entry.get("description", "")


# 取作者列表
def _entry_authors(entry) -> str:
    names = [a.get("name", "") for a in (entry.get("authors") or []) if a.get("name")]
    if not names and entry.get("author"):
        names = [entry.author]
    return ", ".join(names)


# 取发布时间
def _entry_datetime(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(time.mktime(value))
    return None


# 去重哈希：优先 DOI，其次链接、标题
def content_hash(title: str, url: str, doi: str) -> str:
    raw = (doi or url or title).strip().lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# 把 feed 条目转换成待入库的文献数据
def parse_entries(feed: "feedparser.FeedParserDict") -> list[dict]:
    items: list[dict] = []
    for entry in feed.entries:
        title = clean_text(entry.get("title", ""))[:512]
        if not title:
            continue
        link = (entry.get("link") or "")[:1024]
        doi = (entry.get("prism_doi") or entry.get("doi") or "")[:255]

        body = _entry_body(entry)
        abstract = strip_feed_metadata(
            clean_text(entry.get("summary", "") or body)
        )[:MAX_ABSTRACT_LEN]
        full_text = strip_feed_metadata(clean_text(body))

        items.append(
            {
                "title": title,
                "authors": _entry_authors(entry),
                "abstract": abstract,
                "keywords": extract_keywords(abstract or full_text),
                "top_words": top_words(full_text or abstract),
                "url": link,
                "doi": doi,
                "content_hash": content_hash(title, link, doi),
                "published_at": _entry_datetime(entry),
            }
        )
    return items


# 抓取单个订阅源并入库，返回统计
def fetch_source(db: Session, source: Source) -> dict:
    result = {"fetched": 0, "inserted": 0, "duplicated": 0, "errors": []}

    try:
        feed = fetch_feed(source.rss_url)
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"{source.name}: {exc}")
        return result

    items = parse_entries(feed)
    result["fetched"] = len(items)

    seen: set[str] = set()
    for item in items:
        key = item["content_hash"]
        if key in seen:
            result["duplicated"] += 1
            continue
        seen.add(key)

        # 已存在则跳过（哈希表去重）
        exists = db.scalar(select(Paper.id).where(Paper.content_hash == key))
        if exists:
            result["duplicated"] += 1
            continue

        db.add(Paper(source_id=source.id, **item))
        try:
            db.commit()
            result["inserted"] += 1
        except IntegrityError:
            db.rollback()
            result["duplicated"] += 1

    return result
