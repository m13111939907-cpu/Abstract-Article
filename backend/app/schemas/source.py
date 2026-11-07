from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    rss_url: str = Field(min_length=1, max_length=512)

    # 去掉首尾空白，并校验 RSS 地址格式
    @field_validator("name", "rss_url")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value

    @field_validator("rss_url")
    @classmethod
    def http_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("必须是 http(s) 地址")
        return value


# 启用/禁用订阅源
class SourceUpdate(BaseModel):
    enabled: bool


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rss_url: str
    enabled: bool
    created_at: datetime


class SourcePreviewItem(BaseModel):
    title: str
    link: str
    published_at: datetime | None = None
    summary: str = ""


class SourcePreview(BaseModel):
    source_id: int
    source_name: str
    feed_title: str
    total: int
    items: list[SourcePreviewItem]
