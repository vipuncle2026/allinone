"""iGPSPORT 云端同步服务

通过 iGPSPORT Web 端私有接口拉取骑行活动并导入本地库：
1. 账号密码登录换取 JWT（appId=igpsport-web）
2. 分页拉取活动列表 queryMyActivity
3. 按 rideId 获取 FIT 下载地址并下载
4. 复用 fit_parser 解析，写入 cycling_activities
5. 以 external_id(=rideId) 去重，可反复执行

⚠️ 该接口非官方公开 API，若上游调整可能失效；失败时仅记录错误，不影响其他功能。
"""
import asyncio
import json
import os
import time
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from database import get_data_dir, get_upload_dir
from models.cycling import CyclingActivity
from models.settings import UserSetting
from services.fit_parser import parse_fit

IGP_HOST = "https://prod.zh.igpsport.com"
ACT_BASE = f"{IGP_HOST}/service/web-gateway/web-analyze/activity"
LOGIN_URL = f"{IGP_HOST}/service/auth/account/login"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

CRED_KEY = "igpsport.credentials"
STATE_KEY = "igpsport.sync_state"

# 运行状态（进程内，供前端轮询）
SYNC_STATE = {
    "running": False,
    "phase": "idle",
    "total": 0,
    "done": 0,
    "imported": 0,
    "skipped": 0,
    "merged": 0,
    "failed": 0,
    "message": "",
    "started_at": None,
    "finished_at": None,
}


class IgpsportError(Exception):
    """iGPSPORT 接口异常"""


# ── 凭据加密（Fernet，密钥存放在数据目录，随备份一起走）────────────

def _fernet():
    from cryptography.fernet import Fernet

    key_path = os.path.join(get_data_dir(), ".igpsport.key")
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        try:
            os.chmod(key_path, 0o600)
        except Exception:
            pass
    else:
        with open(key_path, "rb") as f:
            key = f.read().strip()
    return Fernet(key)


def _get_setting(db: Session, key: str) -> Optional[dict]:
    row = db.query(UserSetting).filter(UserSetting.key == key).first()
    if not row or not row.value:
        return None
    try:
        return json.loads(row.value)
    except Exception:
        return None


def _set_setting(db: Session, key: str, value: dict):
    row = db.query(UserSetting).filter(UserSetting.key == key).first()
    payload = json.dumps(value, ensure_ascii=False)
    now = datetime.now()
    if row:
        row.value = payload
        row.updated_at = now
    else:
        db.add(UserSetting(key=key, value=payload, updated_at=now))
    db.commit()


def save_credentials(db: Session, username: str, password: str):
    """加密保存账号密码"""
    enc = _fernet().encrypt(password.encode("utf-8")).decode("ascii")
    _set_setting(db, CRED_KEY, {"username": username, "password": enc})


def load_credentials(db: Session) -> Optional[dict]:
    data = _get_setting(db, CRED_KEY)
    if not data:
        return None
    try:
        pwd = _fernet().decrypt(data["password"].encode("ascii")).decode("utf-8")
    except Exception:
        return None
    return {"username": data.get("username"), "password": pwd}


def clear_credentials(db: Session):
    row = db.query(UserSetting).filter(UserSetting.key == CRED_KEY).first()
    if row:
        db.delete(row)
        db.commit()


def save_state(db: Session, state: dict):
    _set_setting(db, STATE_KEY, state)


def load_state(db: Session) -> dict:
    return _get_setting(db, STATE_KEY) or {}


# ── HTTP 层 ───────────────────────────────────────────────────

def _unwrap(resp: httpx.Response):
    """解包 {code, message, data} 信封，异常抛 IgpsportError"""
    try:
        body = resp.json()
    except Exception:
        raise IgpsportError(f"HTTP {resp.status_code}：返回非 JSON（{resp.text[:80]}）")
    if resp.status_code != 200 or body.get("code") not in (0, None):
        msg = body.get("message") or body.get("data") or f"HTTP {resp.status_code}"
        raise IgpsportError(str(msg))
    return body.get("data")


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def login(client: httpx.AsyncClient, username: str, password: str) -> str:
    """账号密码登录，返回 access_token"""
    resp = await client.post(
        LOGIN_URL,
        json={"appId": "igpsport-web", "username": username, "password": password},
    )
    data = _unwrap(resp)
    token = data.get("access_token") if isinstance(data, dict) else None
    if not token:
        raise IgpsportError("登录成功但未返回 access_token")
    return token


