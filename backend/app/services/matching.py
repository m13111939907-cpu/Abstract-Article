import re

from sqlalchemy import select
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


# 对项目执行首轮筛选，有命中的文献写入 project_papers
def screen_project(db: Session, project: Project) -> dict:
    keywords = parse_keywords(project.keywords)
    linked_ids = set(
        db.scalars(
            select(ProjectPaper.paper_id).where(ProjectPaper.project_id == project.id)
        )
    )

    all_papers = db.scalars(select(Paper)).all()
    candidates = [p for p in all_papers if p.id not in linked_ids]

    selected = 0
    for paper in candidates:
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
        "candidates": len(candidates),
        "selected": selected,
        "skipped": len(linked_ids),
    }
