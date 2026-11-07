from fastapi import APIRouter

from app.schemas.settings import LLMSettingsIn, LLMSettingsOut
from app.services.llm import (
    get_runtime_config,
    persist_runtime_config,
    set_runtime_config,
)

router = APIRouter(prefix="/settings", tags=["settings"])


# 读取当前模型配置（不返回明文 key）
@router.get("/llm", response_model=LLMSettingsOut)
def read_llm_settings():
    return LLMSettingsOut(**get_runtime_config())


# 保存模型配置：内存生效 + 持久化到 MySQL
@router.put("/llm", response_model=LLMSettingsOut)
def update_llm_settings(payload: LLMSettingsIn):
    set_runtime_config(payload.model_dump())
    persist_runtime_config()
    return LLMSettingsOut(**get_runtime_config())
