"""全局搜索路由 - 跨模块搜索"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from routers.auth import verify_token

router = APIRouter(prefix="/api/search", tags=["全局搜索"])


@router.get("/")
def global_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="每类最多返回条数"),
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    """跨模块全局搜索"""
    keyword = f"%{q}%"
    results = []

    # 1. 旅行
    from models.travel import TravelTrip, TravelExpense, TravelMileage
    trips = db.query(TravelTrip).filter(
        or_(
            TravelTrip.name.ilike(keyword),
            TravelTrip.destination.ilike(keyword),
        )
    ).limit(limit).all()
    for t in trips:
        results.append({
            "module": "旅行", "icon": "✈️", "type": "旅行",
            "title": t.name,
            "subtitle": t.destination or "",
            "date": str(t.start_date) if t.start_date else "",
            "url": f"/travel/{t.id}",
        })

    # 旅行支出
    expenses = db.query(TravelExpense).filter(
        TravelExpense.note.ilike(keyword)
    ).limit(limit).all()
    for e in expenses:
        trip = db.query(TravelTrip).filter(TravelTrip.id == e.trip_id).first()
        results.append({
            "module": "旅行", "icon": "✈️", "type": "旅行支出",
            "title": e.note or e.category,
            "subtitle": f"{trip.name if trip else ''} · {e.category} · ¥{e.amount:,.0f}",
            "date": e.date,
            "url": f"/travel/{e.trip_id}",
        })

    # 旅行里程
    mileages = db.query(TravelMileage).filter(
        or_(
            TravelMileage.from_place.ilike(keyword),
            TravelMileage.to_place.ilike(keyword),
        )
    ).limit(limit).all()
    for m in mileages:
        trip = db.query(TravelTrip).filter(TravelTrip.id == m.trip_id).first()
        results.append({
            "module": "旅行", "icon": "✈️", "type": "旅行里程",
            "title": f"{m.from_place} → {m.to_place}",
            "subtitle": f"{trip.name if trip else ''} · {m.transport} · {m.km}km",
            "date": m.date,
            "url": f"/travel/{m.trip_id}",
        })

    # 2. 骑行
    from models.cycling import CyclingActivity
    rides = db.query(CyclingActivity).filter(
        or_(
            CyclingActivity.title.ilike(keyword),
            CyclingActivity.notes.ilike(keyword),
            CyclingActivity.route_type.ilike(keyword),
        )
    ).limit(limit).all()
    for r in rides:
        results.append({
            "module": "骑行", "icon": "🚴", "type": "骑行活动",
            "title": r.title,
            "subtitle": f"{r.distance_km:.1f}km" if r.distance_km else "",
            "date": str(r.date) if r.date else "",
            "url": "/cycling",
        })

    # 3. 徒步
    from models.hiking import HikingActivity
    hikes = db.query(HikingActivity).filter(
        or_(
            HikingActivity.title.ilike(keyword),
            HikingActivity.trail_name.ilike(keyword),
            HikingActivity.notes.ilike(keyword),
        )
    ).limit(limit).all()
    for h in hikes:
        results.append({
            "module": "徒步", "icon": "🥾", "type": "徒步活动",
            "title": h.title,
            "subtitle": h.trail_name or (f"{h.distance_km:.1f}km" if h.distance_km else ""),
            "date": str(h.date) if h.date else "",
            "url": "/hiking",
        })

    # 4. 财务收支
    from models.finance import FinanceTransaction
    txs = db.query(FinanceTransaction).filter(
        or_(
            FinanceTransaction.description.ilike(keyword),
            FinanceTransaction.category.ilike(keyword),
        )
    ).order_by(FinanceTransaction.date.desc()).limit(limit).all()
    for t in txs:
        sign = "+" if t.type == "income" else "-"
        results.append({
            "module": "财务", "icon": "💰", "type": "收支记录",
            "title": t.description or t.category,
            "subtitle": f"{t.category} · {sign}¥{t.amount:,.0f}",
            "date": t.date,
            "url": "/finance",
        })

    # 5. 基金
    from models.fund import FundFavorite
    funds = db.query(FundFavorite).filter(
        or_(
            FundFavorite.name.ilike(keyword),
            FundFavorite.code.ilike(keyword),
        )
    ).limit(limit).all()
    for f in funds:
        results.append({
            "module": "基金", "icon": "📈", "type": "自选基金",
            "title": f"{f.name} ({f.code})",
            "subtitle": f"持仓 ¥{f.shares * f.cost_nav:,.2f}" if f.shares and f.cost_nav else f.type,
            "date": f.nav_date or "",
            "url": "/fund/list",
        })

    # 6. 物品
    from models.item import Item
    items = db.query(Item).filter(
        or_(
            Item.name.ilike(keyword),
            Item.brand.ilike(keyword),
            Item.category.ilike(keyword),
            Item.location.ilike(keyword),
            Item.serial_number.ilike(keyword),
        )
    ).limit(limit).all()
    for i in items:
        results.append({
            "module": "物品", "icon": "📦", "type": "物品",
            "title": i.name,
            "subtitle": f"{i.category} · {i.location}" if i.location else i.category,
            "date": i.purchase_date or "",
            "url": "/item",
        })

    # 7. 车辆管理
    from models.vehicle import Vehicle, FuelRecord, VehicleExpense
    vehicles = db.query(Vehicle).filter(
        or_(
            Vehicle.name.ilike(keyword),
            Vehicle.brand.ilike(keyword),
            Vehicle.model.ilike(keyword),
            Vehicle.plate.ilike(keyword),
            Vehicle.color.ilike(keyword),
            Vehicle.fuel_type.ilike(keyword),
            Vehicle.notes.ilike(keyword),
        )
    ).limit(limit).all()
    for v in vehicles:
        results.append({
            "module": "车辆", "icon": "🚗", "type": "车辆",
            "title": v.name,
            "subtitle": f"{v.brand or ''} {v.model or ''} · {v.plate or ''}".strip(),
            "date": str(v.purchase_date) if v.purchase_date else "",
            "url": "/vehicle/list",
        })

    # 加油记录
    fuels = db.query(FuelRecord).filter(
        or_(
            FuelRecord.station_name.ilike(keyword),
            FuelRecord.fuel_grade.ilike(keyword),
            FuelRecord.charge_type.ilike(keyword),
            FuelRecord.notes.ilike(keyword),
        )
    ).order_by(FuelRecord.fuel_date.desc()).limit(limit).all()
    for f in fuels:
        veh = db.query(Vehicle).filter(Vehicle.id == f.vehicle_id).first()
        results.append({
            "module": "车辆", "icon": "⛽", "type": "加油/充电",
            "title": f"{veh.name if veh else ''} · {f.fuel_grade or f.charge_type or ''}",
            "subtitle": f"¥{f.actual_cost:,.0f}" if f.actual_cost else (f"¥{f.display_cost:,.0f}" if f.display_cost else ""),
            "date": str(f.fuel_date) if f.fuel_date else "",
            "url": "/vehicle/fuel",
        })

    # 车辆费用
    expenses = db.query(VehicleExpense).filter(
        or_(
            VehicleExpense.expense_type.ilike(keyword),
            VehicleExpense.notes.ilike(keyword),
        )
    ).order_by(VehicleExpense.expense_date.desc()).limit(limit).all()
    for e in expenses:
        veh = db.query(Vehicle).filter(Vehicle.id == e.vehicle_id).first()
        results.append({
            "module": "车辆", "icon": "🔧", "type": "车辆费用",
            "title": e.expense_type or "费用",
            "subtitle": f"{veh.name if veh else ''} · ¥{e.amount:,.0f}",
            "date": str(e.expense_date) if e.expense_date else "",
            "url": "/vehicle/list",
        })

    # 8. 健康管理
    from models.health import FamilyMember, HealthCheckup, HealthCheckupItem, DiseaseRecord, DiseaseVisit

    # 家庭成员
    members = db.query(FamilyMember).filter(
        or_(
            FamilyMember.name.ilike(keyword),
            FamilyMember.relationship.ilike(keyword),
            FamilyMember.allergy_history.ilike(keyword),
            FamilyMember.medical_history.ilike(keyword),
            FamilyMember.notes.ilike(keyword),
        )
    ).limit(limit).all()
    for m in members:
        results.append({
            "module": "健康", "icon": "❤️", "type": "家庭成员",
            "title": m.name,
            "subtitle": f"{m.relationship or ''}{' · ' + m.blood_type + '型' if m.blood_type else ''}",
            "date": m.birthday or "",
            "url": "/health/members",
        })

    # 疾病档案
    diseases = db.query(DiseaseRecord).filter(
        or_(
            DiseaseRecord.disease_name.ilike(keyword),
            DiseaseRecord.hospital.ilike(keyword),
            DiseaseRecord.doctor.ilike(keyword),
            DiseaseRecord.notes.ilike(keyword),
        )
    ).limit(limit).all()
    for d in diseases:
        mem = db.query(FamilyMember).filter(FamilyMember.id == d.member_id).first()
        results.append({
            "module": "健康", "icon": "🩺", "type": "疾病档案",
            "title": d.disease_name,
            "subtitle": f"{mem.name if mem else ''} · {d.status or ''}",
            "date": d.diagnosed_date or "",
            "url": "/health/disease",
        })

    # 就诊记录
    visits = db.query(DiseaseVisit).filter(
        or_(
            DiseaseVisit.hospital.ilike(keyword),
            DiseaseVisit.department.ilike(keyword),
            DiseaseVisit.doctor.ilike(keyword),
            DiseaseVisit.diagnosis.ilike(keyword),
            DiseaseVisit.treatment.ilike(keyword),
            DiseaseVisit.notes.ilike(keyword),
        )
    ).order_by(DiseaseVisit.visit_date.desc()).limit(limit).all()
    for v in visits:
        dis = db.query(DiseaseRecord).filter(DiseaseRecord.id == v.disease_id).first()
        mem = db.query(FamilyMember).filter(FamilyMember.id == v.member_id).first()
        results.append({
            "module": "健康", "icon": "🏥", "type": "就诊记录",
            "title": v.diagnosis or f"{dis.disease_name if dis else ''} 就诊",
            "subtitle": f"{mem.name if mem else ''} · {v.hospital or ''} {v.department or ''}".strip(),
            "date": v.visit_date or "",
            "url": "/health/disease",
        })

    # 体检记录
    checkups = db.query(HealthCheckup).filter(
        or_(
            HealthCheckup.hospital.ilike(keyword),
            HealthCheckup.checkup_type.ilike(keyword),
            HealthCheckup.summary.ilike(keyword),
            HealthCheckup.notes.ilike(keyword),
        )
    ).order_by(HealthCheckup.checkup_date.desc()).limit(limit).all()
    for c in checkups:
        mem = db.query(FamilyMember).filter(FamilyMember.id == c.member_id).first()
        results.append({
            "module": "健康", "icon": "📋", "type": "健康体检",
            "title": f"{c.checkup_type} · {c.checkup_date}",
            "subtitle": f"{mem.name if mem else ''} · {c.hospital or ''}",
            "date": c.checkup_date or "",
            "url": "/health/checkup",
        })

    # 体检指标
    items = db.query(HealthCheckupItem).filter(
        HealthCheckupItem.item_name.ilike(keyword)
    ).order_by(HealthCheckupItem.checkup_date.desc()).limit(limit).all()
    for it in items:
        mem = db.query(FamilyMember).filter(FamilyMember.id == it.member_id).first()
        val = f"{it.value:g}{it.unit}" if it.value is not None else (it.text_value or "")
        results.append({
            "module": "健康", "icon": "🔬", "type": "体检指标",
            "title": f"{it.item_name} {val}",
            "subtitle": f"{mem.name if mem else ''} · {it.abnormal_flag or ''}",
            "date": it.checkup_date or "",
            "url": "/health/checkup",
        })

    return {"keyword": q, "total": len(results), "results": results}
