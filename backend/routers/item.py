"""重要物品管理 API 路由"""
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db, get_upload_dir
from models.item import Item, ITEM_CATEGORIES

router = APIRouter(prefix="/api/item", tags=["物品管理"])

UPLOAD_DIR = get_upload_dir("items")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── Schemas ────────────────────────────────────────────

class ItemCreate(BaseModel):
    name: str
    category: str = "其他"
    brand: str = ""
    purchase_date: str = ""
    purchase_price: float = 0
    estimated_value: float = 0
    serial_number: str = ""
    location: str = ""
    status: str = "在用"
    photo_path: str = ""
    notes: str = ""
    is_important: bool = False


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    purchase_date: Optional[str] = None
    purchase_price: Optional[float] = None
    estimated_value: Optional[float] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    photo_path: Optional[str] = None
    notes: Optional[str] = None
    is_important: Optional[bool] = None


# ─── CRUD ──────────────────────────────────────────────

def _item_to_dict(item: Item) -> dict:
    """物品对象转字典"""
    return {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "category_icon": ITEM_CATEGORIES.get(item.category, {}).get("icon", "📦"),
        "category_color": ITEM_CATEGORIES.get(item.category, {}).get("color", "#94A3B8"),
        "brand": item.brand,
        "purchase_date": item.purchase_date,
        "purchase_price": item.purchase_price,
        "estimated_value": item.estimated_value,
        "serial_number": item.serial_number,
        "location": item.location,
        "status": item.status,
        "photo_path": item.photo_path,
        "notes": item.notes,
        "is_important": item.is_important,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get("/list")
def list_items(
    category: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    important_only: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """物品列表（分页 + 筛选）"""
    q = db.query(Item)
    if category:
        q = q.filter(Item.category == category)
    if status:
        q = q.filter(Item.status == status)
    if important_only:
        q = q.filter(Item.is_important == True)
    if keyword:
        q = q.filter(
            (Item.name.contains(keyword)) |
            (Item.brand.contains(keyword)) |
            (Item.location.contains(keyword)) |
            (Item.serial_number.contains(keyword))
        )
    total = q.count()
    items = q.order_by(desc(Item.is_important), desc(Item.updated_at)) \
        .offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_item_to_dict(i) for i in items],
        "total": total, "page": page, "page_size": page_size,
    }


@router.get("/all")
def list_all_items(db: Session = Depends(get_db)):
    """获取全部物品（不分页，用于导出等）"""
    items = db.query(Item).order_by(desc(Item.updated_at)).all()
    return [_item_to_dict(i) for i in items]


@router.get("/config")
def get_config():
    """获取分类配置"""
    return {"categories": ITEM_CATEGORIES}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """物品统计"""
    total = db.query(func.count(Item.id)).scalar() or 0
    important_count = db.query(func.count(Item.id)).filter(Item.is_important == True).scalar() or 0
    total_value = db.query(func.sum(Item.estimated_value)).scalar() or 0
    total_cost = db.query(func.sum(Item.purchase_price)).scalar() or 0

    # 分类统计
    category_stats = db.query(
        Item.category,
        func.count(Item.id).label("count"),
        func.coalesce(func.sum(Item.estimated_value), 0).label("total_value"),
    ).group_by(Item.category).all()

    # 状态统计
    status_stats = db.query(
        Item.status,
        func.count(Item.id).label("count"),
    ).group_by(Item.status).all()

    return {
        "total": total,
        "important_count": important_count,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "by_category": [
            {
                "category": cat,
                "icon": ITEM_CATEGORIES.get(cat, {}).get("icon", "📦"),
                "color": ITEM_CATEGORIES.get(cat, {}).get("color", "#94A3B8"),
                "count": cnt,
                "total_value": round(val, 2),
            }
            for cat, cnt, val in category_stats
        ],
        "by_status": [
            {"status": s, "count": cnt}
            for s, cnt in status_stats
        ],
    }


