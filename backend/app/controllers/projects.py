from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.mysql import get_db
from app.models.paper import ProjectPaper
from app.models.project import Project
from app.models.screening import LLMScreening
from app.models.source import Source
from app.schemas.paper import FetchResult, ProjectPaperOut, ScreenResult
from app.schemas.project import (
    ProjectCreate,
    ProjectOut,
    ProjectStats,
    ProjectUpdate,
)
from app.services.export import export_bibtex, export_csv
from app.services.matching import link_candidates, parse_keywords, screen_project
from app.services.rss import fetch_source, store_items
from app.services.search import search_openalex

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


# 项目列表（分页）
@router.get("", response_model=list[ProjectOut])
def list_projects(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Project).order_by(Project.id.desc()).limit(limit).offset(offset)
    ).all()


# 修改项目名称或关键词
@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)
):
    project = _get_project(db, project_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


# 删除项目及其筛选记录（文献与图谱保留）
@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = _get_project(db, project_id)

    db.execute(delete(LLMScreening).where(LLMScreening.project_id == project_id))
    db.execute(delete(ProjectPaper).where(ProjectPaper.project_id == project_id))
    db.delete(project)
    db.commit()


# 项目统计
@router.get("/{project_id}/stats", response_model=ProjectStats)
def project_stats(project_id: int, db: Session = Depends(get_db)):
    _get_project(db, project_id)

    total_papers = (
        db.scalar(
            select(func.count(ProjectPaper.id)).where(
                ProjectPaper.project_id == project_id
            )
        )
        or 0
    )
    first_selected = (
        db.scalar(
            select(func.count(ProjectPaper.id)).where(
                ProjectPaper.project_id == project_id,
                ProjectPaper.status == "selected",
            )
        )
        or 0
    )
    second_screened = (
        db.scalar(
            select(func.count(LLMScreening.id)).where(
                LLMScreening.project_id == project_id
            )
        )
        or 0
    )
    second_passed = (
        db.scalar(
            select(func.count(LLMScreening.id)).where(
                LLMScreening.project_id == project_id,
                LLMScreening.passed.is_(True),
            )
        )
        or 0
    )

    return ProjectStats(
        project_id=project_id,
        total_papers=total_papers,
        first_selected=first_selected,
        second_screened=second_screened,
        second_passed=second_passed,
        second_rejected=second_screened - second_passed,
    )


# 导出 CSV / BibTeX
@router.get("/{project_id}/export")
def export_project(
    project_id: int,
    fmt: Literal["csv", "bibtex"] = Query(default="csv", alias="format"),
    stage: Literal["first", "second"] = Query(default="second"),
    passed: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    _get_project(db, project_id)

    if fmt == "csv":
        content = export_csv(db, project_id, stage, passed)
        media_type = "text/csv; charset=utf-8"
        ext = "csv"
    else:
        content = export_bibtex(db, project_id, stage, passed)
        media_type = "application/x-bibtex; charset=utf-8"
        ext = "bib"

    filename = f'project_{project_id}_{stage}.{ext}'
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# 抓取订阅源（不传 source_id 则抓取全部启用的源）
@router.post("/{project_id}/fetch", response_model=FetchResult)
def fetch_project_sources(
    project_id: int,
    source_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    project = _get_project(db, project_id)

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

    # 按项目关键词做一次 OpenAlex 学术检索
    keywords = parse_keywords(project.keywords)
    if keywords:
        try:
            items = search_openalex(keywords, limit=100)
            topic = store_items(db, items)
            result.topic_fetched = topic["fetched"]
            result.topic_inserted = topic["inserted"]
            result.fetched += topic["fetched"]
            result.inserted += topic["inserted"]
            result.duplicated += topic["duplicated"]
            result.errors.extend(topic["errors"])
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"OpenAlex: {exc}")

    # 把命中关键词的文献关联到当前项目
    result.candidates = link_candidates(db, project)
    result.project_candidates = (
        db.scalar(
            select(func.count(ProjectPaper.id)).where(
                ProjectPaper.project_id == project_id
            )
        )
        or 0
    )
    return result


# 对项目执行首轮字符匹配筛选
@router.post("/{project_id}/screen", response_model=ScreenResult)
def screen(project_id: int, db: Session = Depends(get_db)):
    project = _get_project(db, project_id)
    return ScreenResult(**screen_project(db, project))


# 查看项目下已筛选出的文献（分页）
@router.get("/{project_id}/papers", response_model=list[ProjectPaperOut])
def list_project_papers(
    project_id: int,
    status: str | None = Query(default="selected"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    _get_project(db, project_id)

    stmt = select(ProjectPaper).options(
        selectinload(ProjectPaper.paper)
    ).where(ProjectPaper.project_id == project_id)
    if status:
        stmt = stmt.where(ProjectPaper.status == status)
    stmt = (
        stmt.order_by(ProjectPaper.match_score.desc(), ProjectPaper.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()
