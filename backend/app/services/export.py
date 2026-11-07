import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paper import Paper, ProjectPaper
from app.models.screening import LLMScreening

HEADER = [
    "id", "title", "authors", "doi", "url", "published_at",
    "keywords", "score", "passed", "reason",
]


# 首轮结果
def _first_rows(db: Session, project_id: int):
    rows = db.execute(
        select(ProjectPaper, Paper)
        .join(Paper, ProjectPaper.paper_id == Paper.id)
        .where(ProjectPaper.project_id == project_id)
        .where(ProjectPaper.status == "selected")
        .order_by(ProjectPaper.match_score.desc(), Paper.id)
    ).all()
    for link, paper in rows:
        yield {
            "paper": paper,
            "score": link.match_score,
            "passed": True,
            "reason": "首轮命中：" + "、".join(link.matched_keywords or []),
        }


# 二轮结果（可按是否通过过滤）
def _second_rows(db: Session, project_id: int, passed: bool | None):
    stmt = (
        select(LLMScreening, Paper)
        .join(Paper, LLMScreening.paper_id == Paper.id)
        .where(LLMScreening.project_id == project_id)
        .order_by(LLMScreening.score.desc(), Paper.id)
    )
    if passed is not None:
        stmt = stmt.where(LLMScreening.passed.is_(passed))

    for screening, paper in db.execute(stmt).all():
        yield {
            "paper": paper,
            "score": screening.score,
            "passed": screening.passed,
            "reason": screening.reason,
        }


def _rows(db: Session, project_id: int, stage: str, passed: bool | None):
    if stage == "first":
        return _first_rows(db, project_id)
    return _second_rows(db, project_id, passed)


# 导出 CSV（带 BOM，Excel 直接打开不乱码）
def export_csv(
    db: Session, project_id: int, stage: str, passed: bool | None = None
) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADER)

    for row in _rows(db, project_id, stage, passed):
        paper = row["paper"]
        writer.writerow(
            [
                paper.id,
                paper.title,
                paper.authors,
                paper.doi,
                paper.url,
                paper.published_at.isoformat() if paper.published_at else "",
                "、".join(paper.keywords or []),
                row["score"],
                row["passed"],
                row["reason"],
            ]
        )

    return "\ufeff" + buffer.getvalue()


def _escape(value: str) -> str:
    return str(value).replace("{", "(").replace("}", ")").replace("\n", " ")


# 导出 BibTeX
def export_bibtex(
    db: Session, project_id: int, stage: str, passed: bool | None = None
) -> str:
    entries = []
    for row in _rows(db, project_id, stage, passed):
        paper = row["paper"]
        fields = [
            ("title", paper.title),
            ("author", paper.authors),
            ("year", paper.published_at.year if paper.published_at else ""),
            ("doi", paper.doi),
            ("url", paper.url),
        ]
        body = ",\n".join(
            f"  {key} = {{{_escape(value)}}}"
            for key, value in fields
            if value
        )
        entries.append(f"@article{{paper{paper.id},\n{body}\n}}")

    return "\n\n".join(entries)
