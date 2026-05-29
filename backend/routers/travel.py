"""旅行管理路由"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date as date_type
from io import StringIO, BytesIO
import csv
import re
import json
from urllib.parse import quote

from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models.travel import (
    TravelTrip, TravelExpense, TravelMileage,
    EXPENSE_CATEGORIES, TRANSPORT_TYPES,
)

router = APIRouter(prefix="/api/travel", tags=["旅行管理"])


# ─── Pydantic Schemas ─────────────────────────────────────────

class TripCreate(BaseModel):
    name: str
    destination: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: float = 0
    currency: str = "¥"
    planned_km: float = 0

class TripUpdate(BaseModel):
    name: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = None
    currency: Optional[str] = None
    planned_km: Optional[float] = None

class ExpenseCreate(BaseModel):
    trip_id: int
    date: str
    category: str
    amount: float
    note: str = ""

class ExpenseUpdate(BaseModel):
    date: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    note: Optional[str] = None

class MileageCreate(BaseModel):
    trip_id: int
    date: str
    transport: str
    km: float
    from_place: str = ""
    to_place: str = ""
    note: str = ""

class MileageUpdate(BaseModel):
    date: Optional[str] = None
    transport: Optional[str] = None
    km: Optional[float] = None
    from_place: Optional[str] = None
    to_place: Optional[str] = None
    note: Optional[str] = None


# ─── 配置 ─────────────────────────────────────────

@router.get("/config")
def get_config():
    """获取分类和交通方式配置"""
    return {
        "expense_categories": EXPENSE_CATEGORIES,
        "transport_types": TRANSPORT_TYPES,
    }


@router.get("/category-stats")
def get_category_stats(db: Session = Depends(get_db)):
    """获取全局支出分类统计（用于 Dashboard 展示最大支出项）"""
    rows = db.query(
        TravelExpense.category,
        func.sum(TravelExpense.amount).label("total")
    ).group_by(TravelExpense.category).order_by(func.sum(TravelExpense.amount).desc()).all()

    result = []
    for cat, total in rows:
        info = EXPENSE_CATEGORIES.get(cat, {})
        result.append({
            "category": cat,
            "total": round(total, 2),
            "icon": info.get("icon", "📌"),
            "color": info.get("color", "#6B7280"),
        })
    return result


@router.get("/yearly-stats")
def get_yearly_stats(db: Session = Depends(get_db)):
    """按年统计旅行数据（次数、支出、里程、天数、分类明细）"""
    from sqlalchemy import func, extract

    trips = db.query(TravelTrip).all()
    all_expenses = db.query(TravelExpense).all()
    all_mileages = db.query(TravelMileage).all()

    # 按旅行分组支出和里程
    expense_map = {}
    for e in all_expenses:
        expense_map.setdefault(e.trip_id, []).append(e)

    mileage_map = {}
    for m in all_mileages:
        mileage_map.setdefault(m.trip_id, []).append(m)

    # 按年汇总
    yearly = {}
    for trip in trips:
        year = trip.start_date.year if trip.start_date else None
        if not year:
            continue

        expenses = expense_map.get(trip.id, [])
        mileages = mileage_map.get(trip.id, [])

        total_expense = sum(e.amount for e in expenses)
        total_km = sum(m.km for m in mileages)

        # 计算旅行天数
        days = 1
        if trip.start_date and trip.end_date:
            days = max(1, (trip.end_date - trip.start_date).days + 1)

        # 分类支出明细
        cat_map = {}
        for e in expenses:
            cat_map[e.category] = cat_map.get(e.category, 0) + e.amount

        # 交通方式里程明细
        transport_map = {}
        for m in mileages:
            transport_map[m.transport] = transport_map.get(m.transport, 0) + m.km

        if year not in yearly:
            yearly[year] = {
                "year": year,
                "trip_count": 0,
                "total_expense": 0,
                "total_km": 0,
                "total_days": 0,
                "trips": [],
                "category_breakdown": {},
                "transport_breakdown": {},
            }

        yearly[year]["trip_count"] += 1
        yearly[year]["total_expense"] += total_expense
        yearly[year]["total_km"] += total_km
        yearly[year]["total_days"] += days
        yearly[year]["trips"].append({
            "id": trip.id,
            "name": trip.name,
            "destination": trip.destination,
            "start_date": str(trip.start_date) if trip.start_date else None,
            "end_date": str(trip.end_date) if trip.end_date else None,
            "days": days,
            "total_expense": round(total_expense, 2),
            "total_km": round(total_km, 1),
            "budget": trip.budget or 0,
        })

        for cat, amt in cat_map.items():
            yearly[year]["category_breakdown"][cat] = yearly[year]["category_breakdown"].get(cat, 0) + amt

        for tp, km in transport_map.items():
            yearly[year]["transport_breakdown"][tp] = yearly[year]["transport_breakdown"].get(tp, 0) + km

    # 格式化输出
    result = []
    for year in sorted(yearly.keys(), reverse=True):
        yd = yearly[year]
        result.append({
            "year": yd["year"],
            "trip_count": yd["trip_count"],
            "total_expense": round(yd["total_expense"], 2),
            "total_km": round(yd["total_km"], 1),
            "total_days": yd["total_days"],
            "avg_expense_per_trip": round(yd["total_expense"] / yd["trip_count"], 2) if yd["trip_count"] > 0 else 0,
            "avg_expense_per_day": round(yd["total_expense"] / yd["total_days"], 2) if yd["total_days"] > 0 else 0,
            "trips": yd["trips"],
            "category_breakdown": {k: round(v, 2) for k, v in yd["category_breakdown"].items()},
            "transport_breakdown": {k: round(v, 1) for k, v in yd["transport_breakdown"].items()},
        })

    return result

@router.get("/trips")
def list_trips(db: Session = Depends(get_db)):
    """获取所有旅行（按开始日期降序）"""
    trips = db.query(TravelTrip).order_by(
        TravelTrip.start_date.desc().nullslast(),
        TravelTrip.id.desc()
    ).all()
    result = []
    for t in trips:
        # 统计该旅行的支出总额和里程总额
        total_expense = db.query(func.sum(TravelExpense.amount)).filter(
            TravelExpense.trip_id == t.id
        ).scalar() or 0
        total_km = db.query(func.sum(TravelMileage.km)).filter(
            TravelMileage.trip_id == t.id
        ).scalar() or 0
        expense_count = db.query(func.count(TravelExpense.id)).filter(
            TravelExpense.trip_id == t.id
        ).scalar() or 0

        result.append({
            "id": t.id,
            "name": t.name,
            "destination": t.destination,
            "start_date": t.start_date.isoformat() if t.start_date else "",
            "end_date": t.end_date.isoformat() if t.end_date else "",
            "budget": t.budget,
            "currency": t.currency,
            "planned_km": t.planned_km,
            "total_expense": round(total_expense, 2),
            "total_km": round(total_km, 1),
            "expense_count": expense_count,
            "created_at": t.created_at.isoformat() if t.created_at else "",
        })
    return result


@router.get("/trips/{trip_id}")
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    """获取单个旅行详情"""
    trip = db.query(TravelTrip).filter(TravelTrip.id == trip_id).first()
    if not trip:
        raise HTTPException(404, "旅行不存在")
    total_expense = db.query(func.sum(TravelExpense.amount)).filter(
        TravelExpense.trip_id == trip.id
    ).scalar() or 0
    total_km = db.query(func.sum(TravelMileage.km)).filter(
        TravelMileage.trip_id == trip.id
    ).scalar() or 0
    return {
        "id": trip.id,
        "name": trip.name,
        "destination": trip.destination,
        "start_date": trip.start_date.isoformat() if trip.start_date else "",
        "end_date": trip.end_date.isoformat() if trip.end_date else "",
        "budget": trip.budget,
        "currency": trip.currency,
        "planned_km": trip.planned_km,
        "total_expense": round(total_expense, 2),
        "total_km": round(total_km, 1),
        "created_at": trip.created_at.isoformat() if trip.created_at else "",
    }


def _parse_date(s):
    """将日期字符串 'YYYY-MM-DD' 转为 Python date 对象"""
    if not s:
        return None
    if isinstance(s, date_type):
        return s
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@router.post("/trips")
def create_trip(data: TripCreate, db: Session = Depends(get_db)):
    """新增旅行"""
    trip = TravelTrip(
        name=data.name,
        destination=data.destination,
        start_date=_parse_date(data.start_date),
        end_date=_parse_date(data.end_date),
        budget=data.budget,
        currency=data.currency,
        planned_km=data.planned_km,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return {"id": trip.id, "message": "旅行创建成功"}


@router.put("/trips/{trip_id}")
def update_trip(trip_id: int, data: TripUpdate, db: Session = Depends(get_db)):
    """更新旅行"""
    trip = db.query(TravelTrip).filter(TravelTrip.id == trip_id).first()
    if not trip:
        return {"error": "旅行不存在"}, 404
    for field, value in data.model_dump(exclude_unset=True).items():
        if field in ("start_date", "end_date"):
            value = _parse_date(value)
        setattr(trip, field, value)
    trip.updated_at = datetime.now()
    db.commit()
    return {"message": "更新成功"}


@router.delete("/trips/{trip_id}")
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    """删除旅行（级联删除支出和里程）"""
    trip = db.query(TravelTrip).filter(TravelTrip.id == trip_id).first()
    if not trip:
        return {"error": "旅行不存在"}, 404
    db.query(TravelExpense).filter(TravelExpense.trip_id == trip_id).delete()
    db.query(TravelMileage).filter(TravelMileage.trip_id == trip_id).delete()
    db.delete(trip)
    db.commit()
    return {"message": "删除成功"}


# ═══════════════════════════════════════════════════════════
#  支出 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/trips/{trip_id}/expenses")
def list_expenses(
    trip_id: int,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取旅行支出列表"""
    query = db.query(TravelExpense).filter(TravelExpense.trip_id == trip_id)
    if keyword:
        query = query.filter(TravelExpense.note.contains(keyword))
    expenses = query.order_by(TravelExpense.date.desc(), TravelExpense.id.desc()).all()
    return [
        {
            "id": e.id,
            "trip_id": e.trip_id,
            "date": e.date,
            "category": e.category,
            "amount": e.amount,
            "note": e.note,
            "category_icon": EXPENSE_CATEGORIES.get(e.category, {}).get("icon", "📌"),
            "category_color": EXPENSE_CATEGORIES.get(e.category, {}).get("color", "#6B7280"),
        }
        for e in expenses
    ]


