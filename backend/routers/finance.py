"""财务管理路由"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, timedelta
from io import StringIO
import csv
import json
import os

from sqlalchemy.orm import Session
from database import get_db
from models.finance import (
    FinanceAccount, FinanceTransaction, AssetSnapshot,
    FinanceBillImport, FinanceCategoryRule,
    ASSET_TYPES, INCOME_CATEGORIES, EXPENSE_CATEGORIES, ALL_CATEGORIES,
)
from models.settings import UserSetting

router = APIRouter(prefix="/api/finance", tags=["财务管理"])


# ─── Pydantic Schemas ─────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str
    type: str = "cash"
    amount: float = 0
    institution: str = ""
    notes: str = ""

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[float] = None
    institution: Optional[str] = None
    notes: Optional[str] = None
    is_hidden: Optional[int] = None
    sort_order: Optional[int] = None

class TransactionCreate(BaseModel):
    type: str  # income / expense
    category: str
    amount: float
    date: str  # YYYY-MM-DD
    description: str = ""
    account_id: Optional[int] = None

class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    description: Optional[str] = None
    account_id: Optional[int] = None
    source: Optional[str] = None
    counterparty: Optional[str] = None
    pay_method: Optional[str] = None
    is_transfer: Optional[int] = None
    notes: Optional[str] = None


# ─── 资产配置 ─────────────────────────────────────────

def _get_categories(db: Session) -> tuple:
    """从 user_settings 读取分类列表，不存在则用默认值初始化"""
    for key, default in [
        ("finance_income_categories", INCOME_CATEGORIES),
        ("finance_expense_categories", EXPENSE_CATEGORIES),
    ]:
        row = db.query(UserSetting).filter(UserSetting.key == key).first()
        if not row:
            row = UserSetting(
                key=key,
                value=json.dumps(default, ensure_ascii=False),
                updated_at=datetime.now(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
    income_row = db.query(UserSetting).filter(UserSetting.key == "finance_income_categories").first()
    expense_row = db.query(UserSetting).filter(UserSetting.key == "finance_expense_categories").first()
    return json.loads(income_row.value), json.loads(expense_row.value)


@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    """获取资产类型、收支分类等配置"""
    income_cats, expense_cats = _get_categories(db)
    return {
        "asset_types": ASSET_TYPES,
        "income_categories": income_cats,
        "expense_categories": expense_cats,
    }


# ─── 分类管理 ─────────────────────────────────────────

class CategoryUpdateRequest(BaseModel):
    income_categories: list[str]
    expense_categories: list[str]


@router.put("/config/categories")
def update_categories(data: CategoryUpdateRequest, db: Session = Depends(get_db)):
    """保存分类列表"""
    for key, cats in [
        ("finance_income_categories", data.income_categories),
        ("finance_expense_categories", data.expense_categories),
    ]:
        row = db.query(UserSetting).filter(UserSetting.key == key).first()
        if row:
            row.value = json.dumps(cats, ensure_ascii=False)
            row.updated_at = datetime.now()
        else:
            row = UserSetting(key=key, value=json.dumps(cats, ensure_ascii=False), updated_at=datetime.now())
            db.add(row)
    db.commit()
    return {"message": "分类已更新"}


class CategoryRenameRequest(BaseModel):
    old_name: str
    new_name: str
    txn_type: str  # income / expense


@router.put("/config/categories/rename")
def rename_category(data: CategoryRenameRequest, db: Session = Depends(get_db)):
    """重命名分类，同步更新已有记录"""
    if not data.new_name.strip():
        return {"detail": "分类名不能为空", "updated": 0}
    # 更新分类列表
    key = f"finance_{'income' if data.txn_type == 'income' else 'expense'}_categories"
    row = db.query(UserSetting).filter(UserSetting.key == key).first()
    if row:
        cats = json.loads(row.value)
        if data.old_name in cats:
            idx = cats.index(data.old_name)
            cats[idx] = data.new_name.strip()
            row.value = json.dumps(cats, ensure_ascii=False)
    # 同步更新已有记录
    updated = db.query(FinanceTransaction).filter(
        FinanceTransaction.category == data.old_name,
    ).update({FinanceTransaction.category: data.new_name.strip()})
    db.commit()
    return {"message": f"已重命名，{updated} 条记录已同步", "updated": updated}


class CategoryDeleteRequest(BaseModel):
    category: str
    txn_type: str  # income / expense


@router.put("/config/categories/delete")
def delete_category(data: CategoryDeleteRequest, db: Session = Depends(get_db)):
    """删除分类，已有记录归为'其他'"""
    fallback = "其他收入" if data.txn_type == "income" else "其他支出"
    # 从分类列表中移除
    key = f"finance_{'income' if data.txn_type == 'income' else 'expense'}_categories"
    row = db.query(UserSetting).filter(UserSetting.key == key).first()
    if row:
        cats = json.loads(row.value)
        if data.category in cats:
            cats.remove(data.category)
            row.value = json.dumps(cats, ensure_ascii=False)
    # 已有记录归为"其他"
    updated = db.query(FinanceTransaction).filter(
        FinanceTransaction.category == data.category,
    ).update({FinanceTransaction.category: fallback})
    db.commit()
    return {"message": f"分类已删除，{updated} 条记录已归为'{fallback}'", "updated": updated}


# ═══════════════════════════════════════════════════════════
#  账户 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db)):
    """获取所有账户（按排序字段排列）"""
    accounts = db.query(FinanceAccount).order_by(
        FinanceAccount.is_hidden, FinanceAccount.sort_order, FinanceAccount.id
    ).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "amount": a.amount,
            "institution": a.institution,
            "notes": a.notes,
            "is_hidden": a.is_hidden,
            "sort_order": a.sort_order,
            "created_at": a.created_at.isoformat() if a.created_at else "",
            "updated_at": a.updated_at.isoformat() if a.updated_at else "",
            "type_label": ASSET_TYPES.get(a.type, {}).get("label", a.type),
            "type_icon": ASSET_TYPES.get(a.type, {}).get("icon", "📦"),
            "type_color": ASSET_TYPES.get(a.type, {}).get("color", "#6b7280"),
        }
        for a in accounts
    ]


@router.post("/accounts")
def create_account(data: AccountCreate, db: Session = Depends(get_db)):
    """新增账户"""
    account = FinanceAccount(
        name=data.name,
        type=data.type,
        amount=data.amount,
        institution=data.institution,
        notes=data.notes,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"id": account.id, "message": "账户创建成功"}


@router.put("/accounts/{account_id}")
def update_account(account_id: int, data: AccountUpdate, db: Session = Depends(get_db)):
    """更新账户"""
    account = db.query(FinanceAccount).filter(FinanceAccount.id == account_id).first()
    if not account:
        return {"error": "账户不存在"}, 404
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    account.updated_at = datetime.now()
    db.commit()
    return {"message": "更新成功"}


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """删除账户"""
    account = db.query(FinanceAccount).filter(FinanceAccount.id == account_id).first()
    if not account:
        return {"error": "账户不存在"}, 404
    db.delete(account)
    db.commit()
    return {"message": "删除成功"}


# ═══════════════════════════════════════════════════════════
#  收支记录 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/transactions")
def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    category: Optional[str] = None,
    account_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
    source: Optional[str] = None,
    is_transfer: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """获取收支记录（支持筛选 + 分页）"""
    query = db.query(FinanceTransaction)
    if type:
        query = query.filter(FinanceTransaction.type == type)
    if category:
        query = query.filter(FinanceTransaction.category == category)
    if account_id:
        query = query.filter(FinanceTransaction.account_id == account_id)
    if start_date:
        query = query.filter(FinanceTransaction.date >= start_date)
    if end_date:
        query = query.filter(FinanceTransaction.date <= end_date)
    if keyword:
        query = query.filter(
            FinanceTransaction.description.contains(keyword)
            | FinanceTransaction.counterparty.contains(keyword)
        )
    if source:
        query = query.filter(FinanceTransaction.source == source)
    if is_transfer is not None:
        query = query.filter(FinanceTransaction.is_transfer == is_transfer)

    total = query.count()
    items = query.order_by(FinanceTransaction.date.desc(), FinanceTransaction.id.desc()) \
        .offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [
            {
                "id": t.id,
                "type": t.type,
                "category": t.category,
                "amount": t.amount,
                "date": t.date,
                "description": t.description,
                "account_id": t.account_id,
                "source": t.source or "manual",
                "counterparty": t.counterparty or "",
                "pay_method": t.pay_method or "",
                "trade_no": t.trade_no or "",
                "import_id": t.import_id,
                "is_transfer": t.is_transfer or 0,
                "notes": t.notes or "",
                "created_at": t.created_at.isoformat() if t.created_at else "",
            }
            for t in items
        ],
        "total": total,
        "page": page,
        "total_pages": (total + limit - 1) // limit,
    }


@router.post("/transactions")
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    """新增收支记录"""
    txn = FinanceTransaction(
        type=data.type,
        category=data.category,
        amount=data.amount,
        date=data.date,
        description=data.description,
        account_id=data.account_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return {"id": txn.id, "message": "记录创建成功"}


@router.put("/transactions/{txn_id}")
def update_transaction(txn_id: int, data: TransactionUpdate, db: Session = Depends(get_db)):
    """更新收支记录"""
    txn = db.query(FinanceTransaction).filter(FinanceTransaction.id == txn_id).first()
    if not txn:
        return {"error": "记录不存在"}, 404
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(txn, field, value)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/transactions/{txn_id}")
def delete_transaction(txn_id: int, db: Session = Depends(get_db)):
    """删除收支记录"""
    txn = db.query(FinanceTransaction).filter(FinanceTransaction.id == txn_id).first()
    if not txn:
        return {"error": "记录不存在"}, 404
    db.delete(txn)
    db.commit()
    return {"message": "删除成功"}


# ═══════════════════════════════════════════════════════════
#  统计数据
# ═══════════════════════════════════════════════════════════

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """总览统计：总资产、总负债、净资产、分布"""
    accounts = db.query(FinanceAccount).filter(FinanceAccount.is_hidden == 0).all()
    total_assets = sum(a.amount for a in accounts if a.type != "debt")
    total_debt = sum(a.amount for a in accounts if a.type == "debt")
    net_assets = total_assets - total_debt

    # 资产分布
    breakdown = {}
    for a in accounts:
        key = a.type
        breakdown[key] = breakdown.get(key, 0) + a.amount

    # 本月收入/支出（排除转账）
    today = date.today()
    month_start = today.strftime("%Y-%m-01")
    month_txns = db.query(FinanceTransaction).filter(
        FinanceTransaction.date >= month_start,
        FinanceTransaction.is_transfer == 0,
    ).all()
    month_income = sum(t.amount for t in month_txns if t.type == "income")
    month_expense = sum(t.amount for t in month_txns if t.type == "expense")

    # 压岁钱（查找账户名称为"压岁钱"的账户余额）
    red_envelope_acc = db.query(FinanceAccount).filter(
        FinanceAccount.name == "压岁钱",
        FinanceAccount.is_hidden == 0
    ).first()
    red_envelope_amount = round(red_envelope_acc.amount, 2) if red_envelope_acc else 0

    return {
        "total_assets": round(total_assets, 2),
        "total_debt": round(total_debt, 2),
        "net_assets": round(net_assets, 2),
        "asset_breakdown": {k: round(v, 2) for k, v in breakdown.items()},
        "account_count": len(accounts),
        "month_income": round(month_income, 2),
        "month_expense": round(month_expense, 2),
        "red_envelope_amount": red_envelope_amount,
    }


@router.get("/stats/monthly")
def get_monthly_stats(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """月度收支统计（按月汇总，排除转账）"""
    if not year:
        year = date.today().year
    year_str = str(year)
    txns = db.query(FinanceTransaction).filter(
        FinanceTransaction.date.startswith(year_str),
        FinanceTransaction.is_transfer == 0,
    ).order_by(FinanceTransaction.date).all()

    monthly = {}
    for t in txns:
        month = t.date[:7]  # YYYY-MM
        if month not in monthly:
            monthly[month] = {"income": 0, "expense": 0}
        if t.type == "income":
            monthly[month]["income"] += t.amount
        else:
            monthly[month]["expense"] += t.amount

    result = [
        {"month": m, "income": round(d["income"], 2), "expense": round(d["expense"], 2)}
        for m, d in sorted(monthly.items())
    ]
    return result


@router.get("/stats/category")
def get_category_stats(
    type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """收支分类统计"""
    query = db.query(FinanceTransaction).filter(FinanceTransaction.is_transfer == 0)
    if type:
        query = query.filter(FinanceTransaction.type == type)
    if start_date:
        query = query.filter(FinanceTransaction.date >= start_date)
    if end_date:
        query = query.filter(FinanceTransaction.date <= end_date)

    txns = query.all()
    categories = {}
    for t in txns:
        cat_key = t.category
        if cat_key not in categories:
            categories[cat_key] = {"amount": 0, "type": t.type}
        categories[cat_key]["amount"] += t.amount

    result = [
        {"category": c, "amount": round(d["amount"], 2), "type": d["type"]}
        for c, d in sorted(categories.items(), key=lambda x: -x[1]["amount"])
    ]
    return result


# ═══════════════════════════════════════════════════════════
#  资产快照（趋势图）
# ═══════════════════════════════════════════════════════════

@router.get("/snapshots")
def list_snapshots(
    days: int = Query(365, ge=1, le=730),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取快照历史（分页）"""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    total = db.query(AssetSnapshot).filter(AssetSnapshot.date >= cutoff).count()
    snapshots = db.query(AssetSnapshot).filter(
        AssetSnapshot.date >= cutoff
    ).order_by(AssetSnapshot.date.desc()).offset((page - 1) * limit).limit(limit).all()

    # 处理 breakdown 字段（兼容 dict 和 str 两种存储格式）
    def parse_bd(bd):
        if bd is None:
            return {}
        if isinstance(bd, dict):
            return bd
        try:
            return json.loads(bd) if isinstance(bd, str) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    return {
        "items": [
            {
                "id": s.id,
                "date": s.date,
                "total_assets": s.total_assets,
                "total_debt": s.total_debt,
                "net_assets": s.net_assets,
                "breakdown": parse_bd(s.breakdown),
            }
            for s in snapshots
        ],
        "total": total,
        "page": page,
        "total_pages": (total + limit - 1) // limit,
    }


