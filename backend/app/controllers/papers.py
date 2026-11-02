from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.mysql import get_db
from app.models.paper import Paper
from app.schemas.paper import PaperOut

router = APIRouter(prefix="/papers", tags=["papers"])


# 全部已抓取文献（分页）
@router.get("", response_model=list[PaperOut])
def list_papers(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Paper).order_by(Paper.id.desc()).limit(limit).offset(offset)
    ).all()


# 文献详情
@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")
    return paper
