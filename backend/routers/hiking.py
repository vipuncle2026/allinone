"""徒步模块 API 路由"""
import io
import os
import json
import shutil
from datetime import date, datetime
from typing import Optional
from sqlalchemy import extract

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func
from urllib.parse import quote

from database import get_db, get_upload_dir, get_data_dir
from models.hiking import HikingActivity
from services.gpx_parser import parse_gpx
from services.fit_parser import parse_fit
from services.tcx_parser import parse_tcx
from services.upload_utils import safe_upload_path, safe_remove

router = APIRouter(prefix="/api/hiking", tags=["徒步"])

UPLOAD_DIR = get_upload_dir("hiking")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── Pydantic Schemas ────────────────────────────────────────────

class ActivityCreate(BaseModel):
    title: str
    date: date
    start_time: Optional[str] = None   # 接受任意字符串，自行转换
    end_time: Optional[str] = None
    distance_km: Optional[float] = None
    duration_sec: Optional[int] = None
    elevation_gain: Optional[float] = None
    elevation_loss: Optional[float] = None
    max_elevation: Optional[float] = None
    min_elevation: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    max_speed_kmh: Optional[float] = None
    pace_min_km: Optional[float] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    calories: Optional[float] = None
    avg_cadence: Optional[int] = None
    max_cadence: Optional[int] = None
    steps: Optional[int] = None
    trail_name: Optional[str] = None
    difficulty: Optional[str] = None
    weather: Optional[str] = None
    notes: Optional[str] = None
    file_type: Optional[str] = None
    file_path: Optional[str] = None
    track_json: Optional[str] = None

    def to_model_dict(self):
        """转换为模型可用的字典，处理 datetime 字段"""
        d = self.dict()
        for key in ("start_time", "end_time"):
            val = d.get(key)
            if val:
                try:
                    # 统一去掉 Z 后缀再解析
                    d[key] = datetime.fromisoformat(val.replace("Z", "+00:00").replace("+00:00", ""))
                except Exception:
                    d[key] = None
            else:
                d[key] = None
        return d


class ManualActivityCreate(BaseModel):
    """手动录入（无需文件）"""
    title: str
    date: date
    distance_km: Optional[float] = None
    duration_sec: Optional[int] = None
    elevation_gain: Optional[float] = None
    elevation_loss: Optional[float] = None
    max_elevation: Optional[float] = None
    min_elevation: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    max_speed_kmh: Optional[float] = None
    pace_min_km: Optional[float] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    calories: Optional[float] = None
    avg_cadence: Optional[int] = None
    max_cadence: Optional[int] = None
    steps: Optional[int] = None
    trail_name: Optional[str] = None
    difficulty: Optional[str] = None
    weather: Optional[str] = None
    notes: Optional[str] = None


# ─── 文件上传与解析 ────────────────────────────────────────────

# 文件上传安全配置
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

@router.post("/upload")
async def upload_activity_file(file: UploadFile = File(...)):
    """上传 GPX、FIT 或 TCX 文件，自动解析，返回预览数据（不入库）"""
    # 文件大小验证
    file.file.seek(0, 2)  # 跳到末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置到开头
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件大小超过限制（最大 50MB），当前: {file_size / 1024 / 1024:.1f}MB")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("gpx", "fit", "tcx"):
        raise HTTPException(400, "仅支持 .gpx / .fit / .tcx 文件")

    save_path = safe_upload_path(UPLOAD_DIR, ext)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        if ext == "gpx":
            data = parse_gpx(save_path)
        elif ext == "fit":
            data = parse_fit(save_path)
        else:
            data = parse_tcx(save_path)
    except Exception as e:
        safe_remove(save_path)
        raise HTTPException(422, f"文件解析失败：{e}")

    data["file_type"] = ext
    # 存储相对于 uploads 根目录的路径，便于跨环境迁移
    data["file_path"] = os.path.relpath(save_path, get_upload_dir())
    data["suggested_title"] = _suggest_title(data)

    # 把 track_points / chart_points 序列化存入 track_json
    track_pts = data.pop("track_points", [])
    chart_pts = data.pop("chart_points", [])
    track_payload = {}
    if track_pts:
        track_payload["map"] = track_pts
    if chart_pts:
        track_payload["chart"] = chart_pts
    data["track_json"] = json.dumps(track_payload, ensure_ascii=False) if track_payload else None

    # 计算配速（分钟/公里）
    dist = data.get("distance_km", 0)
    dur = data.get("duration_sec", 0)
    if dist and dist > 0 and dur and dur > 0:
        data["pace_min_km"] = round(dur / 60 / dist, 2)

    return data


def _suggest_title(data: dict) -> str:
    """根据解析数据自动生成标题建议"""
    dist = data.get("distance_km", 0)
    ts = data.get("start_time")
    prefix = "徒步"
    if dist:
        prefix = f"{dist}km 徒步"
    if ts:
        try:
            dt = datetime.fromisoformat(ts)
            return f"{dt.strftime('%m月%d日')} {prefix}"
        except Exception:
            pass
    return prefix


# ─── 活动 CRUD ────────────────────────────────────────────────