@router.get("/snapshots/stats")
def get_snapshot_stats(db: Session = Depends(get_db)):
    """快照月度统计分析：每月最后一条快照，计算环比变化"""
    all_snaps = db.query(AssetSnapshot).order_by(AssetSnapshot.date).all()

    # 按月分组，每月取最后一条
    monthly = {}
    for s in all_snaps:
        month = s.date[:7]
        monthly[month] = s

    result = []
    prev = None
    for month in sorted(monthly.keys()):
        snap = monthly[month]
        bd = snap.breakdown if isinstance(snap.breakdown, dict) else {}
        try:
            bd = json.loads(snap.breakdown) if isinstance(snap.breakdown, str) else bd
        except (json.JSONDecodeError, TypeError):
            bd = {}

        row = {
            "month": month,
            "total_assets": round(snap.total_assets, 2),
            "total_debt": round(snap.total_debt, 2),
            "net_assets": round(snap.net_assets, 2),
            "breakdown": {k: round(v, 2) for k, v in bd.items()},
        }

        if prev:
            # 环比变化
            row["assets_change"] = round(snap.total_assets - prev["total_assets"], 2)
            row["assets_change_pct"] = round(
                (snap.total_assets - prev["total_assets"]) / prev["total_assets"] * 100, 2
            ) if prev["total_assets"] != 0 else 0
            row["net_change"] = round(snap.net_assets - prev["net_assets"], 2)
            row["net_change_pct"] = round(
                (snap.net_assets - prev["net_assets"]) / prev["net_assets"] * 100, 2
            ) if prev["net_assets"] != 0 else 0
        else:
            row["assets_change"] = 0
            row["assets_change_pct"] = 0
            row["net_change"] = 0
            row["net_change_pct"] = 0

        # 账户环比变化
        if prev and prev.get("breakdown"):
            bd_changes = {}
            all_keys = set(list(bd.keys()) + list(prev["breakdown"].keys()))
            for k in all_keys:
                cur_val = bd.get(k, 0)
                prev_val = prev["breakdown"].get(k, 0)
                if prev_val != 0:
                    bd_changes[k] = {
                        "value": round(cur_val, 2),
                        "change": round(cur_val - prev_val, 2),
                        "change_pct": round((cur_val - prev_val) / abs(prev_val) * 100, 2),
                    }
                else:
                    bd_changes[k] = {"value": round(cur_val, 2), "change": round(cur_val, 2), "change_pct": 0}
            row["breakdown_changes"] = bd_changes

        prev = {
            "total_assets": snap.total_assets,
            "net_assets": snap.net_assets,
            "breakdown": bd,
        }
        result.append(row)

    return result


