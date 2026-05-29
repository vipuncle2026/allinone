"""骑行模块 API 路由"""
import os
import io
import csv
import json
import shutil
import time
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import extract

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, get_upload_dir, get_data_dir
from models.cycling import CyclingActivity, Bike, BikeMaintenanceRecord
from services.gpx_parser import parse_gpx
from services.upload_utils import safe_upload_path, safe_remove
from services.fit_parser import parse_fit

router = APIRouter(prefix="/api/cycling", tags=["骑行"])

UPLOAD_DIR = get_upload_dir("cycling")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 上传限流：每分钟最多 10 次
_upload_rate_limit: dict[str, list[float]] = {}


def _check_upload_rate(client_ip: str) -> bool:
    """检查上传频率，返回 True 表示允许"""
    now = time.time()
    if client_ip not in _upload_rate_limit:
        _upload_rate_limit[client_ip] = []
    # 清理 1 分钟前的记录
    _upload_rate_limit[client_ip] = [t for t in _upload_rate_limit[client_ip] if now - t < 60]
    if len(_upload_rate_limit[client_ip]) >= 10:
        return False
    _upload_rate_limit[client_ip].append(now)
    return True


# ─── Pydantic Schemas ────────────────────────────────────────────

class ActivityCreate(BaseModel):
    title: str
    date: date
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    distance_km: Optional[float] = None
    duration_sec: Optional[int] = None
    elevation_gain: Optional[float] = None
    elevation_loss: Optional[float] = None
    max_elevation: Optional[float] = None
    min_elevation: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    max_speed_kmh: Optional[float] = None
    avg_power_w: Optional[float] = None
    max_power_w: Optional[float] = None
    normalized_power: Optional[float] = None
    tss: Optional[float] = None
    ftp: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    avg_cadence: Optional[int] = None
    max_cadence: Optional[int] = None
    calories: Optional[int] = None
    route_type: Optional[str] = None
    weather: Optional[str] = None
    notes: Optional[str] = None
    file_type: Optional[str] = None
    file_path: Optional[str] = None
    track_json: Optional[str] = None
    bike_id: Optional[int] = None


class BikeCreate(BaseModel):
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    weight_kg: Optional[float] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None
    notes: Optional[str] = None


class MaintenanceCreate(BaseModel):
    bike_id: int
    component: str
    action: str
    date: date
    cost: Optional[float] = None
    mileage_at: Optional[float] = None
    notes: Optional[str] = None


# ─── 文件上传与解析 ────────────────────────────────────────────

# 文件上传安全配置
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

@router.post("/upload")
async def upload_activity_file(request: Request, file: UploadFile = File(...)):
    """上传 GPX 或 FIT 文件，自动解析，返回预览数据（不入库）"""
    # 限流检查
    client_ip = request.client.host if request.client else "unknown"
    if not _check_upload_rate(client_ip):
        raise HTTPException(429, "上传过于频繁，请 1 分钟后再试")

    # 文件大小验证
    file.file.seek(0, 2)  # 跳到末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置到开头
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件大小超过限制（最大 50MB），当前: {file_size / 1024 / 1024:.1f}MB")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("gpx", "fit"):
        raise HTTPException(400, "仅支持 .gpx 或 .fit 文件")

    save_path = safe_upload_path(UPLOAD_DIR, ext)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        if ext == "gpx":
            data = parse_gpx(save_path)
        else:
            data = parse_fit(save_path)
    except Exception as e:
        safe_remove(save_path)
        raise HTTPException(422, f"文件解析失败：{e}")

    data["file_type"] = ext
    # 存储相对于 uploads 根目录的路径，便于跨环境迁移
    data["file_path"] = os.path.relpath(save_path, get_upload_dir())
    data["suggested_title"] = _suggest_title(data)
    return data


