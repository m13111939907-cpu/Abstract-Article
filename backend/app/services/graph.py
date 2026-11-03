from app.core.neo4j import get_driver

# 覆盖写入单篇文献的图：先删除旧图，再写 Paper 与实体
_ENTITY_QUERY = """
MATCH (p:Paper {paper_id: $pid})
UNWIND $entities AS e
MERGE (n:Entity {paper_id: $pid, name: e.name})
SET n.type = e.type
MERGE (p)-[:HAS_ENTITY]->(n)
"""

_RELATION_QUERY = """
UNWIND $relations AS r
MATCH (a:Entity {paper_id: $pid, name: r.source})
MATCH (b:Entity {paper_id: $pid, name: r.target})
MERGE (a)-[rel:RELATED {paper_id: $pid, type: r.type}]->(b)
SET rel.confidence = r.confidence
"""


# 清理实体与关系：去重、过滤非法引用
def _normalize(entities: list[dict], relations: list[dict]):
    unique: dict[str, dict] = {}
    for entity in entities:
        name = (entity.get("name") or "").strip()
        if not name:
            continue
        unique.setdefault(
            name.lower(),
            {"name": name, "type": (entity.get("type") or "CONCEPT").upper()},
        )

    entity_list = list(unique.values())
    names = {e["name"] for e in entity_list}

    relation_list: list[dict] = []
    seen: set[tuple] = set()
    for relation in relations:
        source = (relation.get("source") or "").strip()
        target = (relation.get("target") or "").strip()
        rel_type = (relation.get("type") or "RELATED_TO").upper()
        if source not in names or target not in names or source == target:
            continue
        key = (source, target, rel_type)
        if key in seen:
            continue
        seen.add(key)

        try:
            confidence = float(relation.get("confidence") or 0.5)
        except (TypeError, ValueError):
            confidence = 0.5

        relation_list.append(
            {
                "source": source,
                "target": target,
                "type": rel_type,
                "confidence": confidence,
            }
        )

    return entity_list, relation_list


# 写入/覆盖一篇文献的图
def replace_paper_graph(
    paper_id: int, title: str, entities: list[dict], relations: list[dict]
) -> tuple[int, int]:
    entity_list, relation_list = _normalize(entities, relations)

    with get_driver().session() as session:
        session.run("MATCH (n {paper_id: $pid}) DETACH DELETE n", pid=paper_id).consume()
        session.run(
            "MERGE (p:Paper {paper_id: $pid}) SET p.title = $title",
            pid=paper_id,
            title=title,
        ).consume()
        if entity_list:
            session.run(_ENTITY_QUERY, pid=paper_id, entities=entity_list).consume()
        if relation_list:
            session.run(_RELATION_QUERY, pid=paper_id, relations=relation_list).consume()

    return len(entity_list), len(relation_list)


# 读取一篇文献的图
def get_paper_graph(paper_id: int) -> dict:
    with get_driver().session() as session:
        title_row = session.run(
            "MATCH (p:Paper {paper_id: $pid}) RETURN p.title AS title", pid=paper_id
        ).single()
        node_rows = session.run(
            "MATCH (e:Entity {paper_id: $pid}) "
            "RETURN e.name AS name, e.type AS type ORDER BY name",
            pid=paper_id,
        ).data()
        edge_rows = session.run(
            "MATCH (a:Entity {paper_id: $pid})-[r:RELATED {paper_id: $pid}]->"
            "(b:Entity {paper_id: $pid}) "
            "RETURN a.name AS source, b.name AS target, "
            "r.type AS type, r.confidence AS confidence",
            pid=paper_id,
        ).data()

    return {
        "paper_id": paper_id,
        "title": title_row["title"] if title_row else "",
        "exists": title_row is not None,
        "nodes": [
            {"id": row["name"], "label": row["name"], "type": row["type"] or "CONCEPT"}
            for row in node_rows
        ],
        "edges": [
            {
                "source": row["source"],
                "target": row["target"],
                "type": row["type"] or "RELATED_TO",
                "confidence": row["confidence"] or 0.5,
            }
            for row in edge_rows
        ],
    }


# 删除一篇文献的图
def delete_paper_graph(paper_id: int) -> None:
    with get_driver().session() as session:
        session.run("MATCH (n {paper_id: $pid}) DETACH DELETE n", pid=paper_id).consume()


# 图谱总量统计
def graph_stats() -> dict:
    with get_driver().session() as session:
        nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        relations = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        papers = session.run("MATCH (p:Paper) RETURN count(p) AS c").single()["c"]
    return {"nodes": nodes, "relations": relations, "papers": papers}
