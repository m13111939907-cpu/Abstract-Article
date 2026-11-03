from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paper import Paper, ProjectPaper
from app.services.graph import replace_paper_graph
from app.services.llm import get_provider
from app.services.preprocess import preprocess_papers


# 单篇标注：预处理 → LLM 抽取 → 写 Neo4j
def annotate_paper(paper: Paper) -> tuple[int, int]:
    df = preprocess_papers([paper])
    if df.empty:
        return replace_paper_graph(paper.id, paper.title, [], [])

    text = str(df.iloc[0]["text"])
    result = get_provider().annotate(text)
    entities = result.get("entities") or []
    relations = result.get("relations") or []
    return replace_paper_graph(paper.id, paper.title, entities, relations)


# 取项目下已通过首轮筛选的文献
def project_papers(db: Session, project_id: int, limit: int) -> list[Paper]:
    return list(
        db.scalars(
            select(Paper)
            .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
            .where(ProjectPaper.project_id == project_id)
            .order_by(ProjectPaper.match_score.desc(), Paper.id)
            .limit(limit)
        )
    )
