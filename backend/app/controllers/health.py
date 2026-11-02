from fastapi import APIRouter

from app.core.mysql import check_mysql
from app.core.neo4j import check_neo4j

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """检查 MySQL 与 Neo4j 连通性。"""
    status = {"mysql": "ok", "neo4j": "ok"}

    try:
        check_mysql()
    except Exception as exc:  # noqa: BLE001
        status["mysql"] = f"error: {exc}"

    try:
        check_neo4j()
    except Exception as exc:  # noqa: BLE001
        status["neo4j"] = f"error: {exc}"

    return status
