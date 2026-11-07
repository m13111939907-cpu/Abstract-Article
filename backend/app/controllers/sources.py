import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.mysql import get_db
from app.models.paper import Paper
from app.models.source import Source
from app.schemas.source import (
    SourceCreate,
    SourceOut,
    SourcePreview,
    SourcePreviewItem,
    SourceUpdate,
)
from app.services.rss import fetch_feed
from app.services.text import clean_text

router = APIRouter(prefix="/sources", tags=["sources"])


# 从 feed 条目读取发布时间
def _entry_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(time.mktime(value))
    return None


# 添加订阅源
@router.post("", response_model=SourceOut, status_code=201)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(Source).where(Source.rss_url == payload.rss_url))
    if exists:
        raise HTTPException(status_code=409, detail="该 RSS 源已存在")

    source = Source(name=payload.name, rss_url=payload.rss_url)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


# 订阅源列表
@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return db.scalars(select(Source).order_by(Source.id)).all()


# 预览 RSS 最新条目（不入库，仅用于确认真实抓取内容）
@router.get("/{source_id}/preview", response_model=SourcePreview)
def preview_source(
    source_id: int,
    limit: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="订阅源不存在")

    try:
        feed = fetch_feed(source.rss_url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"RSS 读取失败: {exc}") from exc

    items = []
    for entry in feed.entries[:limit]:
        items.append(
            SourcePreviewItem(
                title=clean_text(entry.get("title", "")) or "(无标题)",
                link=entry.get("link", ""),
                published_at=_entry_time(entry),
                summary=clean_text(entry.get("summary", ""))[:300],
            )
        )

    return SourcePreview(
        source_id=source.id,
        source_name=source.name,
        feed_title=clean_text(feed.feed.get("title", "")) or source.name,
        total=len(feed.entries),
        items=items,
    )


# 启用/禁用订阅源
@router.patch("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: int, payload: SourceUpdate, db: Session = Depends(get_db)
):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="订阅源不存在")

    source.enabled = payload.enabled
    db.commit()
    db.refresh(source)
    return source


# 删除订阅源；已入库文献保留，只解除来源关联
@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="订阅源不存在")

    db.execute(update(Paper).where(Paper.source_id == source_id).values(source_id=None))
    db.delete(source)
    db.commit()