async def list_activities(client: httpx.AsyncClient, token: str, page_no: int, page_size: int = 20) -> dict:
    """拉取活动列表：{totalRows, rows:[{rideId,title,startTime,rideDistance,...}]}"""
    resp = await client.get(
        f"{ACT_BASE}/queryMyActivity",
        params={
            "reqType": 1,
            "sportType": 0,
            "pageNo": page_no,
            "pageSize": page_size,
            "sort": 1,
            "title": "",
        },
        headers=_auth(token),
    )
    data = _unwrap(resp)
    return data if isinstance(data, dict) else {"totalRows": 0, "rows": []}


async def get_download_url(client: httpx.AsyncClient, token: str, ride_id) -> str:
    resp = await client.get(f"{ACT_BASE}/getDownloadUrl/{ride_id}", headers=_auth(token))
    data = _unwrap(resp)
    if isinstance(data, str) and data.startswith("http"):
        return data
    if isinstance(data, dict):
        for k in ("url", "downloadUrl", "fileUrl"):
            if data.get(k):
                return data[k]
    raise IgpsportError("未获取到下载地址")


async def download_fit(client: httpx.AsyncClient, url: str) -> bytes:
    resp = await client.get(url)
    if resp.status_code != 200:
        raise IgpsportError(f"下载失败 HTTP {resp.status_code}")
    if len(resp.content) < 100:
        raise IgpsportError("下载内容异常（过小）")
    return resp.content


# ── 入库 ─────────────────────────────────────────────────────

def _already_imported(db: Session, ride_id) -> bool:
    return (
        db.query(CyclingActivity.id)
        .filter(
            CyclingActivity.external_source == "igpsport",
            CyclingActivity.external_id == str(ride_id),
        )
        .first()
        is not None
    )


# 判定「同一次骑行」的容差
TWIN_DIST_TOL = 0.05   # km
TWIN_DUR_TOL = 5       # 秒


def _find_manual_twin(db: Session, date_val, distance_km, duration_sec, exclude_id=None):
    """查找同一活动的手动导入记录（无 external_id）。

    手动导入的记录没有 rideId，若只按 rideId 去重会与自动同步重复；
    这里按「同日期 + 距离接近 + 时长接近」判定为同一次骑行。
    """
    if not distance_km:
        return None
    rows = (
        db.query(CyclingActivity)
        .filter(
            CyclingActivity.date == date_val,
            CyclingActivity.external_id.is_(None),
        )
        .all()
    )
    best, best_diff = None, 1e9
    for row in rows:
        if exclude_id is not None and row.id == exclude_id:
            continue
        if row.distance_km is None:
            continue
        diff = abs(row.distance_km - distance_km)
        if diff > TWIN_DIST_TOL:
            continue
        if duration_sec and row.duration_sec and abs(row.duration_sec - duration_sec) > TWIN_DUR_TOL:
            continue
        if diff < best_diff:
            best, best_diff = row, diff
    return best


def _adopt(db: Session, target: CyclingActivity, ride_id, parsed: dict) -> CyclingActivity:
    """把手动记录认领为 iGPSPORT 记录：打上 rideId，仅补齐原记录为空的字段"""
    target.external_source = "igpsport"
    target.external_id = str(ride_id)
    for field in (
        "elevation_gain", "elevation_loss", "max_elevation", "min_elevation",
        "avg_speed_kmh", "max_speed_kmh", "avg_power_w", "max_power_w",
        "normalized_power", "tss", "avg_heart_rate", "max_heart_rate",
        "avg_cadence", "max_cadence", "calories",
    ):
        if getattr(target, field, None) is None and parsed.get(field) is not None:
            setattr(target, field, parsed.get(field))
    if not target.track_json and parsed.get("track_json"):
        target.track_json = parsed.get("track_json")
        if not target.file_path:
            target.file_type = "fit"
    db.commit()
    db.refresh(target)
    return target


def _to_dt(value):
    """把 ISO 字符串（parse_fit 返回 str）转成 datetime，供 SQLite DateTime 列使用"""
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except Exception:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    continue
    return None


def _suggest_title(parsed: dict) -> str:
    """与手动导入一致的命名：MM月DD日 XX.XXkm 骑行"""
    from services.upload_utils import suggest_title
    return suggest_title(parsed)


