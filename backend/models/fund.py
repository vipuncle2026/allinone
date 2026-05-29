"""基金管理数据模型"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class FundLibrary(Base):
    """基金基础信息库（预置 + 用户添加）"""
    __tablename__ = "fund_library"

    code = Column(String(10), primary_key=True, comment="基金代码")
    name = Column(String(100), nullable=False, comment="基金名称")
    type = Column(String(20), default="混合型", comment="类型：股票型/混合型/债券型/指数型/商品型/跨境型")
    is_etf = Column(Boolean, default=False, comment="是否场内ETF")
    manager = Column(String(50), default="--", comment="基金经理")
    company = Column(String(100), default="--", comment="基金公司")
    scale = Column(Float, default=0, comment="基金规模(亿)")


class FundFavorite(Base):
    """自选基金"""
    __tablename__ = "fund_favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, comment="基金代码")
    name = Column(String(100), nullable=False, comment="基金名称")
    type = Column(String(20), default="混合型", comment="类型")
    is_etf = Column(Boolean, default=False, comment="是否场内ETF")
    group_id = Column(String(50), default="default", comment="分组ID")

    # 净值数据（每次刷新更新）
    nav = Column(Float, default=0, comment="单位净值（上一交易日）")
    prev_nav = Column(Float, default=0, comment="前一日净值（用于计算昨日收益）")
    est_nav = Column(Float, default=0, comment="估算净值")
    nav_date = Column(String(20), default="", comment="净值日期")
    day_chg = Column(Float, default=0, comment="今日估算涨跌幅%")
    val_time = Column(String(30), default="", comment="估值时间")
    no_estimate = Column(Boolean, default=False, comment="是否无估算数据")

    # 持仓数据
    shares = Column(Float, default=0, comment="持仓份额")
    cost_nav = Column(Float, default=0, comment="成本净值")

    # 基金经理/公司/规模（从基础库获取）
    manager = Column(String(50), default="--")
    company = Column(String(100), default="--")
    scale = Column(Float, default=0)

    # 近期收益
    ret_1m = Column(Float, default=0, comment="近1月收益率%")
    ret_3m = Column(Float, default=0, comment="近3月收益率%")
    ret_6m = Column(Float, default=0, comment="近6月收益率%")
    ret_1y = Column(Float, default=0, comment="近1年收益率%")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundGroup(Base):
    """基金分组"""
    __tablename__ = "fund_groups"

    id = Column(String(50), primary_key=True, comment="分组ID")
    name = Column(String(50), nullable=False, comment="分组名称")
    color = Column(String(10), default="#6b7280", comment="显示颜色")
    sort_order = Column(Integer, default=0, comment="排序序号")
    is_default = Column(Boolean, default=False, comment="是否默认分组")


class FundSnapshot(Base):
    """基金持仓每日快照（汇总）"""
    __tablename__ = "fund_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(String(10), unique=True, nullable=False, comment="快照日期 YYYY-MM-DD")
    total_market = Column(Float, default=0, comment="总市值")
    total_cost = Column(Float, default=0, comment="总成本")
    total_gain = Column(Float, default=0, comment="累计收益")
    total_rate = Column(Float, default=0, comment="总收益率%")
    today_profit = Column(Float, default=0, comment="当日收益")
    created_at = Column(DateTime, default=datetime.now)


class FundSnapshotItem(Base):
    """基金持仓每日快照（单只明细）"""
    __tablename__ = "fund_snapshot_items"
    __table_args__ = (
        Index("ix_snap_date_code", "snapshot_date", "code", unique=True),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(String(10), nullable=False, comment="快照日期")
    code = Column(String(10), nullable=False, comment="基金代码")
    name = Column(String(100), default="", comment="基金名称")
    nav = Column(Float, default=0, comment="当日净值")
    shares = Column(Float, default=0, comment="持仓份额")
    market_value = Column(Float, default=0, comment="市值")
    day_chg = Column(Float, default=0, comment="涨跌幅%")
    today_gain = Column(Float, default=0, comment="当日收益")
