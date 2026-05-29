"""Dashboard 模块 API —— 跨模块时间线"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

logger = logging.getLogger("dashboard")

from database import get_db
from routers.auth import verify_token
from models.cycling import CyclingActivity
from models.hiking import HikingActivity
from models.running import RunningActivity
from models.travel import TravelTrip, TravelExpense
from models.finance import FinanceTransaction
from models.item import Item
from models.vehicle import FuelRecord, VehicleExpense

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/timeline")
def get_timeline(limit: int = 20, db: Session = Depends(get_db)):
    """获取跨模块近期动态时间线（骑行/徒步/旅行/收支）"""
    events = []

    # ── 骑行活动 ──────────────────────────────────────────
    try:
        acts = (
            db.query(CyclingActivity)
            .order_by(CyclingActivity.date.desc())
            .limit(8)
            .all()
        )
        for a in acts:
            events.append({
                "type": "cycling",
                "icon": "🚴",
                "color": "#0ea5e9",
                "tag": "骑行",
                "title": a.title or "骑行活动",
                "date": str(a.date),
                "meta": _build_cycling_meta(a),
                "link": f"/sports/cycling/{a.id}",
            })
    except Exception as e:
        logger.warning("[dashboard] 骑行数据加载失败: %s", e, exc_info=True)

    # ── 徒步活动 ──────────────────────────────────────────
    try:
        hikes = (
            db.query(HikingActivity)
            .order_by(HikingActivity.date.desc())
            .limit(6)
            .all()
        )
        for h in hikes:
            events.append({
                "type": "hiking",
                "icon": "🥾",
                "color": "#10b981",
                "tag": "徒步",
                "title": h.title or "徒步活动",
                "date": str(h.date),
                "meta": _build_hiking_meta(h),
                "link": f"/sports/hiking/detail/{h.id}",
            })
    except Exception as e:
        logger.warning("[dashboard] 徒步数据加载失败: %s", e, exc_info=True)

    # ── 跑步活动 ──────────────────────────────────────────
    try:
        runs = (
            db.query(RunningActivity)
            .order_by(RunningActivity.date.desc())
            .limit(6)
            .all()
        )
        for r in runs:
            events.append({
                "type": "running",
                "icon": "🏃",
                "color": "#f97316",
                "tag": "跑步",
                "title": r.title or "跑步活动",
                "date": str(r.date),
                "meta": _build_running_meta(r),
                "link": f"/sports/running/{r.id}",
            })
    except Exception as e:
        logger.warning("[dashboard] 跑步数据加载失败: %s", e, exc_info=True)

    # ── 旅行（最近出发/回来） ────────────────────────────
    try:
        trips = (
            db.query(TravelTrip)
            .order_by(TravelTrip.start_date.desc())
            .limit(5)
            .all()
        )
        for t in trips:
            if not t.start_date:
                continue
            # 查旅行支出总额
            total_exp = (
                db.query(TravelExpense)
                .filter(TravelExpense.trip_id == t.id)
                .all()
            )
            total_amount = sum(e.amount or 0 for e in total_exp)
            events.append({
                "type": "travel",
                "icon": "✈️",
                "color": "#8b5cf6",
                "tag": "旅行",
                "title": t.name,
                "date": str(t.start_date),
                "meta": _build_travel_meta(t, total_amount),
                "link": f"/travel",
            })
    except Exception as e:
        logger.warning("[dashboard] 旅行数据加载失败: %s", e, exc_info=True)

    # ── 财务大额收支（≥500 元） ───────────────────────────
    try:
        txns = (
            db.query(FinanceTransaction)
            .filter(FinanceTransaction.amount >= 500)
            .order_by(FinanceTransaction.date.desc())
            .limit(8)
            .all()
        )
        for tx in txns:
            events.append({
                "type": "finance",
                "icon": "💰" if tx.type == "income" else "💸",
                "color": "#e63946" if tx.type == "income" else "#16a34a",
                "tag": "收入" if tx.type == "income" else "支出",
                "title": tx.description or tx.category,
                "date": tx.date,
                "meta": _build_finance_meta(tx),
                "link": "/finance",
            })
    except Exception as e:
        logger.warning("[dashboard] 财务数据加载失败: %s", e, exc_info=True)

    # ── 物品（最近添加/更新） ──────────────────────────
    try:
        items = (
            db.query(Item)
            .order_by(Item.updated_at.desc())
            .limit(5)
            .all()
        )
        for it in items:
            from models.item import ITEM_CATEGORIES
            cat_icon = ITEM_CATEGORIES.get(it.category, {}).get("icon", "📦")
            events.append({
                "type": "item",
                "icon": cat_icon,
                "color": "#475569",
                "tag": "物品",
                "title": it.name,
                "date": it.updated_at or it.created_at,
                "meta": _build_item_meta(it),
                "link": "/item",
            })
    except Exception as e:
        logger.warning("[dashboard] 物品数据加载失败: %s", e, exc_info=True)

    # ── 车辆加油 / 充电 ────────────────────────────────
    try:
        fuels = (
            db.query(FuelRecord)
            .order_by(FuelRecord.fuel_date.desc())
            .limit(5)
            .all()
        )
        for f in fuels:
            if not f.fuel_date:
                continue
            is_charge = (f.energy_kwh is not None and f.energy_kwh > 0)
            events.append({
                "type": "vehicle",
                "icon": "⚡" if is_charge else "⛽",
                "color": "#f59e0b",
                "tag": "充电" if is_charge else "加油",
                "title": f"{'充电' if is_charge else '加油'} ¥{(f.actual_cost or f.display_cost or 0):.1f}",
                "date": str(f.fuel_date.date() if hasattr(f.fuel_date, 'date') else f.fuel_date),
                "meta": _build_fuel_meta(f, is_charge),
                "link": "/vehicle",
            })
    except Exception as e:
        logger.warning("[dashboard] 车辆加油/充电数据加载失败: %s", e, exc_info=True)

    # ── 车辆费用（按类型区分图标与标签） ─────────────
    try:
        vexps = (
            db.query(VehicleExpense)
            .order_by(VehicleExpense.expense_date.desc())
            .limit(5)
            .all()
        )
        # 费用类型 → (图标, 标签) 映射
        _VE_TYPE_MAP = {
            "停车费": ("🅿️", "停车费"),
            "过路费": ("🛣️", "过路费"),
            "违章处理": ("📝", "违章处理"),
            "车辆保险": ("🛡️", "车辆保险"),
            "车辆保养": ("🔧", "车辆保养"),
            "维修保养": ("🔧", "维修保养"),
            "车辆维修": ("🔧", "车辆维修"),
            "洗车打蜡": ("🚿", "洗车打蜡"),
            "内外车品": ("🛒", "内外车品"),
        }
        for ve in vexps:
            if not ve.expense_date:
                continue
            etype = (ve.expense_type or "").strip()
            icon, tag = _VE_TYPE_MAP.get(etype, ("💳", etype or "车辆费用"))
            events.append({
                "type": "vehicle",
                "icon": icon,
                "color": "#f59e0b",
                "tag": tag,
                "title": ve.notes or etype or "车辆费用",
                "date": str(ve.expense_date.date() if hasattr(ve.expense_date, 'date') else ve.expense_date),
                "meta": _build_vehicle_expense_meta(ve),
                "link": "/vehicle",
            })
    except Exception as e:
        logger.warning("[dashboard] 车辆费用数据加载失败: %s", e, exc_info=True)

    # 按日期降序排序，取前 limit 条
    events.sort(key=lambda e: e.get("date") or "", reverse=True)
    return events[:limit]


# ── 内部辅助函数 ──────────────────────────────────────────────────

def _build_cycling_meta(a) -> str:
    parts = []
    if a.distance_km:
        parts.append(f"{a.distance_km:.1f} km")
    if a.duration_sec:
        h, m = divmod(a.duration_sec // 60, 60)
        parts.append(f"{h}h{m:02d}m" if h else f"{m}min")
    if a.avg_speed_kmh:
        parts.append(f"均速 {a.avg_speed_kmh:.1f} km/h")
    if a.elevation_gain:
        parts.append(f"爬升 {int(a.elevation_gain)}m")
    return " · ".join(parts)


def _build_hiking_meta(h) -> str:
    parts = []
    if h.distance_km:
        parts.append(f"{h.distance_km:.1f} km")
    if h.duration_sec:
        h_, m = divmod(h.duration_sec // 60, 60)
        parts.append(f"{h_}h{m:02d}m" if h_ else f"{m}min")
    if h.elevation_gain:
        parts.append(f"爬升 {int(h.elevation_gain)}m")
    return " · ".join(parts)


def _build_running_meta(r) -> str:
    parts = []
    if r.distance_km:
        parts.append(f"{r.distance_km:.1f} km")
    if r.duration_sec:
        m, s = divmod(r.duration_sec // 60, 60)
        parts.append(f"{m}m{s:02d}s")
    if r.pace_min_km:
        parts.append(f"配速 {r.pace_min_km:.2f} min/km")
    return " · ".join(parts)


def _build_travel_meta(t, total_amount: float) -> str:
    parts = []
    if t.destination:
        parts.append(t.destination)
    if t.end_date and t.start_date:
        try:
            delta = (t.end_date - t.start_date).days + 1
            parts.append(f"{delta} 天")
        except Exception as e:
            logger.debug("[dashboard] 旅行天数计算失败: %s", e)
    if total_amount > 0:
        parts.append(f"¥{total_amount:,.0f}")
    return " · ".join(parts)


def _build_finance_meta(tx) -> str:
    sign = "+" if tx.type == "income" else "-"
    return f"{tx.category}  {sign}¥{tx.amount:,.2f}"


def _build_item_meta(it) -> str:
    parts = []
    if it.category:
        parts.append(it.category)
    if it.purchase_price:
        parts.append(f"购入 ¥{it.purchase_price:,.2f}")
    if it.estimated_value:
        parts.append(f"估值 ¥{it.estimated_value:,.2f}")
    if it.brand:
        parts.append(it.brand)
    return " · ".join(parts)


def _build_fuel_meta(f, is_charge: bool) -> str:
    parts = []
    if is_charge:
        if f.energy_kwh:
            parts.append(f"{f.energy_kwh:.1f} kWh")
        if f.electricity_price:
            parts.append(f"¥{f.electricity_price:.3f}/kWh")
        if f.charge_type:
            parts.append(f.charge_type)
    else:
        if f.fuel_grade:
            parts.append(f.fuel_grade)
        if f.fuel_amount:
            parts.append(f"{f.fuel_amount:.1f} L")
        if f.unit_price:
            parts.append(f"¥{f.unit_price:.2f}/L")
    if f.total_mileage:
        parts.append(f"{f.total_mileage:,.0f} km")
    return " · ".join(parts)


def _build_vehicle_expense_meta(ve) -> str:
    parts = []
    if ve.expense_type:
        parts.append(ve.expense_type)
    if ve.amount:
        parts.append(f"¥{ve.amount:,.2f}")
    if ve.mileage_at:
        parts.append(f"{ve.mileage_at:,.0f} km")
    return " · ".join(parts)


@router.get("/activity-calendar")
def get_activity_calendar(year: int = None, db: Session = Depends(get_db)):
    """本年骑行+徒步+跑步按月统计（用于月历热力图）"""
    if not year:
        year = datetime.now().year

    months = []
    for m in range(1, 13):
        cycling_count = 0
        cycling_km = 0.0
        hiking_count = 0
        hiking_km = 0.0
        running_count = 0
        running_km = 0.0

        try:
            rides = (
                db.query(
                    func.count(CyclingActivity.id),
                    func.sum(CyclingActivity.distance_km),
                )
                .filter(
                    extract("year", CyclingActivity.date) == year,
                    extract("month", CyclingActivity.date) == m,
                )
                .one()
            )
            cycling_count = rides[0] or 0
            cycling_km = rides[1] or 0.0
        except Exception as e:
            logger.warning("[dashboard] 月历骑行统计失败 %d-%02d: %s", year, m, e)

        try:
            hikes = (
                db.query(
                    func.count(HikingActivity.id),
                    func.sum(HikingActivity.distance_km),
                )
                .filter(
                    extract("year", HikingActivity.date) == year,
                    extract("month", HikingActivity.date) == m,
                )
                .one()
            )
            hiking_count = hikes[0] or 0
            hiking_km = hikes[1] or 0.0
        except Exception as e:
            logger.warning("[dashboard] 月历徒步统计失败 %d-%02d: %s", year, m, e)

        try:
            runs = (
                db.query(
                    func.count(RunningActivity.id),
                    func.sum(RunningActivity.distance_km),
                )
                .filter(
                    extract("year", RunningActivity.date) == year,
                    extract("month", RunningActivity.date) == m,
                )
                .one()
            )
            running_count = runs[0] or 0
            running_km = runs[1] or 0.0
        except Exception as e:
            logger.warning("[dashboard] 月历跑步统计失败 %d-%02d: %s", year, m, e)

        total_count = cycling_count + hiking_count + running_count
        total_km = cycling_km + hiking_km + running_km
        months.append({
            "month": m,
            "cycling_count": cycling_count,
            "cycling_km": round(cycling_km, 1),
            "hiking_count": hiking_count,
            "hiking_km": round(hiking_km, 1),
            "running_count": running_count,
            "running_km": round(running_km, 1),
            "total_count": total_count,
            "total_km": round(total_km, 1),
        })

    return {"year": year, "months": months}


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """昨日 + 本周运动统计（骑行+徒步+跑步）"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    monday = today - timedelta(days=today.weekday())

    def _sum_cycling(start_date, end_date=None):
        q = db.query(
            func.count(CyclingActivity.id),
            func.sum(CyclingActivity.distance_km),
            func.sum(CyclingActivity.duration_sec),
            func.sum(CyclingActivity.elevation_gain),
        ).filter(CyclingActivity.date >= start_date)
        if end_date:
            q = q.filter(CyclingActivity.date <= end_date)
        row = q.first()
        return {
            "count": row[0] or 0,
            "km": round(row[1] or 0, 1),
            "hours": round((row[2] or 0) / 3600, 1),
            "gain": round(row[3] or 0, 0),
        }

    def _sum_hiking(start_date, end_date=None):
        q = db.query(
            func.count(HikingActivity.id),
            func.sum(HikingActivity.distance_km),
            func.sum(HikingActivity.duration_sec),
            func.sum(HikingActivity.elevation_gain),
        ).filter(HikingActivity.date >= start_date)
        if end_date:
            q = q.filter(HikingActivity.date <= end_date)
        row = q.first()
        return {
            "count": row[0] or 0,
            "km": round(row[1] or 0, 1),
            "hours": round((row[2] or 0) / 3600, 1),
            "gain": round(row[3] or 0, 0),
        }

    def _sum_running(start_date, end_date=None):
        q = db.query(
            func.count(RunningActivity.id),
            func.sum(RunningActivity.distance_km),
            func.sum(RunningActivity.duration_sec),
            func.sum(RunningActivity.calories),
        ).filter(RunningActivity.date >= start_date)
        if end_date:
            q = q.filter(RunningActivity.date <= end_date)
        row = q.first()
        return {
            "count": row[0] or 0,
            "km": round(row[1] or 0, 1),
            "hours": round((row[2] or 0) / 3600, 1),
            "calories": round(row[3] or 0, 0),
        }

    return {
        "today": {
            "date": str(yesterday),
            "cycling": _sum_cycling(yesterday, yesterday),
            "hiking": _sum_hiking(yesterday, yesterday),
            "running": _sum_running(yesterday, yesterday),
        },
        "week": {
            "start_date": str(monday),
            "end_date": str(today),
            "cycling": _sum_cycling(monday),
            "hiking": _sum_hiking(monday),
            "running": _sum_running(monday),
        },
    }
