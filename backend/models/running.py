from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class RunningActivity(Base):
    """跑步活动记录"""
    __tablename__ = "running_activities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    # 距离与时长
    distance_km = Column(Float)
    duration_sec = Column(Integer)

    # 海拔（部分跑步有）
    elevation_gain = Column(Float)
    elevation_loss = Column(Float)
    max_elevation = Column(Float)
    min_elevation = Column(Float)

    # 速度与配速
    avg_speed_kmh = Column(Float)
    max_speed_kmh = Column(Float)
    pace_min_km = Column(Float)        # 配速（分钟/公里）

    # 心率
    avg_heart_rate = Column(Integer)
    max_heart_rate = Column(Integer)

    # 热量
    calories = Column(Float)

    # 步频
    avg_cadence = Column(Integer)
    max_cadence = Column(Integer)

    # 步数
    steps = Column(Integer)

    # 跑步信息
    running_route = Column(String(200))   # 跑步路线
    weather = Column(String(100))
    notes = Column(Text)

    # 文件信息
    file_type = Column(String(10))     # gpx / fit / tcx / manual
    file_path = Column(String(500))
    track_json = Column(Text)          # 精简轨迹点 JSON

    created_at = Column(DateTime, server_default=func.now())