@router.post("/expenses")
def create_expense(data: ExpenseCreate, db: Session = Depends(get_db)):
    """新增支出"""
    expense = TravelExpense(
        trip_id=data.trip_id,
        date=data.date,
        category=data.category,
        amount=data.amount,
        note=data.note,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return {"id": expense.id, "message": "支出创建成功"}


@router.put("/expenses/{expense_id}")
def update_expense(expense_id: int, data: ExpenseUpdate, db: Session = Depends(get_db)):
    """更新支出"""
    expense = db.query(TravelExpense).filter(TravelExpense.id == expense_id).first()
    if not expense:
        return {"error": "记录不存在"}, 404
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    """删除支出"""
    expense = db.query(TravelExpense).filter(TravelExpense.id == expense_id).first()
    if not expense:
        return {"error": "记录不存在"}, 404
    db.delete(expense)
    db.commit()
    return {"message": "删除成功"}


# ═══════════════════════════════════════════════════════════
#  里程 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/trips/{trip_id}/mileages")
def list_mileages(trip_id: int, db: Session = Depends(get_db)):
    """获取旅行里程列表"""
    mileages = db.query(TravelMileage).filter(
        TravelMileage.trip_id == trip_id
    ).order_by(TravelMileage.date.desc(), TravelMileage.id.desc()).all()
    return [
        {
            "id": m.id,
            "trip_id": m.trip_id,
            "date": m.date,
            "transport": m.transport,
            "km": m.km,
            "from_place": m.from_place,
            "to_place": m.to_place,
            "note": m.note,
            "transport_icon": TRANSPORT_TYPES.get(m.transport, {}).get("icon", "📍"),
            "transport_color": TRANSPORT_TYPES.get(m.transport, {}).get("color", "#6B7280"),
        }
        for m in mileages
    ]


@router.post("/mileages")
def create_mileage(data: MileageCreate, db: Session = Depends(get_db)):
    """新增里程"""
    mileage = TravelMileage(
        trip_id=data.trip_id,
        date=data.date,
        transport=data.transport,
        km=data.km,
        from_place=data.from_place,
        to_place=data.to_place,
        note=data.note,
    )
    db.add(mileage)
    db.commit()
    db.refresh(mileage)
    return {"id": mileage.id, "message": "里程创建成功"}


@router.put("/mileages/{mileage_id}")
def update_mileage(mileage_id: int, data: MileageUpdate, db: Session = Depends(get_db)):
    """更新里程"""
    mileage = db.query(TravelMileage).filter(TravelMileage.id == mileage_id).first()
    if not mileage:
        return {"error": "记录不存在"}, 404
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(mileage, field, value)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/mileages/{mileage_id}")
def delete_mileage(mileage_id: int, db: Session = Depends(get_db)):
    """删除里程"""
    mileage = db.query(TravelMileage).filter(TravelMileage.id == mileage_id).first()
    if not mileage:
        return {"error": "记录不存在"}, 404
    db.delete(mileage)
    db.commit()
    return {"message": "删除成功"}


# ═══════════════════════════════════════════════════════════
#  统计分析
# ═══════════════════════════════════════════════════════════

@router.get("/trips/{trip_id}/stats")
def get_trip_stats(trip_id: int, db: Session = Depends(get_db)):
    """获取旅行统计数据"""
    trip = db.query(TravelTrip).filter(TravelTrip.id == trip_id).first()
    if not trip:
        return {"error": "旅行不存在"}, 404

    expenses = db.query(TravelExpense).filter(TravelExpense.trip_id == trip_id).all()
    mileages = db.query(TravelMileage).filter(TravelMileage.trip_id == trip_id).all()

    total_expense = sum(e.amount for e in expenses)
    expense_count = len(expenses)
    avg_expense = total_expense / expense_count if expense_count > 0 else 0
    total_km = sum(m.km for m in mileages)

    # 分类统计
    category_stats = {}
    for e in expenses:
        cat = e.category
        category_stats[cat] = category_stats.get(cat, 0) + e.amount

    # 每日支出趋势
    daily_stats = {}
    for e in expenses:
        day = e.date[:10] if e.date else ""
        daily_stats[day] = daily_stats.get(day, 0) + e.amount

    daily_trend = [
        {"date": d, "amount": round(a, 2)}
        for d, a in sorted(daily_stats.items())
    ]

    # 分类占比
    category_breakdown = [
        {
            "category": cat,
            "amount": round(amt, 2),
            "percent": round(amt / total_expense * 100, 1) if total_expense > 0 else 0,
            "icon": EXPENSE_CATEGORIES.get(cat, {}).get("icon", "📌"),
            "color": EXPENSE_CATEGORIES.get(cat, {}).get("color", "#6B7280"),
        }
        for cat, amt in sorted(category_stats.items(), key=lambda x: -x[1])
    ]

    return {
        "total_expense": round(total_expense, 2),
        "expense_count": expense_count,
        "avg_expense": round(avg_expense, 2),
        "total_km": round(total_km, 1),
        "budget": trip.budget,
        "budget_used_percent": round(total_expense / trip.budget * 100, 1) if trip.budget > 0 else 0,
        "planned_km": trip.planned_km,
        "km_completed_percent": round(total_km / trip.planned_km * 100, 1) if trip.planned_km > 0 else 0,
        "currency": trip.currency,
        "category_breakdown": category_breakdown,
        "daily_trend": daily_trend,
    }


# ═══════════════════════════════════════════════════════════
#  CSV 导出 / 导入
# ═══════════════════════════════════════════════════════════

@router.get("/trips/{trip_id}/export/csv")
def export_csv(trip_id: int, db: Session = Depends(get_db)):
    """导出旅行数据为 CSV（支出+里程）"""
    # (使用 StreamingResponse，无需额外导入)

    trip = db.query(TravelTrip).filter(TravelTrip.id == trip_id).first()
    if not trip:
        return {"error": "旅行不存在"}, 404

    expenses = db.query(TravelExpense).filter(
        TravelExpense.trip_id == trip_id
    ).order_by(TravelExpense.date).all()

    mileages = db.query(TravelMileage).filter(
        TravelMileage.trip_id == trip_id
    ).order_by(TravelMileage.date).all()

    output = StringIO()
    output.write("\ufeff")  # BOM for Excel
    writer = csv.writer(output)

    # 支出
    writer.writerow(["日期", "分类", "金额", "备注"])
    for e in expenses:
        writer.writerow([e.date, e.category, e.amount, e.note or ""])

    # 里程
    if mileages:
        writer.writerow([])
        writer.writerow(["日期", "交通方式", "里程(km)", "出发地", "目的地", "备注"])
        for m in mileages:
            writer.writerow([m.date, m.transport, m.km, m.from_place or "", m.to_place or "", m.note or ""])

    return StreamingResponse(
        BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(trip.name + '_记录.csv')}"
        },
    )


