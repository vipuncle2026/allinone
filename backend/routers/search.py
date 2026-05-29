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

    return {"keyword": q, "total": len(results), "results": results}
