from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.mysql_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# 所有 ORM 模型的基类
class Base(DeclarativeBase):
    pass


# FastAPI 依赖：每个请求一个 Session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 健康检查用
def check_mysql() -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


# 启动时建表（Step 2 阶段用 create_all，后续可换 Alembic）
def init_db() -> None:
    from app import models  # noqa: F401  确保模型已注册到 Base

    Base.metadata.create_all(bind=engine)