@router.post("/trips/{trip_id}/import/csv")
def import_csv(trip_id: int, data: dict, db: Session = Depends(get_db)):
    """导入 CSV 数据（自动识别支出/里程格式）"""
    trip = db.query(TravelTrip).filter(TravelTrip.id == trip_id).first()
    if not trip:
        return {"error": "旅行不存在"}, 404

    csv_content = data.get("csv", "")
    if not csv_content.strip():
        return {"error": "CSV 内容为空"}

    lines = csv_content.strip().split("\n")
    if len(lines) < 2:
        return {"error": "CSV 内容不足"}

    imported = {"expenses": 0, "mileages": 0}

    # 逐行解析
    expense_lines = []
    mileage_lines = []
    current_section = None  # 'expense' or 'mileage'

    for line in lines:
        line = line.strip()
        if not line:
            continue

        header = line.lower()
        if "分类" in header and "金额" in header:
            current_section = "expense"
            continue
        if "交通方式" in header and "里程" in header:
            current_section = "mileage"
            continue

        if current_section == "expense":
            expense_lines.append(line)
        elif current_section == "mileage":
            mileage_lines.append(line)

    # 解析支出
    for line in expense_lines:
        parts = _parse_csv_line(line)
        if len(parts) >= 3:
            date_str = parts[0].strip().strip('"')
            category = parts[1].strip().strip('"')
            amount_str = parts[2].strip().strip('"')
            note = parts[3].strip().strip('"') if len(parts) > 3 else ""

            try:
                amount = float(amount_str)
                if amount > 0:
                    expense = TravelExpense(
                        trip_id=trip_id,
                        date=date_str,
                        category=category,
                        amount=amount,
                        note=note,
                    )
                    db.add(expense)
                    imported["expenses"] += 1
            except (ValueError, TypeError):
                continue

    # 解析里程
    for line in mileage_lines:
        parts = _parse_csv_line(line)
        if len(parts) >= 3:
            date_str = parts[0].strip().strip('"')
            transport = parts[1].strip().strip('"')
            km_str = parts[2].strip().strip('"')
            from_place = parts[3].strip().strip('"') if len(parts) > 3 else ""
            to_place = parts[4].strip().strip('"') if len(parts) > 4 else ""
            note = parts[5].strip().strip('"') if len(parts) > 5 else ""

            try:
                km = float(km_str)
                if km > 0:
                    mileage = TravelMileage(
                        trip_id=trip_id,
                        date=date_str,
                        transport=transport,
                        km=km,
                        from_place=from_place,
                        to_place=to_place,
                        note=note,
                    )
                    db.add(mileage)
                    imported["mileages"] += 1
            except (ValueError, TypeError):
                continue

    db.commit()
    total = imported["expenses"] + imported["mileages"]
    return {
        "message": f"成功导入 {total} 条记录（支出 {imported['expenses']}，里程 {imported['mileages']}）",
        "imported": imported,
    }