@router.post("/activities")
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)):
    """保存徒步活动（文件导入）"""
    act = HikingActivity(**payload.to_model_dict())
    db.add(act)
    db.commit()
    db.refresh(act)
    return act


@router.post("/activities/manual")
def create_manual_activity(payload: ManualActivityCreate, db: Session = Depends(get_db)):
    """手动录入徒步活动"""
    data = payload.dict()
    data["file_type"] = "manual"
    act = HikingActivity(**data)
    db.add(act)
    db.commit()
    db.refresh(act)
    return act


@router.get("/activities")
def list_activities(
    page: int = 1,
    limit: int = 20,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """徒步活动列表（分页）"""
    q = db.query(HikingActivity)
    if difficulty:
        q = q.filter(HikingActivity.difficulty == difficulty)
    total = q.count()
    items = (
        q.order_by(HikingActivity.date.desc())
         .offset((page - 1) * limit)
         .limit(limit)
         .all()
    )
    # 列表也动态计算步数
    result_items = []
    for act in items:
        d = {c.name: getattr(act, c.name) for c in act.__table__.columns}
        if d.get("steps") is None and d.get("avg_cadence") and d.get("duration_sec"):
            d["steps"] = round(d["avg_cadence"] * (d["duration_sec"] / 60))
        result_items.append(d)
    return {"total": total, "page": page, "limit": limit, "items": result_items}


@router.get("/activities/stats")
def get_stats(db: Session = Depends(get_db)):
    """徒步总览统计"""
    total = db.query(func.count(HikingActivity.id)).scalar()
    total_km = db.query(func.sum(HikingActivity.distance_km)).scalar() or 0
    total_sec = db.query(func.sum(HikingActivity.duration_sec)).scalar() or 0
    total_gain = db.query(func.sum(HikingActivity.elevation_gain)).scalar() or 0
    total_cal = db.query(func.sum(HikingActivity.calories)).scalar() or 0
    return {
        "total_activities": total,
        "total_km": round(total_km, 1),
        "total_hours": round(total_sec / 3600, 1),
        "total_elevation_gain": round(total_gain, 0),
        "total_calories": round(total_cal, 0),
    }


@router.get("/activities/achievements")
def get_achievements(db: Session = Depends(get_db)):
    """运动成就"""
    achievements = {}

    # 单次最长距离
    max_dist = (
        db.query(HikingActivity)
        .order_by(HikingActivity.distance_km.desc().nullslast())
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
        db.query(HikingActivity)
        .order_by(HikingActivity.duration_sec.desc().nullslast())
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

    # 10公里最快时间
    ten_km = (
        db.query(HikingActivity)
        .filter(HikingActivity.distance_km >= 10)
        .order_by(HikingActivity.duration_sec.asc().nullslast())
        .first()
    )
    if ten_km:
        # 计算该活动完成10公里的预估时间（返回秒）
        speed = ten_km.distance_km / (ten_km.duration_sec / 3600) if ten_km.duration_sec else 0
        if speed > 0:
            ten_km_time_sec = round(10 / speed * 3600)
            achievements["fastest_10km"] = {
                "value": ten_km_time_sec,
                "unit": "秒",
                "title": ten_km.title,
                "date": str(ten_km.date),
                "activity_id": ten_km.id,
                "note": f"基于「{ten_km.title}」({ten_km.distance_km}km)的配速推算",
            }

    # 最高海拔（优先用字段，没有则从 track_json 回填）
    highest = (
        db.query(HikingActivity)
        .order_by(HikingActivity.max_elevation.desc().nullslast())
        .first()
    )
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

    return achievements


@router.get("/activities/year-summary")
def year_summary(year: Optional[int] = None, db: Session = Depends(get_db)):
    """指定年份徒步年度总结（默认当年）"""
    if year is None:
        year = date.today().year

    q = db.query(HikingActivity).filter(
        extract('year', HikingActivity.date) == year
    )
    activities = q.order_by(HikingActivity.date.asc()).all()

    total_count = len(activities)
    total_km = sum(a.distance_km or 0 for a in activities)
    total_sec = sum(a.duration_sec or 0 for a in activities)
    total_gain = sum(a.elevation_gain or 0 for a in activities)
    total_calories = sum(a.calories or 0 for a in activities)
    total_steps = sum(a.steps or 0 for a in activities)

    # 最远一次
    best_dist = max(activities, key=lambda a: a.distance_km or 0, default=None)
    # 最快配速（pace_min_km 越小越快）
    fastest_pace = min(
        [a for a in activities if a.pace_min_km],
        key=lambda a: a.pace_min_km,
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
    # 最高海拔
    highest_alt = max(
        [a for a in activities if a.max_elevation],
        key=lambda a: a.max_elevation,
        default=None
    )

    # 月度里程分布
    monthly = {}
    for a in activities:
        m = a.date.month if hasattr(a.date, 'month') else int(str(a.date)[5:7])
        monthly[m] = monthly.get(m, 0) + (a.distance_km or 0)
    monthly_dist = [round(monthly.get(i, 0), 1) for i in range(1, 13)]

    # 月度次数
    monthly_cnt = {}
    for a in activities:
        m = a.date.month if hasattr(a.date, 'month') else int(str(a.date)[5:7])
        monthly_cnt[m] = monthly_cnt.get(m, 0) + 1
    monthly_count = [monthly_cnt.get(i, 0) for i in range(1, 13)]

    def fmt_act(a):
        if not a:
            return None
        return {
            "id": a.id,
            "title": a.title,
            "date": str(a.date),
            "distance_km": round(a.distance_km or 0, 1),
            "elevation_gain": round(a.elevation_gain or 0, 0),
            "max_elevation": round(a.max_elevation or 0, 0),
            "duration_sec": a.duration_sec or 0,
            "pace_min_km": round(a.pace_min_km or 0, 2),
            "avg_speed_kmh": round(a.avg_speed_kmh or 0, 1),
            "avg_heart_rate": a.avg_heart_rate,
            "steps": a.steps,
        }

    return {
        "year": year,
        "total_count": total_count,
        "total_km": round(total_km, 1),
        "total_hours": round(total_sec / 3600, 1),
        "total_gain": round(total_gain, 0),
        "total_calories": round(total_calories, 0),
        "total_steps": total_steps,
        "avg_km_per_hike": round(total_km / total_count, 1) if total_count else 0,
        "monthly_dist": monthly_dist,
        "monthly_count": monthly_count,
        "best_dist": fmt_act(best_dist),
        "best_pace": fmt_act(fastest_pace),
        "best_gain": fmt_act(best_gain),
        "best_duration": fmt_act(best_duration),
        "highest_alt": fmt_act(highest_alt),
    }


@router.get("/activities/{activity_id}")
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    """活动详情（含轨迹）"""
    act = db.query(HikingActivity).filter(HikingActivity.id == activity_id).first()
    if not act:
        raise HTTPException(404, "活动不存在")
    # 动态计算步数：如果 steps 为空且有步频数据，用 avg_cadence × duration_min
    d = {c.name: getattr(act, c.name) for c in act.__table__.columns}
    if d.get("steps") is None and d.get("avg_cadence") and d.get("duration_sec"):
        d["steps"] = round(d["avg_cadence"] * (d["duration_sec"] / 60))
    return d


@router.put("/activities/{activity_id}")
def update_activity(
    activity_id: int,
    payload: ActivityCreate,
    db: Session = Depends(get_db)
):
    act = db.query(HikingActivity).filter(HikingActivity.id == activity_id).first()
    if not act:
        raise HTTPException(404, "活动不存在")
    for k, v in payload.to_model_dict().items():
        if v is not None:
            setattr(act, k, v)
    db.commit()
    db.refresh(act)
    return act


@router.delete("/activities/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    act = db.query(HikingActivity).filter(HikingActivity.id == activity_id).first()
    if not act:
        raise HTTPException(404, "活动不存在")
    # 同步删除原始上传文件
    if act.file_path and os.path.isfile(act.file_path):
        try:
            os.remove(act.file_path)
        except Exception:
            pass
    db.delete(act)
    db.commit()
    return {"ok": True}


# ─── 导出 / 导入 ──────────────────────────────────────────────────

def _activity_to_dict(act: HikingActivity) -> dict:
    d = {}
    for c in HikingActivity.__table__.columns:
        v = getattr(act, c.name)
        if v is not None:
            if isinstance(v, (date, datetime)):
                d[c.name] = v.isoformat()
            else:
                d[c.name] = v
    return d


@router.get("/export/json")
def export_backup(db: Session = Depends(get_db)):
    """导出全部徒步活动为 JSON 备份"""
    activities = [_activity_to_dict(a) for a in db.query(HikingActivity).order_by(HikingActivity.id).all()]
    payload = {
        "version": "1.0",
        "module": "hiking",
        "exported_at": datetime.now().isoformat(),
        "activities": activities,
    }
    buf = io.StringIO()
    json.dump(payload, buf, ensure_ascii=False, indent=2)
    buf.seek(0)
    filename = f"hiking_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    """导出徒步活动为 CSV 文件"""
    import csv
    activities = db.query(HikingActivity).order_by(HikingActivity.date.desc()).all()
    headers = [
        "ID", "活动名称", "日期", "距离(km)", "时长(秒)", "均速(km/h)",
        "最大速度(km/h)", "爬升(m)", "下降(m)", "最高海拔(m)", "最低海拔(m)",
        "配速(min/km)", "平均心率", "最大心率", "热量(kcal)",
        "平均步频", "最大步频", "步数", "路线名称", "难度", "天气", "备注", "来源",
    ]
    rows = []
    for a in activities:
        rows.append([
            a.id, a.title, a.date, a.distance_km, a.duration_sec, a.avg_speed_kmh,
            a.max_speed_kmh, a.elevation_gain, a.elevation_loss, a.max_elevation, a.min_elevation,
            a.pace_min_km, a.avg_heart_rate, a.max_heart_rate, a.calories,
            a.avg_cadence, a.max_cadence, a.steps, a.trail_name, a.difficulty, a.weather, a.notes, a.file_type,
        ])
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    buf.seek(0)
    filename = f"hiking_activities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
