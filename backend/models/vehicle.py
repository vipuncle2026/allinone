from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Boolean
from sqlalchemy.sql import func
from database import Base


class Vehicle(Base):
    """机动车/汽车信息"""
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="车辆名称/昵称")
    brand = Column(String(100), comment="品牌")
    model = Column(String(100), comment="型号")
    color = Column(String(50), comment="颜色")
    plate = Column(String(20), comment="车牌号")
    fuel_type = Column(String(20), comment="燃料类型：汽油/柴油/电动/混动")
    purchase_date = Column(Date, comment="购入日期")
    purchase_price = Column(Float, comment="购入价格")
    current_mileage = Column(Float, default=0, comment="当前里程(km)")
    notes = Column(Text, comment="备注")
    created_at = Column(DateTime, server_default=func.now())


class FuelRecord(Base):
    """加油记录"""
    __tablename__ = "fuel_records"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, nullable=False, index=True, comment="车辆ID")
    fuel_date = Column(DateTime, nullable=False, index=True, comment="加油日期时间")
    total_mileage = Column(Float, comment="总里程表(km)")
    unit_price = Column(Float, comment="单价(元/L)")
    fuel_amount = Column(Float, comment="加油量(L)")
    display_cost = Column(Float, comment="机显金额")
    actual_cost = Column(Float, comment="实付金额")
    fuel_grade = Column(String(20), comment="油号：92#/95#/98#")
    is_full = Column(Boolean, default=False, comment="是否加满")
    is_low_fuel = Column(Boolean, default=False, comment="是否亮灯")
    is_missed = Column(Boolean, default=False, comment="是否漏记")
    fuel_consumption = Column(Float, comment="油耗(L/100km)")
    trip_mileage = Column(Float, comment="行程(km)，两次加油间行驶里程")
    station_name = Column(String(200), comment="加油站名称")
    # 电动车专属字段
    energy_kwh = Column(Float, comment="充电量(kWh)")
    electricity_price = Column(Float, comment="电价(元/kWh)")
    electricity_consumption = Column(Float, comment="电耗(kWh/100km)")
    charge_type = Column(String(20), comment="充电方式：快充/慢充/家充")
    soc_start = Column(Integer, comment="充电前电量(%)")
    soc_end = Column(Integer, comment="充电后电量(%)")
    notes = Column(Text, comment="备注")
    created_at = Column(DateTime, server_default=func.now())


class VehicleExpense(Base):
    """车辆费用记录（保养/保险/维修等）"""
    __tablename__ = "vehicle_expenses"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, nullable=False, index=True, comment="车辆ID")
    expense_date = Column(DateTime, nullable=False, index=True, comment="费用日期时间")
    expense_type = Column(String(100), comment="费用类型：车辆保养/车辆保险/车辆维修/洗车打蜡等")
    amount = Column(Float, comment="金额(元)")
    mileage_at = Column(Float, comment="当时里程(km)")
    notes = Column(Text, comment="备注")
    created_at = Column(DateTime, server_default=func.now())
