from sqlalchemy import select

from app.core.mysql import SessionLocal
from app.models.source import Source


# 首次启动时插入默认订阅源（Nature 演示）
def seed_default_sources() -> None:
    with SessionLocal() as db:
        exists = db.scalar(select(Source.id).limit(1))
        if exists:
            return
        db.add(Source(name="Nature", rss_url="https://www.nature.com/nature.rss"))
        db.commit()