@router.post("/snapshots")
def create_snapshot(db: Session = Depends(get_db)):
    """保存今日快照"""
    today_str = date.today().isoformat()
    accounts = db.query(FinanceAccount).filter(FinanceAccount.is_hidden == 0).all()
    total_assets = sum(a.amount for a in accounts if a.type != "debt")
    total_debt = sum(a.amount for a in accounts if a.type == "debt")

    breakdown = {}
    for a in accounts:
        label = ASSET_TYPES.get(a.type, {}).get("label", a.type)
        breakdown[label] = breakdown.get(label, 0) + a.amount

    # 如果今天已有快照，则更新
    existing = db.query(AssetSnapshot).filter(AssetSnapshot.date == today_str).first()
    if existing:
        existing.total_assets = round(total_assets, 2)
        existing.total_debt = round(total_debt, 2)
        existing.net_assets = round(total_assets - total_debt, 2)
        existing.breakdown = {k: round(v, 2) for k, v in breakdown.items()}
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "message": "今日快照已更新"}

    snapshot = AssetSnapshot(
        date=today_str,
        total_assets=round(total_assets, 2),
        total_debt= round(total_debt, 2),
        net_assets=round(total_assets - total_debt, 2),
        breakdown={k: round(v, 2) for k, v in breakdown.items()},
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"id": snapshot.id, "message": "快照创建成功"}


