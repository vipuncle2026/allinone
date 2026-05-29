"""基金管理 API 路由"""
from datetime import datetime, date as date_type, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models.fund import FundFavorite, FundGroup, FundLibrary, FundSnapshot, FundSnapshotItem
from services import fund_service

router = APIRouter(prefix="/api/fund", tags=["fund"])


# ============================================================
# Pydantic Schemas
# ============================================================

class FundAddRequest(BaseModel):
    code: str
    group_id: Optional[str] = "default"
    shares: float = 0
    cost_nav: float = 0


class FundUpdateHolding(BaseModel):
    shares: float = 0
    cost_nav: float = 0
    type: Optional[str] = None


class FundChangeGroup(BaseModel):
    group_id: str


class GroupCreate(BaseModel):
    name: str
    color: str = "#6b7280"


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class FundImportItem(BaseModel):
    code: str
    name: str
    type: Optional[str] = "混合型"
    is_etf: Optional[bool] = False
    group_id: Optional[str] = "default"
    shares: Optional[float] = 0
    cost_nav: Optional[float] = 0
    nav: Optional[float] = 0
    est_nav: Optional[float] = 0
    day_chg: Optional[float] = 0
    nav_date: Optional[str] = ""
    val_time: Optional[str] = ""
    manager: Optional[str] = "--"
    company: Optional[str] = "--"
    scale: Optional[float] = 0


# ============================================================
# 基金自选 API
# ============================================================

@router.get("/search/{code}")
async def search_fund(code: str, db: Session = Depends(get_db)):
    """查询基金信息（不添加，用于添加前预览）"""
    return await fund_service.search_fund_data(code, db)


@router.post("/add")
async def add_fund(req: FundAddRequest, db: Session = Depends(get_db)):
    """添加自选基金（自动识别场外/场内）"""
    code = req.code.strip().zfill(6)
    fund = await fund_service.build_new_fund(code, req.group_id, req.shares, req.cost_nav, db)

    lib = db.query(FundLibrary).filter(FundLibrary.code == code).first()
    if fund.nav > 0 or lib or fund.name != f"基金{code}":
        db.add(fund)
        db.commit()
        db.refresh(fund)
        return {"ok": True, "message": f"已添加：{fund.name}", "fund": fund_service.fund_to_dict(fund)}
    else:
        raise HTTPException(404, f"未找到基金代码 {code}，请确认后重试")


@router.delete("/{code}")
async def remove_fund(code: str, db: Session = Depends(get_db)):
    """移出自选"""
    fund = db.query(FundFavorite).filter(FundFavorite.code == code).first()
    if not fund:
        raise HTTPException(404, "基金不存在")
    db.delete(fund)
    db.commit()
    return {"ok": True, "message": "已移出自选"}


@router.post("/refresh")
async def refresh_all(db: Session = Depends(get_db)):
    """刷新所有自选基金估值"""
    return await fund_service.refresh_all_navs(db)


@router.get("/list")
async def list_funds(
    group_id: Optional[str] = Query("all", description="分组筛选，all=全部"),
    db: Session = Depends(get_db),
):
    """获取自选基金列表"""
    query = db.query(FundFavorite)
    if group_id != "all":
        query = query.filter(FundFavorite.group_id == group_id)

    funds = query.order_by(desc(FundFavorite.updated_at)).all()
    return [fund_service.fund_to_dict(f) for f in funds]


@router.put("/{code}/holding")
async def update_holding(code: str, req: FundUpdateHolding, db: Session = Depends(get_db)):
    """更新持仓（份额 + 成本净值）"""
    fund = db.query(FundFavorite).filter(FundFavorite.code == code).first()
    if not fund:
        raise HTTPException(404, "基金不存在")
    fund.shares = req.shares
    fund.cost_nav = req.cost_nav
    if req.type:
        fund.type = req.type
    fund.updated_at = datetime.now()
    db.commit()
    db.refresh(fund)
    return {"ok": True, "message": "持仓已保存", "fund": fund_service.fund_to_dict(fund)}


@router.put("/{code}/group")
async def change_group(code: str, req: FundChangeGroup, db: Session = Depends(get_db)):
    """修改基金分组"""
    fund = db.query(FundFavorite).filter(FundFavorite.code == code).first()
    if not fund:
        raise HTTPException(404, "基金不存在")
    fund.group_id = req.group_id
    fund.updated_at = datetime.now()
    db.commit()
    group = db.query(FundGroup).filter(FundGroup.id == req.group_id).first()
    group_name = group.name if group else "默认分组"
    return {"ok": True, "message": f"已移至\"{group_name}\""}


# ============================================================
# 持仓分析 API
# ============================================================

@router.get("/holding/summary")
async def holding_summary(db: Session = Depends(get_db)):
    """持仓汇总"""
    return fund_service.calc_holding_summary(db)


# ============================================================
# 分组管理 API
# ============================================================

@router.get("/groups")
async def list_groups(db: Session = Depends(get_db)):
    """获取所有分组"""
    groups = db.query(FundGroup).order_by(FundGroup.sort_order).all()
    result = []
    for g in groups:
        count = db.query(FundFavorite).filter(FundFavorite.group_id == g.id).count()
        result.append({
            "id": g.id, "name": g.name, "color": g.color,
            "sort_order": g.sort_order, "is_default": g.is_default, "count": count,
        })
    return result


