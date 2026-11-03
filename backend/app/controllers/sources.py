from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.mysql import get_db
from app.models.paper import Paper
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceOut, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


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


# 删除订阅源
@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="订阅源不存在")

    # 已有文献引用时禁止删除，避免外键冲突
    used = db.scalar(select(Paper.id).where(Paper.source_id == source_id).limit(1))
    if used:
        raise HTTPException(status_code=409, detail="该订阅源下已有文献，无法删除")

    db.delete(source)
    db.commit()
