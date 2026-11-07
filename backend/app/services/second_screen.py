from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.paper import Paper, ProjectPaper
from app.models.project import Project
from app.models.screening import LLMScreening
from app.services.annotation import annotate_paper
from app.services.graph import get_paper_graph
from app.services.llm import get_provider
from app.services.matching import project_keywords


# 第二轮筛选：图谱 + 摘要 交给 LLM 判断，结果写入 MySQL
def screen_project_round2(db: Session, project: Project, limit: int = 20) -> dict:
    keywords = project_keywords(project.keywords)
    provider = get_provider()

    # 只取「已通过首轮、且还没二轮审阅」的文献
    papers = list(
        db.scalars(
            select(Paper)
            .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
            .outerjoin(
                LLMScreening,
                (LLMScreening.paper_id == Paper.id)
                & (LLMScreening.project_id == project.id),
            )
            .where(
                ProjectPaper.project_id == project.id,
                ProjectPaper.status == "selected",
                LLMScreening.id.is_(None),
            )
            .order_by(ProjectPaper.match_score.desc(), Paper.id)
            .limit(limit)
        )
    )

    result = {
        "candidates": len(papers),
        "screened": 0,
        "passed": 0,
        "skipped": 0,
        "errors": [],
    }

    for paper in papers:
        try:
            # 没有图就先补标注，保证图谱作为判断依据
            graph = get_paper_graph(paper.id)
            if not graph["exists"]:
                annotate_paper(paper)
                graph = get_paper_graph(paper.id)

            entities = [node["label"] for node in graph["nodes"]]
            verdict = provider.judge(keywords, paper.abstract or "", entities)
            if not isinstance(verdict, dict):
                raise ValueError("LLM 返回格式错误")
        except Exception as exc:  # noqa: BLE001
            result["errors"].append(f"paper {paper.id}: {exc}")
            continue

        try:
            score = float(verdict.get("score") or 0)
        except (TypeError, ValueError):
            score = 0.0

        passed = bool(verdict.get("relevant"))
        try:
            with db.begin_nested():
                db.add(
                    LLMScreening(
                        project_id=project.id,
                        paper_id=paper.id,
                        score=score,
                        passed=passed,
                        reason=str(verdict.get("reason") or "")[:2000],
                        model=provider.name,
                    )
                )
        except IntegrityError:
            # 并发或重复提交时已存在记录，直接跳过
            result["skipped"] += 1
            continue

        result["screened"] += 1
        result["passed"] += 1 if passed else 0

    db.commit()
    return result