@router.get("/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    """物品详情"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "物品不存在")
    return _item_to_dict(item)


@router.post("/create")
def create_item(data: ItemCreate, db: Session = Depends(get_db)):
    """创建物品"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    item = Item(**data.model_dump(), created_at=now, updated_at=now)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "message": "创建成功"}


@router.put("/{item_id}")
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db)):
    """更新物品"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "物品不存在")
    update_data = data.model_dump(exclude_none=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    item.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    return {"message": "更新成功"}


@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """删除物品"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "物品不存在")
    # 删除关联图片文件（photo_path 格式: uploads/items/xxx.jpg）
    if item.photo_path:
        # 去掉 "uploads/" 前缀，用 get_upload_dir 拼完整路径
        rel_path = item.photo_path
        if rel_path.startswith("uploads/"):
            rel_path = rel_path[len("uploads/"):]
        full_path = os.path.join(get_upload_dir(), rel_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    db.delete(item)
    db.commit()
    return {"message": "删除成功"}


class BatchUpdatePayload(BaseModel):
    ids: list[int]
    status: Optional[str] = None
    is_important: Optional[bool] = None


@router.post("/batch-update")
def batch_update_items(payload: BatchUpdatePayload, db: Session = Depends(get_db)):
    """批量更新物品状态或重要标记"""
    items = db.query(Item).filter(Item.id.in_(payload.ids)).all()
    if not items:
        raise HTTPException(404, "未找到任何物品")
    updated = 0
    for item in items:
        if payload.status is not None:
            item.status = payload.status
        if payload.is_important is not None:
            item.is_important = payload.is_important
        item.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated += 1
    db.commit()
    return {"message": f"更新成功，共 {updated} 条"}


@router.post("/batch-delete")
def batch_delete_items(payload: dict, db: Session = Depends(get_db)):
    """批量删除物品"""
    ids: list = payload.get("ids", [])
    if not ids:
        raise HTTPException(400, "未提供要删除的物品ID")
    items = db.query(Item).filter(Item.id.in_(ids)).all()
    # 删除关联图片文件
    for item in items:
        if item.photo_path:
            rel_path = item.photo_path
            if rel_path.startswith("uploads/"):
                rel_path = rel_path[len("uploads/"):]
            full_path = os.path.join(get_upload_dir(), rel_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        db.delete(item)
    db.commit()
    return {"message": f"删除成功，共 {len(items)} 条"}


@router.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    """上传物品照片"""
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
        raise HTTPException(400, "仅支持图片文件（jpg/png/gif/webp/bmp）")
    # 限制 5MB
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "图片大小不能超过 5MB")
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    save_path = os.path.join(UPLOAD_DIR, filename)
    with open(save_path, "wb") as f:
        f.write(content)
    # 返回相对于 uploads 根目录的路径（前端用 '/' + path 拼出 /uploads/items/xxx.jpg）
    return {"path": f"uploads/items/{filename}"}


@router.delete("/photo")
def delete_photo(path: str, db: Session = Depends(get_db)):
    """删除物品照片"""
    # 从所有物品中清除该图片引用
    items = db.query(Item).filter(Item.photo_path == path).all()
    for item in items:
        item.photo_path = ""
        item.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    # 删除文件（path 格式: uploads/items/xxx.jpg）
    rel_path = path
    if rel_path.startswith("uploads/"):
        rel_path = rel_path[len("uploads/"):]
    full_path = os.path.join(get_upload_dir(), rel_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    return {"message": "照片已删除"}


@router.get("/export/json")
def export_items(db: Session = Depends(get_db)):
    """导出全部物品为 JSON"""
    items = db.query(Item).order_by(desc(Item.updated_at)).all()
    data = [_item_to_dict(i) for i in items]
    return {"items": data, "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


@router.post("/import/json")
def import_items(data: dict, db: Session = Depends(get_db)):
    """导入物品 JSON（mode: merge 合并/overwrite 覆盖）"""
    mode = data.get("mode", "merge")
    items_data = data.get("items", [])
    if not items_data:
        raise HTTPException(400, "无有效数据")

    imported = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if mode == "overwrite":
        # 清空旧数据
        db.query(Item).delete()
        db.commit()

    for item_data in items_data:
        if not item_data.get("name"):
            continue
        # 清理不含 ORM 字段的 key
        clean = {k: v for k, v in item_data.items()
                 if k in ItemCreate.model_fields}
        if mode == "merge":
            # 按 id 或 name+serial_number 去重
            existing = None
            if item_data.get("id"):
                existing = db.query(Item).filter(Item.id == item_data["id"]).first()
            if not existing and item_data.get("serial_number"):
                existing = db.query(Item).filter(
                    Item.serial_number == item_data["serial_number"],
                    Item.name == item_data["name"],
                ).first()
            if existing:
                for k, v in clean.items():
                    setattr(existing, k, v)
                existing.updated_at = now
            else:
                clean.pop("id", None)
                new_item = Item(**clean, created_at=now, updated_at=now)
                db.add(new_item)
        else:
            clean.pop("id", None)
            new_item = Item(**clean, created_at=now, updated_at=now)
            db.add(new_item)
        imported += 1

    db.commit()
    return {"imported": imported, "mode": mode, "message": f"导入完成：{imported} 条物品"}
