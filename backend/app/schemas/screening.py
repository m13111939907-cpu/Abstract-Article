from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.graph import GraphOut
from app.schemas.paper import PaperOut


class ScreeningBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    score: float
    passed: bool
    reason: str
    model: str
    created_at: datetime


# 阅读页聚合：文献 + 图谱 + 二轮结论
class ReadingOut(BaseModel):
    paper: PaperOut
    graph: GraphOut
    screening: ScreeningBrief | None = None


class ScreeningOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paper_id: int
    score: float
    passed: bool
    reason: str
    model: str
    created_at: datetime
    paper: PaperOut


class Screen2Result(BaseModel):
    candidates: int = 0
    screened: int = 0
    passed: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)