def _upsert_activity(db: Session, ride_id, item: dict, parsed: dict, rel_path: str):
    """写入活动：若已存在同一活动的手动记录则认领它，否则新建。

    返回 (activity, adopted) —— adopted=True 表示合并到已有手动记录。
    """
    start_dt = _to_dt(parsed.get("start_time"))
    end_dt = _to_dt(parsed.get("end_time"))
    date_val = start_dt.date() if start_dt else datetime.now().date()

    # 同名活动的手动记录：认领而不是重复插入
    twin = _find_manual_twin(db, date_val, parsed.get("distance_km"), parsed.get("duration_sec"))
    if twin:
        return _adopt(db, twin, ride_id, parsed), True

    # 命名与手动导入统一（不再使用 iGPSPORT 的「户外骑行」等标题）
    title = _suggest_title(parsed)
    if not title or title == "骑行":
        title = (item.get("title") or "").strip() or f"{date_val.strftime('%m月%d日')} 骑行"

    act = CyclingActivity(
        title=title[:200],
        date=date_val,
        start_time=start_dt,
        end_time=end_dt,
        distance_km=parsed.get("distance_km"),
        duration_sec=parsed.get("duration_sec"),
        elevation_gain=parsed.get("elevation_gain"),
        elevation_loss=parsed.get("elevation_loss"),
        max_elevation=parsed.get("max_elevation"),
        min_elevation=parsed.get("min_elevation"),
        avg_speed_kmh=parsed.get("avg_speed_kmh"),
        max_speed_kmh=parsed.get("max_speed_kmh"),
        avg_power_w=parsed.get("avg_power_w"),
        max_power_w=parsed.get("max_power_w"),
        normalized_power=parsed.get("normalized_power"),
        tss=parsed.get("tss"),
        avg_heart_rate=parsed.get("avg_heart_rate"),
        max_heart_rate=parsed.get("max_heart_rate"),
        avg_cadence=parsed.get("avg_cadence"),
        max_cadence=parsed.get("max_cadence"),
        calories=parsed.get("calories"),
        track_json=parsed.get("track_json"),
        file_path=rel_path,
        file_type="fit",
        external_source="igpsport",
        external_id=str(ride_id),
    )
    db.add(act)
    db.commit()
    db.refresh(act)
    return act, False


def dedupe_existing(db: Session) -> dict:
    """整理历史重复：自动同步产生的记录若与手动导入的是同一活动，
    则把 rideId 认领到手动记录上并删除自动记录（含其 FIT 文件）。"""
    from services.upload_utils import safe_remove_upload

    autos = (
        db.query(CyclingActivity)
        .filter(CyclingActivity.external_source == "igpsport")
        .all()
    )
    merged = kept = 0
    for a in autos:
        twin = _find_manual_twin(
            db, a.date, a.distance_km, a.duration_sec, exclude_id=a.id
        )
        if not twin:
            kept += 1
            continue
        _adopt(db, twin, a.external_id, {})
        file_path = a.file_path
        db.delete(a)
        db.commit()
        if file_path:
            safe_remove_upload(file_path)
        merged += 1
    return {"merged": merged, "kept": kept}


# ── 同步主流程 ────────────────────────────────────────────────

def _reset_state():
    SYNC_STATE.update(
        running=True,
        phase="login",
        total=0,
        done=0,
        imported=0,
        skipped=0,
        merged=0,
        failed=0,
        message="正在登录 iGPSPORT…",
        started_at=datetime.now().isoformat(timespec="seconds"),
        finished_at=None,
    )


