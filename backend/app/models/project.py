from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.mysql import Base


# 项目：一次文献检索任务
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    keywords: Mapped[str] = mapped_column(Text, nullable=False)  # 逗号分隔的检索关键词
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    papers = relationship(
        "ProjectPaper", back_populates="project", cascade="all, delete-orphan"
    )
