from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.mysql import Base


# 运行时设置（模型配置等），重启后恢复
class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
