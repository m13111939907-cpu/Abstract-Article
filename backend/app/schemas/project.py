from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    keywords: str = Field(min_length=1, max_length=2000, description="逗号分隔的检索关键词")

    # 去掉首尾空白并拒绝纯空白输入
    @field_validator("name", "keywords")
    @classmethod
    def not_blank(cls, value: str) -> str:
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
