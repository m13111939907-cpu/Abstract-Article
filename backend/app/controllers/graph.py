from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.mysql import get_db
from app.models.paper import Paper
from app.models.project import Project
from app.schemas.graph import (
    AnnotateResult,
    BatchAnnotateResult,
    GraphOut,
    GraphStats,
)
from app.services.annotation import annotate_paper, project_papers
from app.services.graph import delete_paper_graph, get_paper_graph, graph_stats

router = APIRouter(tags=["graph"])


# 单篇文献标注并写入图谱
@router.post("/papers/{paper_id}/annotate", response_model=AnnotateResult)
def annotate_one(paper_id: int, db: Session = Depends(get_db)):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    try:
        entities, relations = annotate_paper(paper)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"标注失败: {exc}") from exc

    return AnnotateResult(
        paper_id=paper_id, entities=entities, relations=relations
    )


# 批量标注项目下的文献
@router.post("/projects/{project_id}/annotate", response_model=BatchAnnotateResult)
def annotate_project(
    project_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="项目不存在")

    papers = project_papers(db, project_id, limit)
    result = BatchAnnotateResult(project_id=project_id, total=len(papers))

    for paper in papers:
        try:
            entities, relations = annotate_paper(paper)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"paper {paper.id}: {exc}")
            continue
        result.annotated += 1
        result.entities += entities
        result.relations += relations

    return result


# 读取一篇文献的图
@router.get("/papers/{paper_id}/graph", response_model=GraphOut)
def read_graph(paper_id: int):
    return get_paper_graph(paper_id)


# 删除一篇文献的图
@router.delete("/papers/{paper_id}/graph", status_code=204)
def remove_graph(paper_id: int):
    delete_paper_graph(paper_id)


# 图谱总量统计
@router.get("/graph/stats", response_model=GraphStats)
def stats():
    return graph_stats()
