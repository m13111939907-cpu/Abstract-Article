from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# 新建项目
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    keywords: str = Field(min_length=1, max_length=2000, description="逗号分隔的检索关键词")

    @field_validator("name", "keywords")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value


# 更新项目（字段可选）
class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    keywords: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("name", "keywords")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    keywords: str
    created_at: datetime


# 项目统计
class ProjectStats(BaseModel):
    project_id: int
    total_papers: int
    first_selected: int
    second_screened: int
    second_passed: int
    second_rejected: int
