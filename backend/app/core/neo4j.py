from neo4j import GraphDatabase

from app.core.config import settings

_driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password),
)


def get_driver():
    return _driver


def check_neo4j() -> bool:
    _driver.verify_connectivity()
    return True
