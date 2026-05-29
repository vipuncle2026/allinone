"""旅行管理数据模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Date
from datetime import datetime

from database import Base


# 支出分类配置
EXPENSE_CATEGORIES = {
    '交通': {'icon': '🚄', 'color': '#3B82F6'},
    '住宿': {'icon': '🏨', 'color': '#8B5CF6'},
    '餐饮': {'icon': '🍜', 'color': '#F59E0B'},
    '景点': {'icon': '🎫', 'color': '#10B981'},
    '购物': {'icon': '🛍️', 'color': '#EC4899'},
    '通讯': {'icon': '📱', 'color': '#6366F1'},
    '其他': {'icon': '📌', 'color': '#6B7280'},
}

# 交通方式配置
TRANSPORT_TYPES = {
    '飞机': {'icon': '✈️', 'color': '#3B82F6'},
    '高铁': {'icon': '🚄', 'color': '#2D7D6F'},
    '汽车': {'icon': '🚗', 'color': '#F59E0B'},
    '巴士': {'icon': '🚌', 'color': '#8B5CF6'},
    '轮船': {'icon': '🚢', 'color': '#06B6D4'},
    '步行': {'icon': '🚶', 'color': '#10B981'},
    '骑行': {'icon': '🚲', 'color': '#EC4899'},
    '其他': {'icon': '📍', 'color': '#6B7280'},
}


class TravelTrip(Base):
    """旅行"""
    __tablename__ = "travel_trips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="旅行名称")
    destination = Column(String(200), default="", comment="目的地")
    start_date = Column(Date, default=None, comment="开始日期")
    end_date = Column(Date, default=None, comment="结束日期")
    budget = Column(Float, default=0, comment="预算金额")
    currency = Column(String(10), default="¥", comment="币种")
    planned_km = Column(Float, default=0, comment="预计里程(km)")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class TravelExpense(Base):
    """旅行支出"""
    __tablename__ = "travel_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, nullable=False, index=True, comment="关联旅行ID")
    date = Column(String(20), nullable=False, index=True, comment="日期时间")
    category = Column(String(20), nullable=False, comment="分类")
    amount = Column(Float, nullable=False, default=0, comment="金额")
    note = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=datetime.now)


class TravelMileage(Base):
    """旅行里程"""
    __tablename__ = "travel_mileages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, nullable=False, index=True, comment="关联旅行ID")
    date = Column(String(20), nullable=False, index=True, comment="日期时间")
    transport = Column(String(20), nullable=False, comment="交通方式")
    km = Column(Float, nullable=False, default=0, comment="里程(km)")
    from_place = Column(String(200), default="", comment="出发地")
    to_place = Column(String(200), default="", comment="目的地")
    note = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=datetime.now)
