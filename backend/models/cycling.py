from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Bike(Base):
    """车辆信息"""
    __tablename__ = "bikes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    brand = Column(String(100))
    model = Column(String(100))
    color = Column(String(50))
    weight_kg = Column(Float)
    purchase_date = Column(Date)
    purchase_price = Column(Float)
    total_km = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    activities = relationship("CyclingActivity", back_populates="bike")
    maintenances = relationship("BikeMaintenanceRecord", back_populates="bike")


class BikeMaintenanceRecord(Base):
    """车辆维护记录"""
    __tablename__ = "bike_maintenance"

    id = Column(Integer, primary_key=True, index=True)
    bike_id = Column(Integer, ForeignKey("bikes.id"), nullable=False)
    component = Column(String(100))   # 链条 / 刹车片 / 轮胎 / 变速线 ...
    action = Column(String(100))      # 更换 / 调整 / 清洁 / 润滑
    date = Column(Date)
    cost = Column(Float)
    mileage_at = Column(Float)        # 维护时车辆累计里程
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    bike = relationship("Bike", back_populates="maintenances")


class CyclingActivity(Base):
    """骑行活动记录"""
    __tablename__ = "cycling_activities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    # 距离与时长
    distance_km = Column(Float)
    duration_sec = Column(Integer)

    # 海拔
    elevation_gain = Column(Float)
    elevation_loss = Column(Float)
    max_elevation = Column(Float)
    min_elevation = Column(Float)

    # 速度
    avg_speed_kmh = Column(Float)
    max_speed_kmh = Column(Float)

    # 功率（FIT 专有）
    avg_power_w = Column(Float)
    max_power_w = Column(Float)
    normalized_power = Column(Float)
    tss = Column(Float)
    ftp = Column(Integer, default=200, comment="功能阈值功率(W)，用于TSS计算")

    # 心率（FIT 专有）
    avg_heart_rate = Column(Integer)
    max_heart_rate = Column(Integer)

    # 踏频（FIT 专有）
    avg_cadence = Column(Integer)
    max_cadence = Column(Integer)

    # 热量消耗
    calories = Column(Integer, comment="热量消耗(kcal)")

    # 路线信息
    route_type = Column(String(50))   # 公路 / 山地 / 室内 / 砾石
    weather = Column(String(100))
    notes = Column(Text)

    # 文件信息
    file_type = Column(String(10))    # gpx / fit / manual
    file_path = Column(String(500))
    track_json = Column(Text)         # 精简轨迹点 JSON（地图渲染用）

    # 关联车辆
    bike_id = Column(Integer, ForeignKey("bikes.id"), nullable=True)
    bike = relationship("Bike", back_populates="activities")

    created_at = Column(DateTime, server_default=func.now())
