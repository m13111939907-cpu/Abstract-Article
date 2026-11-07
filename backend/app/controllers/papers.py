from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.mysql import get_db
from app.models.paper import Paper, ProjectPaper
from app.models.screening import LLMScreening
from app.schemas.graph import GraphOut
from app.schemas.paper import PaperOut
from app.schemas.screening import ReadingOut, ScreeningBrief
from app.services.graph import delete_paper_graph, get_paper_graph

router = APIRouter(prefix="/papers", tags=["papers"])


# 全部已抓取文献（分页）
@router.get("", response_model=list[PaperOut])
def list_papers(
    project_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Paper)
    if project_id is not None:
        stmt = stmt.join(
            ProjectPaper, ProjectPaper.paper_id == Paper.id
        ).where(ProjectPaper.project_id == project_id)
    return db.scalars(
        stmt.order_by(Paper.id.desc()).limit(limit).offset(offset)
    ).all()


# 文献详情
@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")
    return paper


# 阅读页聚合：文献 + 图谱 + 二轮结论
@router.get("/{paper_id}/reading", response_model=ReadingOut)
def read_paper(
    paper_id: int,
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    graph = GraphOut(**get_paper_graph(paper_id))

    stmt = (
        select(LLMScreening)
        .where(LLMScreening.paper_id == paper_id)
        .order_by(LLMScreening.id.desc())
        .limit(1)
    )
    if project_id is not None:
        stmt = stmt.where(LLMScreening.project_id == project_id)
    row = db.scalar(stmt)

    return ReadingOut(
        paper=PaperOut.model_validate(paper),
        graph=graph,
        screening=ScreeningBrief.model_validate(row) if row else None,
    )


# 删除文献及其关联记录和图谱
@router.delete("/{paper_id}", status_code=204)
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    delete_paper_graph(paper_id)
    db.execute(delete(ProjectPaper).where(ProjectPaper.paper_id == paper_id))
    db.execute(delete(LLMScreening).where(LLMScreening.paper_id == paper_id))
    db.delete(paper)
    db.commit()
