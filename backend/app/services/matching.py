import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.paper import Paper, ProjectPaper
from app.models.project import Project


# 拆分用户输入的关键词（中英文逗号、分号、空白都支持）
def parse_keywords(raw: str) -> list[str]:
    parts = re.split(r"[,，;；\s]+", raw or "")
    return [p.strip().lower() for p in parts if p.strip()]


# 纯字符匹配：标题命中 2 分，摘要/关键词/高频词命中 1 分
def match_paper(paper: Paper, keywords: list[str]) -> tuple[int, list[str]]:
    title = (paper.title or "").lower()
    body = " ".join(
        [
            paper.abstract or "",
            " ".join(paper.keywords or []),
            " ".join(paper.top_words or []),
        ]
    ).lower()

    score = 0
    matched: list[str] = []
    for keyword in keywords:
        if keyword in title:
            score += 2
            matched.append(keyword)
        elif keyword in body:
            score += 1
            matched.append(keyword)
    return score, matched


# 把库中命中关键词的文献关联为项目候选
def link_candidates(db: Session, project: Project) -> int:
    keywords = parse_keywords(project.keywords)
    if not keywords:
        return 0

    linked = set(
        db.scalars(
            select(ProjectPaper.paper_id).where(ProjectPaper.project_id == project.id)
        )
    )

    added = 0
    for paper in db.scalars(select(Paper)).all():
        if paper.id in linked:
            continue
        score, matched = match_paper(paper, keywords)
        if score <= 0:
            continue
        try:
            with db.begin_nested():
                db.add(
                    ProjectPaper(
                        project_id=project.id,
                        paper_id=paper.id,
                        match_score=score,
                        matched_keywords=matched,
                        status="candidate",
                    )
                )
        except IntegrityError:
            continue
        added += 1

    db.commit()
    return added


# 首轮筛选：优先处理候选，兼容旧项目则扫描全部未关联文献
def screen_project(db: Session, project: Project) -> dict:
    keywords = parse_keywords(project.keywords)

    candidates = db.scalars(
        select(ProjectPaper).where(
            ProjectPaper.project_id == project.id,
            ProjectPaper.status == "candidate",
        )
    ).all()

    if candidates:
        selected = 0
        for link in candidates:
            paper = db.get(Paper, link.paper_id)
            if not paper:
                continue
            score, matched = match_paper(paper, keywords)
            link.match_score = score
            link.matched_keywords = matched
            link.status = "selected" if score > 0 else "rejected"
            selected += 1 if score > 0 else 0
        db.commit()
        return {"candidates": len(candidates), "selected": selected, "skipped": 0}

    linked_ids = set(
        db.scalars(
            select(ProjectPaper.paper_id).where(ProjectPaper.project_id == project.id)
        )
    )

    all_papers = db.scalars(select(Paper)).all()
    remaining = [p for p in all_papers if p.id not in linked_ids]

    selected = 0
    for paper in remaining:
        score, matched = match_paper(paper, keywords)
        if score <= 0:
            continue
        db.add(
            ProjectPaper(
                project_id=project.id,
                paper_id=paper.id,
                match_score=score,
                matched_keywords=matched,
                status="selected",
            )
        )
        selected += 1

    db.commit()
    return {
        "candidates": len(remaining),
        "selected": selected,
        "skipped": len(linked_ids),
    }