def _parse_csv_line(line: str) -> list:
    """简单解析 CSV 行，支持引号内的逗号"""
    result = []
    current = ""
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ',' and not in_quotes:
            result.append(current)
            current = ""
        else:
            current += ch
    result.append(current)
    return result


# ═══════════════════════════════════════════════════════════
#  JSON 导出 / 导入（旅行级别）
# ═══════════════════════════════════════════════════════════

@router.get("/trips/{trip_id}/export/json")
def export_trip_json(trip_id: int, db: Session = Depends(get_db)):
    """导出单个旅行的完整数据（JSON）"""
    trip = db.query(TravelTrip).filter(TravelTrip.id == trip_id).first()
    if not trip:
        return {"error": "旅行不存在"}, 404

    expenses = db.query(TravelExpense).filter(
        TravelExpense.trip_id == trip_id
    ).order_by(TravelExpense.date, TravelExpense.id).all()

    mileages = db.query(TravelMileage).filter(
        TravelMileage.trip_id == trip_id
    ).order_by(TravelMileage.date, TravelMileage.id).all()

    data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "trip": {
            "name": trip.name,
            "destination": trip.destination,
            "start_date": trip.start_date.isoformat() if trip.start_date else "",
            "end_date": trip.end_date.isoformat() if trip.end_date else "",
            "budget": trip.budget,
            "currency": trip.currency,
            "planned_km": trip.planned_km,
        },
        "expenses": [
            {
                "date": e.date,
                "category": e.category,
                "amount": e.amount,
                "note": e.note,
            }
            for e in expenses
        ],
        "mileages": [
            {
                "date": m.date,
                "transport": m.transport,
                "km": m.km,
                "from_place": m.from_place,
                "to_place": m.to_place,
                "note": m.note,
            }
            for m in mileages
        ],
    }

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(trip.name)}.json"
        },
    )