@router.delete("/snapshots/{snapshot_id}")
def delete_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    """删除快照"""
    snap = db.query(AssetSnapshot).filter(AssetSnapshot.id == snapshot_id).first()
    if not snap:
        return {"error": "快照不存在"}, 404
    db.delete(snap)
    db.commit()
    return {"message": "删除成功"}


# ═══════════════════════════════════════════════════════════
#  导入 / 导出
# ═══════════════════════════════════════════════════════════

@router.get("/export/backup")
def export_backup(db: Session = Depends(get_db)):
    """导出全量备份 JSON"""
    accounts = db.query(FinanceAccount).all()
    transactions = db.query(FinanceTransaction).all()
    snapshots = db.query(AssetSnapshot).all()

    backup = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "accounts": [
            {
                "name": a.name, "type": a.type, "amount": a.amount,
                "institution": a.institution, "notes": a.notes,
            }
            for a in accounts
        ],
        "transactions": [
            {
                "type": t.type, "category": t.category, "amount": t.amount,
                "date": t.date, "description": t.description,
            }
            for t in transactions
        ],
        "snapshots": [
            {
                "date": s.date, "total_assets": s.total_assets,
                "total_debt": s.total_debt, "net_assets": s.net_assets,
                "breakdown": s.breakdown,
            }
            for s in snapshots
        ],
    }
    return backup


