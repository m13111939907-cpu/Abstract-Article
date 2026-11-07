from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaperOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    authors: str
    abstract: str
    keywords: list[str]
    top_words: list[str]
    url: str
    doi: str
    published_at: datetime | None


class ProjectPaperOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_score: int
    matched_keywords: list[str]
    status: str
    paper: PaperOut


# 抓取结果统计
class FetchResult(BaseModel):
    fetched: int = 0
    inserted: int = 0
    duplicated: int = 0
    topic_fetched: int = 0
    topic_inserted: int = 0
    candidates: int = 0
    project_candidates: int = 0
    errors: list[str] = Field(default_factory=list)


# 首轮筛选结果统计
class ScreenResult(BaseModel):
    candidates: int = 0
    selected: int = 0
    skipped: int = 0
