from typing import Literal

from pydantic import BaseModel, Field


class LLMSettingsIn(BaseModel):
    provider: Literal["mock", "deepseek", "huggingface", "custom"] = "mock"
    model: str = Field(default="", max_length=128)
    base_url: str = Field(default="", max_length=512)
    api_key: str = Field(default="", max_length=512)


class LLMSettingsOut(BaseModel):
    provider: str
    model: str
    base_url: str
    has_key: bool
