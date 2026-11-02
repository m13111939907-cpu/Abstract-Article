from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.mysql import get_db
from app.models.paper import ProjectPaper
from app.models.project import Project
from app.models.source import Source
from app.schemas.paper import FetchResult, ProjectPaperOut, ScreenResult
from app.schemas.project import ProjectCreate, ProjectOut
from app.services.matching import screen_project
from app.services.rss import fetch_source

router = APIRouter(prefix="/projects", tags=["projects"])


# 取项目，不存在则 404
def _get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


# 新建检索项目
@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=payload.name, keywords=payload.keywords)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# 项目列表
@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(Project).order_by(Project.id.desc())).all()


# 抓取订阅源（不传 source_id 则抓取全部启用的源）
@router.post("/{project_id}/fetch", response_model=FetchResult)
def fetch_project_sources(
    project_id: int,
    source_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    _get_project(db, project_id)

    if source_id:
        source = db.get(Source, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="订阅源不存在")
        sources = [source]
    else:
        sources = db.scalars(select(Source).where(Source.enabled.is_(True))).all()

    result = FetchResult()
    for source in sources:
        stats = fetch_source(db, source)
        result.fetched += stats["fetched"]
        result.inserted += stats["inserted"]
        result.duplicated += stats["duplicated"]
        result.errors.extend(stats["errors"])
    return result


# 对项目执行首轮字符匹配筛选
@router.post("/{project_id}/screen", response_model=ScreenResult)
def screen(project_id: int, db: Session = Depends(get_db)):
    project = _get_project(db, project_id)
    return ScreenResult(**screen_project(db, project))


# 查看项目下已筛选出的文献
@router.get("/{project_id}/papers", response_model=list[ProjectPaperOut])
def list_project_papers(
    project_id: int,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    _get_project(db, project_id)

    stmt = (
        select(ProjectPaper)
        .options(selectinload(ProjectPaper.paper))
        .where(ProjectPaper.project_id == project_id)
        .order_by(ProjectPaper.match_score.desc(), ProjectPaper.id.desc())
    )
    if status:
        stmt = stmt.where(ProjectPaper.status == status)
    return db.scalars(stmt).all()
