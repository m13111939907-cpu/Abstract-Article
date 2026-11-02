from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    rss_url: str = Field(min_length=1, max_length=512)


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rss_url: str
    enabled: bool
    created_at: datetime
