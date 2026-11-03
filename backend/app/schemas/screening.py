from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.paper import PaperOut


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