@router.post("/groups")
async def create_group(req: GroupCreate, db: Session = Depends(get_db)):
    """创建分组"""
    existing = db.query(FundGroup).filter(FundGroup.name == req.name).first()
    if existing:
        raise HTTPException(400, "分组名称已存在")

    max_order = db.query(FundGroup).count()
    group = FundGroup(
        id=f"g_{int(datetime.now().timestamp()*1000)}",
        name=req.name, color=req.color, sort_order=max_order,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"ok": True, "message": "分组已添加", "group": {"id": group.id, "name": group.name, "color": group.color}}


@router.put("/groups/{group_id}")
async def update_group(group_id: str, req: GroupUpdate, db: Session = Depends(get_db)):
    """编辑分组"""
    group = db.query(FundGroup).filter(FundGroup.id == group_id).first()
    if not group:
        raise HTTPException(404, "分组不存在")
    if group.is_default:
        raise HTTPException(400, "默认分组不可编辑")
    if req.name:
        existing = db.query(FundGroup).filter(FundGroup.name == req.name, FundGroup.id != group_id).first()
        if existing:
            raise HTTPException(400, "分组名称已存在")
        group.name = req.name
    if req.color:
        group.color = req.color
    db.commit()
    return {"ok": True, "message": "分组已更新"}


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str, db: Session = Depends(get_db)):
    """删除分组（基金移到默认分组）"""
    group = db.query(FundGroup).filter(FundGroup.id == group_id).first()
    if not group:
        raise HTTPException(404, "分组不存在")
    if group.is_default:
        raise HTTPException(400, "默认分组不可删除")

    db.query(FundFavorite).filter(FundFavorite.group_id == group_id).update({"group_id": "default"})
    db.delete(group)
    db.commit()
    return {"ok": True, "message": "分组已删除"}


# ============================================================
# 导入导出 API
# ============================================================

@router.get("/export")
async def export_holdings(db: Session = Depends(get_db)):
    """导出自选基金数据"""
    funds = db.query(FundFavorite).all()
    data = {
        "version": 3,
        "exported_at": datetime.now().isoformat(),
        "funds": {f.code: fund_service.fund_to_dict(f) for f in funds},
    }
    return data


@router.post("/import")
async def import_holdings(items: list[FundImportItem], db: Session = Depends(get_db)):
    """导入自选基金数据（跳过已存在的）"""
    added = 0
    skipped = 0
    for item in items:
        existing = db.query(FundFavorite).filter(FundFavorite.code == item.code).first()
        if existing:
            skipped += 1
            continue
        fund = FundFavorite(
            code=item.code, name=item.name, type=item.type or "混合型",
            is_etf=item.is_etf or False, group_id=item.group_id or "default",
            shares=item.shares or 0, cost_nav=item.cost_nav or 0,
            nav=item.nav or 0, est_nav=item.est_nav or 0, day_chg=item.day_chg or 0,
            nav_date=item.nav_date or "", val_time=item.val_time or "",
            manager=item.manager or "--", company=item.company or "--", scale=item.scale or 0,
        )
        db.add(fund)
        added += 1
    db.commit()
    return {"ok": True, "message": f"导入完成：新增 {added} 只，跳过 {skipped} 只", "added": added, "skipped": skipped}


# ============================================================
# 基金详情
# ============================================================

@router.get("/detail/{code}")
async def get_fund_detail(code: str, db: Session = Depends(get_db)):
    """获取基金详情（持仓Top10 + 近30天净值 + 基本信息）"""
    return await fund_service.fetch_fund_detail_data(code, db)


# ============================================================
# 持仓快照 API
# ============================================================

@router.post("/snapshot/take")
async def take_snapshot(db: Session = Depends(get_db)):
    """手动触发今日持仓快照"""
    return await fund_service.do_take_snapshot(db)


@router.get("/snapshot/list")
async def list_snapshots(
    days: int = Query(30, description="查询最近N天，0表示全部"),
    db: Session = Depends(get_db),
):
    """获取持仓快照列表"""
    q = db.query(FundSnapshot).order_by(FundSnapshot.snapshot_date.desc())
    if days > 0:
        since = (date_type.today() - timedelta(days=days)).isoformat()
        q = q.filter(FundSnapshot.snapshot_date >= since)
    snapshots = q.all()

    result = []
    for s in snapshots:
        items = db.query(FundSnapshotItem).filter(FundSnapshotItem.snapshot_date == s.snapshot_date).all()
        result.append({
            "date": s.snapshot_date,
            "total_market": s.total_market,
            "total_cost": s.total_cost,
            "total_gain": s.total_gain,
            "total_rate": s.total_rate,
            "today_profit": s.today_profit,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "items": [
                {
                    "code": i.code, "name": i.name, "nav": i.nav,
                    "shares": i.shares, "market_value": i.market_value,
                    "day_chg": i.day_chg, "today_gain": i.today_gain,
                }
                for i in items
            ],
        })

    return {"snapshots": result, "total": len(result)}


@router.delete("/snapshot/{snapshot_date}")
async def delete_snapshot(snapshot_date: str, db: Session = Depends(get_db)):
    """删除某天快照"""
    snap = db.query(FundSnapshot).filter(FundSnapshot.snapshot_date == snapshot_date).first()
    if not snap:
        raise HTTPException(404, "快照不存在")
    db.query(FundSnapshotItem).filter(FundSnapshotItem.snapshot_date == snapshot_date).delete()
    db.delete(snap)
    db.commit()
    return {"ok": True, "message": f"已删除 {snapshot_date} 快照"}
