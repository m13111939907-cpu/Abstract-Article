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
JUNK_WORDS = ("封面", "封底", "目录", "征稿", "启事", "广告", "编委", "会议通知", "招聘", "投稿指南", "更正", "致谢")


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
        # 过滤期刊 RSS 里的封面、目录、征稿等非论文条目
        if any(word in title for word in JUNK_WORDS) and len(title) <= 24:
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


# 批量写入文献并按 content_hash 去重（一次查询 + 一次提交）
def store_items(db: Session, items: list[dict], source_id: int | None = None) -> dict:
    result = {
        "fetched": len(items),
        "inserted": 0,
        "duplicated": 0,
        "errors": [],
        "hashes": [],
    }

    unique: dict[str, dict] = {}
    for item in items:
        key = item["content_hash"]
        if key in unique:
            result["duplicated"] += 1
            continue
        unique[key] = item

    hashes = list(unique.keys())
    result["hashes"] = hashes
    if not hashes:
        return result

    existing = set(
        db.scalars(select(Paper.content_hash).where(Paper.content_hash.in_(hashes)))
    )
    result["duplicated"] += len(existing)

    new_items = [item for key, item in unique.items() if key not in existing]
    if not new_items:
        return result

    db.add_all([Paper(source_id=source_id, **item) for item in new_items])
    try:
        db.commit()
        result["inserted"] = len(new_items)
    except IntegrityError:
        # 并发冲突时回退到逐条写入
        db.rollback()
        for item in new_items:
            try:
                db.add(Paper(source_id=source_id, **item))
                db.commit()
                result["inserted"] += 1
            except IntegrityError:
                db.rollback()
                result["duplicated"] += 1

    return result


# 抓取单个订阅源并入库，返回统计
def fetch_source(db: Session, source: Source) -> dict:
    try:
        feed = fetch_feed(source.rss_url)
    except Exception as exc:  # noqa: BLE001
        return {
            "fetched": 0,
            "inserted": 0,
            "duplicated": 0,
            "errors": [f"{source.name}: {exc}"],
            "hashes": [],
        }

    return store_items(db, parse_entries(feed), source.id)