@router.get("/export-all/json")
def export_all_trips_json(db: Session = Depends(get_db)):
    """导出所有旅行的完整数据（JSON）"""
    trips = db.query(TravelTrip).order_by(
        TravelTrip.start_date.desc().nullslast(),
        TravelTrip.id.desc()
    ).all()

    trips_data = []
    for trip in trips:
        expenses = db.query(TravelExpense).filter(
            TravelExpense.trip_id == trip.id
        ).order_by(TravelExpense.date, TravelExpense.id).all()

        mileages = db.query(TravelMileage).filter(
            TravelMileage.trip_id == trip.id
        ).order_by(TravelMileage.date, TravelMileage.id).all()

        trips_data.append({
            "name": trip.name,
            "destination": trip.destination,
            "start_date": trip.start_date.isoformat() if trip.start_date else "",
            "end_date": trip.end_date.isoformat() if trip.end_date else "",
            "budget": trip.budget,
            "currency": trip.currency,
            "planned_km": trip.planned_km,
            "expenses": [
                {
                    "date": e.date,
                    "category": e.category,
                    "amount": e.amount,
                    "note": e.note,
                }
                for e in expenses
            ],
            "mileages": [
                {
                    "date": m.date,
                    "transport": m.transport,
                    "km": m.km,
                    "from_place": m.from_place,
                    "to_place": m.to_place,
                    "note": m.note,
                }
                for m in mileages
            ],
        })

    data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "trips": trips_data,
    }

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote('全部旅行.json')}"
        },
    )


