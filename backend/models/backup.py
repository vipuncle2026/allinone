"""备份操作记录模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from database import Base


class BackupLog(Base):
    __tablename__ = "backup_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operation = Column(String(10), nullable=False)  # 'export' / 'import'
    file_name = Column(String(200), default="")
    file_size = Column(Float, default=0)          # 文件大小（字节）
    record_count = Column(Integer, default=0)     # 操作涉及的记录数
    detail = Column(Text, default="")             # 操作详情（如导入统计）
    created_at = Column(DateTime, default=datetime.now)
