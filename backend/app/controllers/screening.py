from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.mysql import get_db
from app.models.project import Project
from app.models.screening import LLMScreening
from app.schemas.screening import Screen2Result, ScreeningOut
from app.services.second_screen import screen_project_round2

router = APIRouter(tags=["screening"])


# 对项目执行第二轮 LLM 筛选
@router.post("/projects/{project_id}/screen2", response_model=Screen2Result)
def screen2(
    project_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return Screen2Result(**screen_project_round2(db, project, limit))


# 查看第二轮筛选结果
@router.get("/projects/{project_id}/screen2", response_model=list[ScreeningOut])
def list_screen2(
    project_id: int,
    passed: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="项目不存在")

    stmt = select(LLMScreening).options(
        selectinload(LLMScreening.paper)
    ).where(LLMScreening.project_id == project_id)
    if passed is not None:
        stmt = stmt.where(LLMScreening.passed.is_(passed))
    stmt = (
        stmt.order_by(LLMScreening.score.desc(), LLMScreening.id)
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()