def _suggest_title(data: dict) -> str:
    """根据解析数据自动生成标题建议"""
    dist = data.get("distance_km", 0)
    ts = data.get("start_time")
    prefix = "骑行"
    if dist:
        prefix = f"{dist}km 骑行"
    if ts:
        try:
            dt = datetime.fromisoformat(ts)
            return f"{dt.strftime('%m月%d日')} {prefix}"
        except Exception:
            pass
    return prefix


# ─── 活动 CRUD ────────────────────────────────────────────────

def _recalc_tss(np_power: Optional[float], duration_sec: Optional[int], ftp: int) -> Optional[float]:
    """用指定 FTP 重新计算 TSS"""
    if not np_power or not duration_sec:
        return None
    intensity_factor = np_power / ftp
    return round((duration_sec * np_power * intensity_factor) / (ftp * 3600) * 100, 1)


@router.post("/activities")
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)):
    """保存骑行活动"""
    data = payload.dict()

    # 若传入 ftp，用它重新计算 TSS（覆盖解析时的默认值）
    ftp_val = data.get("ftp")
    if ftp_val and ftp_val != 200:
        np_power = data.get("normalized_power") or data.get("avg_power_w")
        duration_sec = data.get("duration_sec")
        data["tss"] = _recalc_tss(np_power, duration_sec, ftp_val)

    act = CyclingActivity(**data)
    db.add(act)
    db.commit()
    db.refresh(act)
    # 更新车辆累计里程
    if act.bike_id and act.distance_km:
        bike = db.query(Bike).filter(Bike.id == act.bike_id).first()
        if bike:
            bike.total_km = (bike.total_km or 0) + act.distance_km
            db.commit()
    return act