async def run_sync(db: Session, page_size: int = 20, delay: float = 0.4) -> dict:
    """执行一次全量同步（增量：仅导入未入库的 rideId）"""
    creds = load_credentials(db)
    if not creds:
        raise IgpsportError("尚未配置 iGPSPORT 账号")

    if SYNC_STATE["running"]:
        return {"ok": False, "message": "同步正在进行中"}

    _reset_state()
    cycling_dir = get_upload_dir("cycling")
    os.makedirs(cycling_dir, exist_ok=True)
    result = {"ok": True, "imported": 0, "skipped": 0, "failed": 0}

    try:
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True, headers={"User-Agent": UA}
        ) as client:
            token = await login(client, creds["username"], creds["password"])
            SYNC_STATE["phase"] = "listing"
            SYNC_STATE["message"] = "正在获取活动列表…"

            page = 1
            relogined = False
            while True:
                try:
                    data = await list_activities(client, token, page, page_size)
                except IgpsportError as e:
                    # token 中途失效：重登一次
                    if not relogined and ("token" in str(e).lower() or "401" in str(e)):
                        relogined = True
                        token = await login(client, creds["username"], creds["password"])
                        data = await list_activities(client, token, page, page_size)
                    else:
                        raise

                rows = data.get("rows") or []
                total = int(data.get("totalRows") or 0)
                if total and SYNC_STATE["total"] != total:
                    SYNC_STATE["total"] = total
                if not rows:
                    break

                for item in rows:
                    ride_id = item.get("rideId")
                    if not ride_id:
                        continue
                    SYNC_STATE["phase"] = "downloading"
                    abs_path = None
                    try:
                        if _already_imported(db, ride_id):
                            SYNC_STATE["skipped"] += 1
                            SYNC_STATE["done"] += 1
                            continue

                        url = await get_download_url(client, token, ride_id)
                        content = await download_fit(client, url)

                        filename = f"igpsport_{ride_id}.fit"
                        abs_path = os.path.join(cycling_dir, filename)
                        with open(abs_path, "wb") as f:
                            f.write(content)

                        parsed = parse_fit(abs_path)
                        sport = (parsed.get("sport") or "").lower()
                        if sport and sport not in ("cycling", "generic", "e_biking"):
                            # 非骑行活动（跑步等）不导入骑行模块
                            try:
                                os.remove(abs_path)
                            except Exception:
                                pass
                            SYNC_STATE["skipped"] += 1
                            SYNC_STATE["done"] += 1
                            SYNC_STATE["message"] = f"跳过非骑行活动 {ride_id}（{sport}）"
                            continue

                        rel_path = os.path.join("cycling", filename)
                        act, adopted = _upsert_activity(db, ride_id, item, parsed, rel_path)
                        if adopted:
                            # 已合并到手动记录：本次下载的 FIT 不再需要
                            try:
                                os.remove(abs_path)
                            except Exception:
                                pass
                            abs_path = None
                            SYNC_STATE["merged"] += 1
                            SYNC_STATE["message"] = f"合并到已有记录 {SYNC_STATE['merged']} 条"
                        else:
                            SYNC_STATE["imported"] += 1
                            SYNC_STATE["message"] = f"已导入 {SYNC_STATE['imported']} 条"
                        SYNC_STATE["done"] += 1
                    except Exception as e:
                        # 单条失败必须回滚，否则 session 进入 rollback 状态会导致后续全部失败
                        try:
                            db.rollback()
                        except Exception:
                            pass
                        # 清理失败留下的半成品文件
                        if abs_path:
                            try:
                                os.remove(abs_path)
                            except Exception:
                                pass
                        SYNC_STATE["failed"] += 1
                        SYNC_STATE["done"] += 1
                        SYNC_STATE["message"] = f"rideId {ride_id} 失败：{str(e)[:150]}"
                        print(f"[iGPSPORT] rideId {ride_id} 失败: {e}")

                    await asyncio.sleep(delay)

                if total and page * page_size >= total:
                    break
                page += 1
                if page > 500:  # 安全上限
                    break

        SYNC_STATE["phase"] = "done"
        SYNC_STATE["message"] = (
            f"完成：新增 {SYNC_STATE['imported']}，合并 {SYNC_STATE['merged']}，"
            f"跳过 {SYNC_STATE['skipped']}，失败 {SYNC_STATE['failed']}"
        )
        result.update(
            imported=SYNC_STATE["imported"],
            merged=SYNC_STATE["merged"],
            skipped=SYNC_STATE["skipped"],
            failed=SYNC_STATE["failed"],
        )
        save_state(
            db,
            {
                "last_sync_at": datetime.now().isoformat(timespec="seconds"),
                "imported": SYNC_STATE["imported"],
                "merged": SYNC_STATE["merged"],
                "skipped": SYNC_STATE["skipped"],
                "failed": SYNC_STATE["failed"],
                "error": "",
            },
        )
    except Exception as e:
        SYNC_STATE["phase"] = "error"
        SYNC_STATE["message"] = f"同步失败：{str(e)[:300]}"
        result = {"ok": False, "message": str(e), **{k: SYNC_STATE[k] for k in ("imported", "skipped", "failed")}}
        save_state(
            db,
            {
                "last_sync_at": SYNC_STATE["started_at"],
                **{k: SYNC_STATE[k] for k in ("imported", "skipped", "failed")},
                "error": str(e)[:300],
            },
        )
        print(f"[iGPSPORT] 同步失败: {e}")
    finally:
        SYNC_STATE["running"] = False
        SYNC_STATE["finished_at"] = datetime.now().isoformat(timespec="seconds")

    return result


def snapshot_state() -> dict:
    """当前同步进度快照"""
    return dict(SYNC_STATE)
