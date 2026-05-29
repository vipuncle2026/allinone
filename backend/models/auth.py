"""用户认证模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    security_code = Column(String(64), nullable=True, comment="安全码，用于忘记密码时重置")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SessionToken(Base):
    """会话 Token（持久化，重启不丢失）"""
    __tablename__ = "session_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_session_token_user_expires", "user_id", "expires_at"),
    )