@router.get("/activities")
def list_activities(
    page: int = 1,
    limit: int = 20,
    bike_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """骑行活动列表（分页）"""
    q = db.query(CyclingActivity)
    if bike_id:
        q = q.filter(CyclingActivity.bike_id == bike_id)
    total = q.count()
    items = (
        q.order_by(CyclingActivity.date.desc())
         .offset((page - 1) * limit)
         .limit(limit)
         .all()
    )
    return {"total": total, "page": page, "limit": limit, "items": items}


@router.get("/activities/stats")
def get_stats(db: Session = Depends(get_db)):
    """骑行总览统计"""
    total = db.query(func.count(CyclingActivity.id)).scalar()
    total_km = db.query(func.sum(CyclingActivity.distance_km)).scalar() or 0
    total_sec = db.query(func.sum(CyclingActivity.duration_sec)).scalar() or 0
    total_gain = db.query(func.sum(CyclingActivity.elevation_gain)).scalar() or 0
    return {
        "total_activities": total,
        "total_km": round(total_km, 1),
        "total_hours": round(total_sec / 3600, 1),
        "total_elevation_gain": round(total_gain, 0),
    }


@router.get("/activities/achievements")
def get_achievements(db: Session = Depends(get_db)):
    """骑行成就"""
    achievements = {}

    # 单次最长距离
    max_dist = (
        db.query(CyclingActivity)
        .order_by(CyclingActivity.distance_km.desc().nullslast())
        .first()
    )
    if max_dist and max_dist.distance_km:
        achievements["longest_distance"] = {
            "value": max_dist.distance_km,
            "unit": "km",
            "title": max_dist.title,
            "date": str(max_dist.date),
            "activity_id": max_dist.id,
        }

    # 单次最长时间
    longest = (
        db.query(CyclingActivity)
        .order_by(CyclingActivity.duration_sec.desc().nullslast())
        .first()
    )
    if longest and longest.duration_sec:
        achievements["longest_duration"] = {
            "value": longest.duration_sec,
            "unit": "秒",
            "title": longest.title,
            "date": str(longest.date),
            "activity_id": longest.id,
        }

    # 最高海拔（优先用字段，没有则从 track_json 回填）
    highest = (
        db.query(CyclingActivity)
        .order_by(CyclingActivity.max_elevation.desc().nullslast())
        .first()
    )
    # 如果没有字段数据，尝试从 track_json 中找
    if highest and not highest.max_elevation and highest.track_json:
        import json as _json
        try:
            pts = _json.loads(highest.track_json)
            eles = [p.get("ele") for p in pts if p.get("ele") is not None]
            if eles:
                highest.max_elevation = round(max(eles), 1)
        except Exception:
            pass
    if highest and highest.max_elevation:
        achievements["highest_elevation"] = {
            "value": highest.max_elevation,
            "unit": "m",
            "title": highest.title,
            "date": str(highest.date),
            "activity_id": highest.id,
        }

    # 最高速度
    fastest = (
        db.query(CyclingActivity)
        .order_by(CyclingActivity.max_speed_kmh.desc().nullslast())
        .first()
    )
    if fastest and fastest.max_speed_kmh:
        achievements["max_speed"] = {
            "value": fastest.max_speed_kmh,
            "unit": "km/h",
            "title": fastest.title,
            "date": str(fastest.date),
            "activity_id": fastest.id,
        }

    return achievements


@router.get("/activities/year-summary")
def year_summary(year: Optional[int] = None, db: Session = Depends(get_db)):
    """指定年份骑行年度总结（默认当年）"""
    if year is None:
        year = date.today().year

    q = db.query(CyclingActivity).filter(
        extract('year', CyclingActivity.date) == year
    )
    activities = q.order_by(CyclingActivity.date.asc()).all()

    total_count = len(activities)
    total_km = sum(a.distance_km or 0 for a in activities)
    total_sec = sum(a.duration_sec or 0 for a in activities)
    total_gain = sum(a.elevation_gain or 0 for a in activities)
    total_calories = sum(a.calories or 0 for a in activities)

    # 最远一次
    best_dist = max(activities, key=lambda a: a.distance_km or 0, default=None)
    # 最快均速
    best_speed = max(
        [a for a in activities if a.avg_speed_kmh],
        key=lambda a: a.avg_speed_kmh,
        default=None
    )
    # 最大爬升
    best_gain = max(
        [a for a in activities if a.elevation_gain],
        key=lambda a: a.elevation_gain,
        default=None
    )
    # 最长时长
    best_duration = max(
        [a for a in activities if a.duration_sec],
        key=lambda a: a.duration_sec,
        default=None
    )

    # 月度里程分布（用于迷你热力条）
    monthly = {}
    for a in activities:
        m = a.date.month if hasattr(a.date, 'month') else int(str(a.date)[5:7])
        monthly[m] = monthly.get(m, 0) + (a.distance_km or 0)
    monthly_dist = [round(monthly.get(i, 0), 1) for i in range(1, 13)]

    def fmt_act(a):
        if not a:
            return None
        return {
            "id": a.id,
            "title": a.title,
            "date": str(a.date),
            "distance_km": round(a.distance_km or 0, 1),
            "avg_speed_kmh": round(a.avg_speed_kmh or 0, 1),
            "elevation_gain": round(a.elevation_gain or 0, 0),
            "duration_sec": a.duration_sec or 0,
        }

    return {
        "year": year,
        "total_count": total_count,
        "total_km": round(total_km, 1),
        "total_hours": round(total_sec / 3600, 1),
        "total_gain": round(total_gain, 0),
        "total_calories": total_calories,
        "avg_km_per_ride": round(total_km / total_count, 1) if total_count else 0,
        "monthly_dist": monthly_dist,
        "best_dist": fmt_act(best_dist),
        "best_speed": fmt_act(best_speed),
        "best_gain": fmt_act(best_gain),
        "best_duration": fmt_act(best_duration),
    }


@router.get("/activities/{activity_id}")
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    """活动详情（含轨迹）"""
    act = db.query(CyclingActivity).filter(CyclingActivity.id == activity_id).first()
    if not act:
        raise HTTPException(404, "活动不存在")
    return act


@router.put("/activities/{activity_id}")
def update_activity(
    activity_id: int,
    payload: ActivityCreate,
    db: Session = Depends(get_db)
):
    act = db.query(CyclingActivity).filter(CyclingActivity.id == activity_id).first()
    if not act:
        raise HTTPException(404, "活动不存在")

    data = payload.dict(exclude_unset=True)
    # 若传入 ftp，重新计算 TSS
    ftp_val = data.pop("ftp", None)
    if ftp_val:
        np_power = act.normalized_power or act.avg_power_w
        duration_sec = act.duration_sec
        act.tss = _recalc_tss(np_power, duration_sec, ftp_val) or act.tss
        act.ftp = ftp_val

    for k, v in data.items():
        setattr(act, k, v)
    db.commit()
    db.refresh(act)
    return act


@router.delete("/activities/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    act = db.query(CyclingActivity).filter(CyclingActivity.id == activity_id).first()
    if not act:
        raise HTTPException(404, "活动不存在")
    # 同步删除原始上传文件
    if act.file_path and os.path.isfile(act.file_path):
        try:
            os.remove(act.file_path)
        except Exception:
            pass  # 文件删除失败不阻断记录删除
    db.delete(act)
    db.commit()
    return {"ok": True}


# ─── 车辆 CRUD ────────────────────────────────────────────────

@router.get("/bikes")
def list_bikes(db: Session = Depends(get_db)):
    return db.query(Bike).order_by(Bike.id).all()


@router.post("/bikes")
def create_bike(payload: BikeCreate, db: Session = Depends(get_db)):
    bike = Bike(**payload.dict())
    db.add(bike)
    db.commit()
    db.refresh(bike)
    return bike


@router.put("/bikes/{bike_id}")
def update_bike(bike_id: int, payload: BikeCreate, db: Session = Depends(get_db)):
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    if not bike:
        raise HTTPException(404, "车辆不存在")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(bike, k, v)
    db.commit()
    db.refresh(bike)
    return bike


@router.delete("/bikes/{bike_id}")
def delete_bike(bike_id: int, db: Session = Depends(get_db)):
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    if not bike:
        raise HTTPException(404, "车辆不存在")
    db.delete(bike)
    db.commit()
    return {"ok": True}


# ─── 维护记录 CRUD ────────────────────────────────────────────

@router.get("/bikes/{bike_id}/maintenance")
def list_maintenance(bike_id: int, db: Session = Depends(get_db)):
    return (
        db.query(BikeMaintenanceRecord)
          .filter(BikeMaintenanceRecord.bike_id == bike_id)
          .order_by(BikeMaintenanceRecord.date.desc())
          .all()
    )


@router.post("/maintenance")
def create_maintenance(payload: MaintenanceCreate, db: Session = Depends(get_db)):
    record = BikeMaintenanceRecord(**payload.dict())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/maintenance/{record_id}")
def delete_maintenance(record_id: int, db: Session = Depends(get_db)):
    r = db.query(BikeMaintenanceRecord).filter(BikeMaintenanceRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "记录不存在")
    db.delete(r)
    db.commit()
    return {"ok": True}


# ─── 导出导入 ────────────────────────────────────────────────

def _activity_to_dict(act: CyclingActivity) -> dict:
    """将活动 ORM 对象转为可序列化的 dict"""
    d = {c.name: getattr(act, c.name) for c in act.__table__.columns}
    # 处理特殊类型
    for k, v in d.items():
        if isinstance(v, (date, datetime)):
            d[k] = v.isoformat()
        elif v is None:
            d[k] = None
    # 导出时去除轨迹数据（太大且可重新导入文件解析）
    d.pop("track_json", None)
    return d


def _bike_to_dict(bike: Bike) -> dict:
    d = {c.name: getattr(bike, c.name) for c in bike.__table__.columns}
    for k, v in d.items():
        if isinstance(v, (date, datetime)):
            d[k] = v.isoformat()
        elif v is None:
            d[k] = None
    return d


def _maint_to_dict(r: BikeMaintenanceRecord) -> dict:
    d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    for k, v in d.items():
        if isinstance(v, (date, datetime)):
            d[k] = v.isoformat()
        elif v is None:
            d[k] = None
    return d


@router.get("/export/backup")
def export_backup(db: Session = Depends(get_db)):
    """导出骑行数据为 JSON 备份（活动 + 车辆 + 维护记录）"""
    activities = [_activity_to_dict(a) for a in db.query(CyclingActivity).order_by(CyclingActivity.id).all()]
    bikes = [_bike_to_dict(b) for b in db.query(Bike).order_by(Bike.id).all()]
    maintenance = [_maint_to_dict(r) for r in db.query(BikeMaintenanceRecord).order_by(BikeMaintenanceRecord.id).all()]

    payload = {
        "version": "1.0",
        "module": "cycling",
        "exported_at": datetime.now().isoformat(),
        "activities": activities,
        "bikes": bikes,
        "maintenance": maintenance,
    }

    buf = io.StringIO()
    json.dump(payload, buf, ensure_ascii=False, indent=2)
    buf.seek(0)

    filename = f"cycling_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/import/backup")
def import_backup(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """从 JSON 备份导入骑行数据（合并模式：按 ID 跳过已存在的）"""
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext != "json":
        raise HTTPException(400, "仅支持 .json 备份文件")

    content = file.file.read().decode("utf-8")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "JSON 格式错误")

    if data.get("module") != "cycling":
        raise HTTPException(400, "这不是骑行模块的备份文件")

    stats = {"bikes": 0, "activities": 0, "maintenance": 0}

    # 导入车辆
    for item in data.get("bikes", []):
        exists = db.query(Bike).filter(Bike.id == item.get("id")).first()
        if exists:
            continue
        bike = Bike(**{k: v for k, v in item.items() if k in Bike.__table__.columns and v is not None})
        db.add(bike)
        stats["bikes"] += 1

    db.flush()

    # 导入活动
    for item in data.get("activities", []):
        exists = db.query(CyclingActivity).filter(CyclingActivity.id == item.get("id")).first()
        if exists:
            continue
        act = CyclingActivity(**{k: v for k, v in item.items() if k in CyclingActivity.__table__.columns and v is not None})
        db.add(act)
        stats["activities"] += 1

    db.flush()

    # 导入维护记录
    for item in data.get("maintenance", []):
        exists = db.query(BikeMaintenanceRecord).filter(BikeMaintenanceRecord.id == item.get("id")).first()
        if exists:
            continue
        rec = BikeMaintenanceRecord(**{k: v for k, v in item.items() if k in BikeMaintenanceRecord.__table__.columns and v is not None})
        db.add(rec)
        stats["maintenance"] += 1

    db.commit()
    return {"ok": True, "imported": stats}


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    """导出骑行活动为 CSV 文件"""
    activities = db.query(CyclingActivity).order_by(CyclingActivity.date.desc()).all()

    headers = [
        "ID", "活动名称", "日期", "距离(km)", "时长(秒)", "均速(km/h)",
        "最大速度(km/h)", "爬升(m)", "下降(m)", "最高海拔(m)", "最低海拔(m)",
        "平均心率", "最大心率", "平均踏频", "最大踏频",
        "平均功率(W)", "最大功率(W)", "NP(W)", "TSS",
        "路线类型", "天气", "车辆ID", "文件类型", "备注"
    ]

    fields = [
        "id", "title", "date", "distance_km", "duration_sec", "avg_speed_kmh",
        "max_speed_kmh", "elevation_gain", "elevation_loss", "max_elevation", "min_elevation",
        "avg_heart_rate", "max_heart_rate", "avg_cadence", "max_cadence",
        "avg_power_w", "max_power_w", "normalized_power", "tss",
        "route_type", "weather", "bike_id", "file_type", "notes"
    ]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)

    for act in activities:
        row = []
        for f in fields:
            val = getattr(act, f, None)
            if isinstance(val, (date, datetime)):
                val = val.isoformat()
            elif val is None:
                val = ""
            row.append(val)
        writer.writerow(row)

    buf.seek(0)
    filename = f"cycling_activities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),  # BOM for Excel
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