@router.post("/import/backup")
def import_backup(data: dict, db: Session = Depends(get_db)):
    """导入备份 JSON，支持两种格式：
    1. allinone 格式：{"backup": {"version": ..., "accounts": [...], ...}, "mode": "merge/replace"}
    2. money 项目格式（顶层直接 assets/transactions/snapshots）
    """
    mode = data.get("mode", "merge")
    backup = data.get("backup")

    # 判断是 money 格式还是 allinone 格式
    is_money_format = not backup and ("assets" in data or "transactions" in data)
    if is_money_format:
        backup = data

    if not backup:
        return {"error": "备份文件格式不正确"}

    imported = {"accounts": 0, "transactions": 0, "snapshots": 0}

    if mode == "replace":
        db.query(FinanceAccount).delete()
        db.query(FinanceTransaction).delete()
        db.query(AssetSnapshot).delete()
        db.commit()

    # 兼容 money 的 "assets" 和 allinone 的 "accounts"
    account_list = backup.get("assets", backup.get("accounts", []))
    for a in account_list:
        acc = FinanceAccount(
            name=a.get("name", ""),
            type=a.get("type", "other"),
            amount=float(a.get("amount", 0)),
            institution=a.get("institution", ""),
            notes=a.get("notes", ""),
        )
        db.add(acc)
        imported["accounts"] += 1

    for t in backup.get("transactions", []):
        txn = FinanceTransaction(
            type=t.get("type", "expense"),
            category=t.get("category", "其他"),
            amount=float(t.get("amount", 0)),
            date=t.get("date", ""),
            description=t.get("description", ""),
        )
        db.add(txn)
        imported["transactions"] += 1

    for s in backup.get("snapshots", []):
        # money 格式用 camelCase: totalAssets, allinone 用 snake_case: total_assets
        snap_date = s.get("date", "")
        total_assets = float(s.get("totalAssets", s.get("total_assets", 0)))
        total_debt = float(s.get("totalDebt", s.get("total_debt", 0)))
        net_assets = float(s.get("netAssets", s.get("net_assets", total_assets - total_debt)))
        breakdown = s.get("breakdown")

        existing = db.query(AssetSnapshot).filter(AssetSnapshot.date == snap_date).first()
        if existing and mode == "merge":
            continue
        snap = AssetSnapshot(
            date=snap_date,
            total_assets=total_assets,
            total_debt=total_debt,
            net_assets=net_assets,
            breakdown=json.dumps(breakdown) if breakdown else None,
        )
        if existing:
            snap.id = existing.id
        db.add(snap)
        imported["snapshots"] += 1

    db.commit()
    return {
        "message": f"导入成功（{'覆盖' if mode == 'replace' else '合并'}模式）",
        "imported": imported,
    }


@router.get("/export/csv")
def export_csv(
    type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """导出收支记录为 CSV"""
    query = db.query(FinanceTransaction)
    if type:
        query = query.filter(FinanceTransaction.type == type)
    txns = query.order_by(FinanceTransaction.date.desc()).all()

    output = StringIO()
    output.write("\ufeff")  # BOM for Excel
    writer = csv.writer(output)
    writer.writerow(["日期", "类型", "分类", "金额", "描述", "来源", "交易对方", "支付方式"])

    for t in txns:
        writer.writerow([
            t.date,
            "收入" if t.type == "income" else "支出",
            t.category,
            t.amount,
            t.description,
            t.source or "手动",
            t.counterparty or "",
            t.pay_method or "",
        ])

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=transactions_{date.today().isoformat()}.csv"
        },
    )