@router.post("/import/json")
def import_trip_json(data: dict, db: Session = Depends(get_db)):
    """导入旅行数据（JSON，支持单个或多个旅行）"""
    imported_trips = []

    # 兼容单旅行格式（顶层有 "trip" 字段）和多旅行格式（顶层有 "trips" 数组）
    if "trip" in data:
        trips_to_import = [data["trip"]]
    elif "trips" in data:
        trips_to_import = data["trips"]
    else:
        return {"error": "JSON 格式不正确，缺少 trip 或 trips 字段"}

    for trip_data in trips_to_import:
        # 创建旅行
        trip = TravelTrip(
            name=trip_data.get("name", "未命名旅行"),
            destination=trip_data.get("destination", ""),
            start_date=_parse_date(trip_data.get("start_date")),
            end_date=_parse_date(trip_data.get("end_date")),
            budget=trip_data.get("budget", 0),
            currency=trip_data.get("currency", "¥"),
            planned_km=trip_data.get("planned_km", 0),
        )
        db.add(trip)
        db.flush()  # 获取 id

        expense_count = 0
        mileage_count = 0

        # 导入支出
        for e in trip_data.get("expenses", []):
            if not e.get("amount"):
                continue
            expense = TravelExpense(
                trip_id=trip.id,
                date=e.get("date", ""),
                category=e.get("category", "其他"),
                amount=float(e.get("amount", 0)),
                note=e.get("note", ""),
            )
            db.add(expense)
            expense_count += 1

        # 导入里程
        for m in trip_data.get("mileages", []):
            if not m.get("km"):
                continue
            mileage = TravelMileage(
                trip_id=trip.id,
                date=m.get("date", ""),
                transport=m.get("transport", "其他"),
                km=float(m.get("km", 0)),
                from_place=m.get("from_place", ""),
                to_place=m.get("to_place", ""),
                note=m.get("note", ""),
            )
            db.add(mileage)
            mileage_count += 1

        imported_trips.append({
            "name": trip.name,
            "expenses": expense_count,
            "mileages": mileage_count,
        })

    db.commit()

    total_trips = len(imported_trips)
    total_expenses = sum(t["expenses"] for t in imported_trips)
    total_mileages = sum(t["mileages"] for t in imported_trips)
    return {
        "message": f"成功导入 {total_trips} 个旅行（支出 {total_expenses} 条，里程 {total_mileages} 条）",
        "imported": imported_trips,
    }
