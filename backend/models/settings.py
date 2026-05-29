"""用户设置模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base


class UserSetting(Base):
    """键值对用户设置表（如骑行默认FTP等）"""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True, comment="设置键")
    value = Column(Text, nullable=False, comment="设置值")
    updated_at = Column(DateTime, nullable=False)