# ═══════════════════════════════════════════════════════════
#  账单导入
# ═══════════════════════════════════════════════════════════

from fastapi import UploadFile, File, HTTPException
from services.bill_parser import parse_bill, deduplicate, auto_classify

# 预览数据缓存（key: filename hash, value: parsed records）
_preview_cache: dict = {}


class BillImportRequest(BaseModel):
    filename: str
    records: list  # 前端确认后的记录列表


@router.post("/bills/parse")
async def parse_bill_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传并解析账单文件，返回预览数据（不入库）"""
    content = await file.read()

    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "文件大小不能超过 50MB")

    source, records = parse_bill(content, file.filename or "")

    if source == "unknown" or not records:
        raise HTTPException(400, "无法识别账单格式，请确认是支付宝或微信导出的 CSV 文件")

    # 去重检测
    new_records, dup_records = deduplicate(records, db)

    # 自动分类
    new_records = auto_classify(new_records, db)

    # 统计未分类数量
    unclassified = sum(1 for r in new_records if r.get("category", "") in ("", "其他支出", "其他收入"))

    # 缓存解析结果供导入使用
    import hashlib
    cache_key = hashlib.md5(content).hexdigest()
    _preview_cache[cache_key] = {
        "source": source,
        "filename": file.filename,
        "records": new_records,
    }

    # 预览返回前 50 条
    preview = new_records[:50]

    source_label = {"alipay": "支付宝", "wechat": "微信"}.get(source, source)

    return {
        "source": source,
        "source_label": source_label,
        "cache_key": cache_key,
        "preview": [
            {
                "date": r.get("date", ""),
                "description": r.get("description", ""),
                "counterparty": r.get("counterparty", ""),
                "amount": r.get("amount", 0),
                "type": r.get("type", ""),
                "category": r.get("category", ""),
                "is_transfer": r.get("is_transfer", 0),
                "is_duplicate": r.get("_is_duplicate", False),
                "trade_no": r.get("trade_no", ""),
            }
            for r in preview
        ],
        "stats": {
            "total": len(records),
            "new": len(new_records),
            "duplicate": len(dup_records),
            "unclassified": unclassified,
            "transfer": sum(1 for r in new_records if r.get("is_transfer")),
        },
    }


@router.post("/bills/import")
def confirm_bill_import(data: BillImportRequest, db: Session = Depends(get_db)):
    """确认导入账单记录"""
    # 查找缓存
    cache_key = data.filename  # 前端传入 cache_key
    cached = _preview_cache.get(cache_key)
    if not cached:
        raise HTTPException(400, "预览数据已过期，请重新上传文件")

    records = cached["records"]
    source = cached["source"]

    if not records:
        return {"error": "没有可导入的记录"}

    # 创建导入批次
    batch = FinanceBillImport(
        source=source,
        file_name=data.filename if data.filename != cache_key else cached.get("filename", ""),
        total_count=len(records),
        status="completed",
    )
    db.add(batch)
    db.flush()  # 获取 batch.id

    imported = 0
    failed = 0
    for r in records:
        if r.get("_is_duplicate"):
            batch.skipped_count = (batch.skipped_count or 0) + 1
            continue
        try:
            txn = FinanceTransaction(
                source=r.get("source", source),
                type=r.get("type", "expense"),
                category=r.get("category", "其他支出"),
                amount=r.get("amount", 0),
                date=r.get("date", ""),
                description=r.get("description", ""),
                counterparty=r.get("counterparty", ""),
                pay_method=r.get("pay_method", ""),
                trade_no=r.get("trade_no", ""),
                import_id=batch.id,
                is_transfer=r.get("is_transfer", 0),
                raw_data=r.get("raw", ""),
            )
            db.add(txn)
            imported += 1
        except Exception:
            failed += 1

    batch.imported_count = imported
    batch.failed_count = failed
    db.commit()

    # 清除缓存
    _preview_cache.pop(cache_key, None)

    return {
        "message": f"导入完成：成功 {imported} 条，跳过 {batch.skipped_count} 条，失败 {failed} 条",
        "imported": imported,
        "skipped": batch.skipped_count,
        "failed": failed,
        "batch_id": batch.id,
    }


@router.get("/bills/imports")
def list_bill_imports(db: Session = Depends(get_db)):
    """获取导入批次列表"""
    batches = db.query(FinanceBillImport).order_by(FinanceBillImport.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "source": b.source,
            "source_label": {"alipay": "支付宝", "wechat": "微信"}.get(b.source, b.source),
            "file_name": b.file_name,
            "total_count": b.total_count,
            "imported_count": b.imported_count,
            "skipped_count": b.skipped_count,
            "failed_count": b.failed_count,
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else "",
        }
        for b in batches
    ]


@router.delete("/bills/imports/{import_id}")
def delete_bill_import(import_id: int, db: Session = Depends(get_db)):
    """删除导入批次及其关联的记录"""
    batch = db.query(FinanceBillImport).filter(FinanceBillImport.id == import_id).first()
    if not batch:
        raise HTTPException(404, "导入批次不存在")

    # 删除关联的交易记录
    count = db.query(FinanceTransaction).filter(FinanceTransaction.import_id == import_id).count()
    db.query(FinanceTransaction).filter(FinanceTransaction.import_id == import_id).delete()
    db.delete(batch)
    db.commit()
    return {"message": f"已删除批次及 {count} 条关联记录"}


# ═══════════════════════════════════════════════════════════
#  分类规则 CRUD
# ═══════════════════════════════════════════════════════════

class CategoryRuleCreate(BaseModel):
    name: str
    match_field: str = "description"  # description / counterparty
    match_type: str = "contains"      # contains / equals / regex
    match_value: str
    category: str
    txn_type: str = "all"             # income / expense / all
    platform: str = "all"             # alipay / wechat / all
    priority: int = 100

class CategoryRuleUpdate(BaseModel):
    name: Optional[str] = None
    match_field: Optional[str] = None
    match_type: Optional[str] = None
    match_value: Optional[str] = None
    category: Optional[str] = None
    txn_type: Optional[str] = None
    platform: Optional[str] = None
    priority: Optional[int] = None
    is_enabled: Optional[int] = None


@router.get("/category-rules")
def list_category_rules(db: Session = Depends(get_db)):
    """获取分类规则列表（按优先级排序）"""
    rules = db.query(FinanceCategoryRule).order_by(
        FinanceCategoryRule.is_enabled.desc(),
        FinanceCategoryRule.priority,
        FinanceCategoryRule.id,
    ).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "match_field": r.match_field,
            "match_type": r.match_type,
            "match_value": r.match_value,
            "category": r.category,
            "txn_type": r.txn_type,
            "platform": r.platform,
            "priority": r.priority,
            "is_enabled": r.is_enabled,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rules
    ]


@router.post("/category-rules")
def create_category_rule(data: CategoryRuleCreate, db: Session = Depends(get_db)):
    """新增分类规则"""
    rule = FinanceCategoryRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "message": "规则已创建"}


@router.put("/category-rules/{rule_id}")
def update_category_rule(rule_id: int, data: CategoryRuleUpdate, db: Session = Depends(get_db)):
    """编辑分类规则"""
    rule = db.query(FinanceCategoryRule).filter(FinanceCategoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    return {"message": "规则已更新"}


@router.delete("/category-rules/{rule_id}")
def delete_category_rule(rule_id: int, db: Session = Depends(get_db)):
    """删除分类规则"""
    rule = db.query(FinanceCategoryRule).filter(FinanceCategoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    db.delete(rule)
    db.commit()
    return {"message": "规则已删除"}


@router.post("/category-rules/reapply")
def reapply_category_rules(db: Session = Depends(get_db)):
    """重新应用分类规则到所有导入记录（source != manual 且未手动指定分类的）"""
    rules = db.query(FinanceCategoryRule).filter(FinanceCategoryRule.is_enabled == 1) \
        .order_by(FinanceCategoryRule.priority, FinanceCategoryRule.id).all()

    if not rules:
        return {"message": "没有启用的分类规则", "updated": 0}

    # 获取所有待分类的记录
    txns = db.query(FinanceTransaction).filter(
        FinanceTransaction.source != "manual",
    ).all()

    import re
    updated = 0
    for t in txns:
        matched = False
        for rule in rules:
            if rule.txn_type != "all" and rule.txn_type != t.type:
                continue
            if rule.platform != "all" and rule.platform != t.source:
                continue

            match_text = ""
            if rule.match_field == "description":
                match_text = t.description or ""
            elif rule.match_field == "counterparty":
                match_text = t.counterparty or ""

            pattern = rule.match_value
            if rule.match_type == "contains":
                patterns = [p.strip() for p in pattern.split("\n") if p.strip()]
                if any(p in match_text for p in patterns):
                    t.category = rule.category
                    matched = True
                    break
            elif rule.match_type == "equals":
                patterns = [p.strip() for p in pattern.split("\n") if p.strip()]
                if match_text.strip() in patterns:
                    t.category = rule.category
                    matched = True
                    break
            elif rule.match_type == "regex":
                try:
                    if re.search(pattern, match_text):
                        t.category = rule.category
                        matched = True
                        break
                except re.error:
                    continue

        if not matched:
            t.category = "其他支出" if t.type == "expense" else "其他收入"
        updated += 1

    db.commit()
    return {"message": f"已重新分类 {updated} 条记录", "updated": updated}


# ═══════════════════════════════════════════════════════════
#  统计增强
# ═══════════════════════════════════════════════════════════

@router.get("/stats/platform")
def get_platform_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """按平台统计收支（排除转账）"""
    query = db.query(FinanceTransaction).filter(FinanceTransaction.is_transfer == 0)
    if start_date:
        query = query.filter(FinanceTransaction.date >= start_date)
    if end_date:
        query = query.filter(FinanceTransaction.date <= end_date)
    txns = query.all()

    platforms = {}
    for t in txns:
        src = t.source or "manual"
        if src not in platforms:
            platforms[src] = {"income": 0, "expense": 0, "count": 0}
        if t.type == "income":
            platforms[src]["income"] += t.amount
        else:
            platforms[src]["expense"] += t.amount
        platforms[src]["count"] += 1

    source_labels = {"manual": "手动录入", "alipay": "支付宝", "wechat": "微信支付"}
    return [
        {
            "platform": k,
            "platform_label": source_labels.get(k, k),
            "income": round(v["income"], 2),
            "expense": round(v["expense"], 2),
            "count": v["count"],
        }
        for k, v in sorted(platforms.items(), key=lambda x: -x[1]["count"])
    ]


@router.get("/stats/top-merchants")
def get_top_merchants(
    limit: int = Query(10, ge=1, le=50),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """TOP 商户/交易对方统计（仅支出）"""
    query = db.query(FinanceTransaction).filter(
        FinanceTransaction.type == "expense",
        FinanceTransaction.is_transfer == 0,
        FinanceTransaction.counterparty != "",
    )
    if start_date:
        query = query.filter(FinanceTransaction.date >= start_date)
    if end_date:
        query = query.filter(FinanceTransaction.date <= end_date)
    txns = query.all()

    merchants = {}
    for t in txns:
        cp = t.counterparty.strip()
        if not cp:
            continue
        if cp not in merchants:
            merchants[cp] = {"amount": 0, "count": 0}
        merchants[cp]["amount"] += t.amount
        merchants[cp]["count"] += 1

    return sorted(
        [{"counterparty": k, "amount": round(v["amount"], 2), "count": v["count"]}
         for k, v in merchants.items()],
        key=lambda x: -x["amount"],
    )[:limit]


@router.get("/stats/transfer")
def get_transfer_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """转账类汇总（不计入收支的部分）"""
    query = db.query(FinanceTransaction).filter(FinanceTransaction.is_transfer == 1)
    if start_date:
        query = query.filter(FinanceTransaction.date >= start_date)
    if end_date:
        query = query.filter(FinanceTransaction.date <= end_date)
    txns = query.all()

    total_amount = sum(t.amount for t in txns)
    return {
        "count": len(txns),
        "total_amount": round(total_amount, 2),
    }


@router.get("/stats/monthly-compare")
def get_monthly_compare(
    months: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """月度环比对比"""
    today = date.today()
    result = []

    for i in range(months - 1, -1, -1):
        d = today - timedelta(days=i * 30)
        month_str = d.strftime("%Y-%m")
        month_start = f"{month_str}-01"

        if i < months - 1:
            next_d = today - timedelta(days=(i - 1) * 30)
            next_month_start = next_d.strftime("%Y-%m-01")
        else:
            next_month_start = (today + timedelta(days=1)).strftime("%Y-%m-01")

        txns = db.query(FinanceTransaction).filter(
            FinanceTransaction.date >= month_start,
            FinanceTransaction.date < next_month_start,
            FinanceTransaction.is_transfer == 0,
        ).all()

        income = sum(t.amount for t in txns if t.type == "income")
        expense = sum(t.amount for t in txns if t.type == "expense")

        row = {
            "month": month_str,
            "income": round(income, 2),
            "expense": round(expense, 2),
            "balance": round(income - expense, 2),
        }

        if result:
            prev = result[-1]
            row["expense_change"] = round(row["expense"] - prev["expense"], 2)
            row["expense_change_pct"] = round(
                (row["expense"] - prev["expense"]) / prev["expense"] * 100, 2
            ) if prev["expense"] != 0 else 0
            row["income_change"] = round(row["income"] - prev["income"], 2)
        else:
            row["expense_change"] = 0
            row["expense_change_pct"] = 0
            row["income_change"] = 0

        result.append(row)

    return result
