"""备份/恢复业务逻辑层 — 从 routers/backup.py 拆出"""
import io
import os
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, date as date_type, timedelta
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import inspect, text

from database import get_session_factory, get_engine, get_upload_dir, get_data_dir, _get_db_path
from services.upload_utils import safe_extract_path, validate_zip_limits

BACKUP_VERSION = "1.0"


# ============================================================
# 通用工具函数
# ============================================================

def row_to_dict(row, columns):
    """将 ORM 行转为字典，处理日期/时间序列化"""
    d = {}
    for col in columns:
        val = getattr(row, col, None)
        if val is not None:
            if hasattr(val, 'isoformat'):
                val = val.isoformat()
            elif isinstance(val, bytes):
                val = val.decode('utf-8', errors='replace')
        d[col] = val
    return d


def get_table_columns(sess, table_name):
    """获取表的所有列名"""
    insp = inspect(get_engine())
    return [c['name'] for c in insp.get_columns(table_name)]


def parse_date(val):
    """将日期字符串转换为 Python date 对象"""
    if val is None or val == "":
        return None
    if hasattr(val, 'year'):
        return val
    s = str(val).strip()
    if not s:
        return None
    from datetime import datetime
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_datetime(val):
    """将日期时间字符串转换为 Python datetime 对象"""
    if val is None or val == "":
        return None
    if hasattr(val, 'hour'):
        return val
    s = str(val).strip()
    if not s:
        return None
    from datetime import datetime
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return val


def format_size(size_bytes):
    """将字节数格式化为可读字符串"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.2f} MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"


def save_log(sess, operation, file_name="", file_size=0, record_count=0, detail=""):
    """写入备份操作记录"""
    from models.backup import BackupLog
    log = BackupLog(
        operation=operation,
        file_name=file_name,
        file_size=file_size,
        record_count=record_count,
        detail=detail,
    )
    sess.add(log)
    sess.commit()


# ============================================================
# 表导出
# ============================================================

def export_table(sess, table_name, model_class=None):
    """导出单张表所有数据"""
    columns = get_table_columns(sess, table_name)
    if model_class:
        rows = sess.query(model_class).all()
    else:
        rows = sess.execute(text(f"SELECT * FROM [{table_name}]")).fetchall()
        result = []
        for row in rows:
            d = {}
            for i, col in enumerate(columns):
                val = row[i]
                if val is not None and hasattr(val, 'isoformat'):
                    val = val.isoformat()
                d[col] = val
            result.append(d)
        return result
    return [row_to_dict(r, columns) for r in rows]


def export_all_data(sess):
    """导出所有模块数据"""
    from models.finance import FinanceAccount, FinanceTransaction, AssetSnapshot, FinanceBillImport, FinanceCategoryRule
    from models.cycling import Bike, BikeMaintenanceRecord, CyclingActivity
    from models.hiking import HikingActivity
    from models.running import RunningActivity
    from models.travel import TravelTrip, TravelExpense, TravelMileage
    from models.fund import FundLibrary, FundFavorite, FundGroup, FundSnapshot, FundSnapshotItem
    from models.vehicle import Vehicle, FuelRecord, VehicleExpense
    from models.item import Item
    from models.auth import User
    from models.backup import BackupLog

    data = {
        "version": BACKUP_VERSION,
        "exported_at": datetime.now().isoformat(),
        "modules": {
            "finance": {
                "accounts": export_table(sess, "finance_accounts", FinanceAccount),
                "transactions": export_table(sess, "finance_transactions", FinanceTransaction),
                "bill_imports": export_table(sess, "finance_bill_imports", FinanceBillImport),
                "category_rules": export_table(sess, "finance_category_rules", FinanceCategoryRule),
                "asset_snapshots": export_table(sess, "asset_snapshots", AssetSnapshot),
            },
            "cycling": {
                "bikes": export_table(sess, "bikes", Bike),
                "bike_maintenance": export_table(sess, "bike_maintenance", BikeMaintenanceRecord),
                "activities": export_table(sess, "cycling_activities", CyclingActivity),
            },
            "hiking": {
                "activities": export_table(sess, "hiking_activities", HikingActivity),
            },
            "running": {
                "activities": export_table(sess, "running_activities", RunningActivity),
            },
            "travel": {
                "trips": export_table(sess, "travel_trips", TravelTrip),
                "expenses": export_table(sess, "travel_expenses", TravelExpense),
                "mileages": export_table(sess, "travel_mileages", TravelMileage),
            },
            "fund": {
                "library": export_table(sess, "fund_library", FundLibrary),
                "favorites": export_table(sess, "fund_favorites", FundFavorite),
                "groups": export_table(sess, "fund_groups", FundGroup),
                "snapshots": export_table(sess, "fund_snapshots", FundSnapshot),
                "snapshot_items": export_table(sess, "fund_snapshot_items", FundSnapshotItem),
            },
            "vehicle": {
                "vehicles": export_table(sess, "vehicles", Vehicle),
                "fuel_records": export_table(sess, "fuel_records", FuelRecord),
                "expenses": export_table(sess, "vehicle_expenses", VehicleExpense),
            },
            "item": {
                "important_items": export_table(sess, "important_items", Item),
            },
            "system": {
                "users": export_table(sess, "users", User),
                "backup_logs": export_table(sess, "backup_logs", BackupLog),
                "user_settings": export_table(sess, "user_settings"),
            },
        },
    }

    counts = {}
    for mod, tables in data["modules"].items():
        counts[mod] = sum(len(v) for v in tables.values())
    data["record_counts"] = counts
    data["total_records"] = sum(v for k, v in counts.items() if k != "system")

    return data


# ============================================================
# 表导入（JSON 模式 & ZIP 模式共用）
# ============================================================

# 导入时用到的日期/时间字段名
_DATE_FIELDS = {"purchase_date", "date", "start_date", "end_date"}
_DATETIME_FIELDS = {
    "start_time", "end_time", "fuel_date", "expense_date",
    "created_at", "updated_at"
}

# 各模块的表配置：(key, model_class, pk_column)
def _build_table_config():
    from models.finance import FinanceAccount, FinanceTransaction, AssetSnapshot, FinanceBillImport, FinanceCategoryRule
    from models.cycling import Bike, BikeMaintenanceRecord, CyclingActivity
    from models.hiking import HikingActivity
    from models.running import RunningActivity
    from models.travel import TravelTrip, TravelExpense, TravelMileage
    from models.fund import FundLibrary, FundFavorite, FundGroup, FundSnapshot, FundSnapshotItem
    from models.vehicle import Vehicle, FuelRecord, VehicleExpense
    from models.item import Item

    return {
        "finance": [
            ("accounts", FinanceAccount, "id"),
            ("transactions", FinanceTransaction, "id"),
            ("bill_imports", FinanceBillImport, "id"),
            ("category_rules", FinanceCategoryRule, "id"),
            ("asset_snapshots", AssetSnapshot, "id"),
        ],
        "cycling": [
            ("bikes", Bike, "id"),
            ("bike_maintenance", BikeMaintenanceRecord, "id"),
            ("activities", CyclingActivity, "id"),
        ],
        "hiking": [
            ("activities", HikingActivity, "id"),
        ],
        "running": [
            ("activities", RunningActivity, "id"),
        ],
        "travel": [
            ("trips", TravelTrip, "id"),
            ("expenses", TravelExpense, "id"),
            ("mileages", TravelMileage, "id"),
        ],
        "fund": [
            ("library", FundLibrary, "code"),
            ("favorites", FundFavorite, "id"),
            ("groups", FundGroup, "id"),
            ("snapshots", FundSnapshot, "id"),
            ("snapshot_items", FundSnapshotItem, "id"),
        ],
        "vehicle": [
            ("vehicles", Vehicle, "id"),
            ("fuel_records", FuelRecord, "id"),
            ("expenses", VehicleExpense, "id"),
        ],
        "item": [
            ("important_items", Item, "id"),
        ],
    }


def import_module_data(sess, modules: dict) -> dict:
    """导入所有模块数据（合并模式：存在则跳过）"""
    TABLE_CONFIG = _build_table_config()

    stats = {"imported": 0, "skipped": 0, "errors": 0}

    # 单独处理 user_settings（key-value 结构）
    from models.settings import UserSetting as UserSettingModel
    user_settings_data = modules.get("system", {}).get("user_settings", [])
    for row_data in user_settings_data:
        key_val = row_data.get("key")
        if key_val:
            existing = sess.query(UserSettingModel).filter(
                UserSettingModel.key == key_val
            ).first()
            if not existing:
                filtered = {k: v for k, v in row_data.items() if k in ["key", "value"]}
                filtered["updated_at"] = parse_datetime(row_data.get("updated_at"))
                if filtered.get("updated_at") is None:
                    filtered["updated_at"] = datetime.now()
                sess.add(UserSettingModel(**filtered))
                stats["imported"] += 1
            else:
                stats["skipped"] += 1

    for mod_name, tables in TABLE_CONFIG.items():
        mod_data = modules.get(mod_name, {})
        for key, model, pk_col in tables:
            rows = mod_data.get(key, [])
            for row_data in rows:
                try:
                    pk_val = row_data.get(pk_col)
                    if pk_val is not None:
                        existing = sess.query(model).filter(
                            getattr(model, pk_col) == pk_val
                        ).first()
                        if existing:
                            stats["skipped"] += 1
                            continue

                    table_name = model.__tablename__
                    valid_columns = get_table_columns(sess, table_name)
                    filtered = {k: v for k, v in row_data.items() if k in valid_columns}

                    for col in _DATE_FIELDS & set(filtered):
                        val = parse_date(filtered[col])
                        if isinstance(val, str):
                            print(f"[Backup] date字段无法解析 table={table_name} col={col} val={val!r}")
                            val = None
                        filtered[col] = val
                    for col in _DATETIME_FIELDS & set(filtered):
                        val = parse_datetime(filtered[col])
                        if isinstance(val, str):
                            print(f"[Backup] datetime字段无法解析 table={table_name} col={col} val={val!r}")
                            val = None
                        filtered[col] = val

                    if (pk_col == "id" and filtered.get("id") is not None
                            and isinstance(filtered["id"], int)):
                        max_id = sess.execute(
                            text(f"SELECT MAX(id) FROM [{table_name}]")
                        ).scalar() or 0
                        if isinstance(max_id, int) and filtered["id"] <= max_id:
                            filtered.pop("id", None)

                    obj = model(**filtered)
                    sess.add(obj)
                    stats["imported"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    print(f"[Backup Import] 导入失败 table={key} row={row_data.get(pk_col, row_data.get('id', '?'))}: {e}")

    sess.commit()
    return stats


# ============================================================
# 完整备份（ZIP）
# ============================================================

def build_full_backup_zip() -> io.BytesIO:
    """生成完整备份 zip（JSON + .db + uploads），返回 BytesIO"""
    sess = get_session_factory()()
    try:
        data = export_all_data(sess)
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    finally:
        sess.close()

    # VACUUM INTO 热备
    db_path, _ = _get_db_path()
    tmp_db_path = None
    try:
        tmp_fd, tmp_db_path = tempfile.mkstemp(suffix=".db", prefix="allinone_vacuumtmp_")
        os.close(tmp_fd)
        os.unlink(tmp_db_path)
        src_conn = sqlite3.connect(str(db_path))
        src_conn.execute(f"VACUUM INTO '{tmp_db_path}'")
        src_conn.close()
    except Exception as e:
        tmp_db_path = None
        print(f"[Backup] VACUUM INTO 失败，跳过 .db 备份: {e}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('backup_data.json', json_bytes)
        if tmp_db_path and os.path.exists(tmp_db_path):
            zf.write(tmp_db_path, 'allinone.db')
        upload_dir = get_upload_dir()
        data_dir = get_data_dir()
        if os.path.isdir(upload_dir):
            for root, dirs, files in os.walk(upload_dir):
                files = [f for f in files if not f.startswith('._')]
                for fname in files:
                    full_path = os.path.join(root, fname)
                    arcname = os.path.relpath(full_path, data_dir)
                    zf.write(full_path, arcname)

    if tmp_db_path and os.path.exists(tmp_db_path):
        try:
            os.unlink(tmp_db_path)
        except Exception:
            pass

    buf.seek(0)
    return buf, data.get("total_records", 0)


# ============================================================
# 完整恢复（ZIP）
# ============================================================

def restore_full_backup(content: bytes, original_filename: str) -> dict:
    """从 zip 备份包还原数据和文件"""
    buf = io.BytesIO(content)

    try:
        zf = zipfile.ZipFile(buf, 'r')
    except zipfile.BadZipFile:
        raise HTTPException(400, "ZIP 文件格式错误，无法解压")

    # 校验 zip 大小限制（防压缩炸弹）
    file_count, total_size = validate_zip_limits(zf)

    json_entry = None
    file_entries = []
    for info in zf.infolist():
        name = info.filename
        if name.startswith('._') or info.is_dir():
            continue
        if name.endswith('backup_data.json'):
            json_entry = info
        elif name.startswith('uploads/'):
            file_entries.append(info)

    if not json_entry:
        raise HTTPException(400, "备份包中未找到备份数据文件（backup_data.json）")

    try:
        payload = json.loads(zf.read(json_entry.filename))
    except json.JSONDecodeError:
        raise HTTPException(400, "备份数据 JSON 格式错误")

    if payload.get("version") != BACKUP_VERSION:
        raise HTTPException(400, f"不支持的备份版本: {payload.get('version')}")

    # 还原 uploads 文件（防 Zip Slip）
    data_dir = get_data_dir()
    restored_files = 0
    for entry in file_entries:
        target = safe_extract_path(data_dir, entry.filename)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with zf.open(entry) as src, open(target, 'wb') as dst:
            dst.write(src.read())
        restored_files += 1

    # 导入数据
    modules = payload.get("modules", {})
    sess = get_session_factory()()
    try:
        stats = import_module_data(sess, modules)
        save_log(sess, "import_full", file_name=original_filename, file_size=len(content),
                 record_count=stats["imported"],
                 detail=f"完整恢复：新增{stats['imported']} 跳过{stats['skipped']} 失败{stats['errors']} 文件{restored_files}个")
    except Exception as e:
        sess.rollback()
        raise HTTPException(500, f"数据导入失败: {str(e)}")
    finally:
        sess.close()

    return {
        "success": True,
        "message": f"完整恢复完成：新增 {stats['imported']} 条，跳过 {stats['skipped']} 条，失败 {stats['errors']} 条，还原 {restored_files} 个文件",
        "stats": stats,
        "restored_files": restored_files,
    }


# ============================================================
# 数据初始化
# ============================================================

def reset_all_data() -> dict:
    """数据初始化：清空所有业务表数据，保留备份日志"""
    sess = get_session_factory()()

    from models.finance import FinanceAccount, FinanceTransaction, AssetSnapshot, FinanceBillImport, FinanceCategoryRule
    from models.cycling import Bike, BikeMaintenanceRecord, CyclingActivity
    from models.hiking import HikingActivity
    from models.running import RunningActivity
    from models.travel import TravelTrip, TravelExpense, TravelMileage
    from models.fund import FundLibrary, FundFavorite, FundGroup, FundSnapshot, FundSnapshotItem
    from models.vehicle import Vehicle, FuelRecord, VehicleExpense
    from models.item import Item
    from models.settings import UserSetting

    reset_tables = [
        ("finance_category_rules", FinanceCategoryRule),
        ("finance_bill_imports", FinanceBillImport),
        ("finance_transactions", FinanceTransaction),
        ("asset_snapshots", AssetSnapshot),
        ("finance_accounts", FinanceAccount),
        ("bike_maintenance", BikeMaintenanceRecord),
        ("cycling_activities", CyclingActivity),
        ("bikes", Bike),
        ("hiking_activities", HikingActivity),
        ("running_activities", RunningActivity),
        ("travel_trips", TravelTrip),
        ("travel_expenses", TravelExpense),
        ("travel_mileages", TravelMileage),
        ("fund_favorites", FundFavorite),
        ("fund_groups", FundGroup),
        ("fund_snapshot_items", FundSnapshotItem),
        ("fund_snapshots", FundSnapshot),
        ("fund_library", FundLibrary),
        ("fuel_records", FuelRecord),
        ("vehicle_expenses", VehicleExpense),
        ("vehicles", Vehicle),
        ("important_items", Item),
        ("user_settings", UserSetting),
    ]

    counts = {}
    try:
        for table_name, model in reset_tables:
            count = sess.query(model).count()
            if count > 0:
                sess.execute(text(f"DELETE FROM [{table_name}]"))
                counts[table_name] = count

        sess.commit()

        try:
            for table_name, _ in reset_tables:
                sess.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'"))
            sess.commit()
        except Exception:
            pass

        total = sum(counts.values())
        save_log(sess, "reset", record_count=total,
                 detail=json.dumps(counts, ensure_ascii=False))

        return {
            "success": True,
            "message": f"数据初始化完成，共清空 {total} 条记录",
            "detail": counts,
        }
    except Exception as e:
        sess.rollback()
        raise HTTPException(500, f"初始化失败: {str(e)}")
    finally:
        sess.close()


# ============================================================
# 孤儿文件清理
# ============================================================

def do_cleanup_orphan_files() -> dict:
    """清理 uploads/ 目录中不再被任何活动记录引用的孤儿文件"""
    from models.cycling import CyclingActivity
    from models.hiking import HikingActivity
    from models.running import RunningActivity

    sess = get_session_factory()()
    try:
        upload_base = os.path.abspath(get_upload_dir())
        db_paths = set()
        for model in (CyclingActivity, HikingActivity, RunningActivity):
            rows = sess.query(model.file_path).filter(model.file_path != None).all()
            for (fp,) in rows:
                if fp:
                    db_paths.add(os.path.abspath(os.path.join(upload_base, fp)))
    finally:
        sess.close()

    subdirs = ["cycling", "hiking", "running"]
    deleted_files = []
    freed_bytes = 0

    for sub in subdirs:
        upload_sub = get_upload_dir(sub)
        if not os.path.isdir(upload_sub):
            continue
        for fname in os.listdir(upload_sub):
            fpath = os.path.abspath(os.path.join(upload_sub, fname))
            if not os.path.isfile(fpath):
                continue
            if fpath not in db_paths:
                size = os.path.getsize(fpath)
                try:
                    os.remove(fpath)
                    freed_bytes += size
                    deleted_files.append({"path": fpath, "size": size})
                except Exception as e:
                    deleted_files.append({"path": fpath, "error": str(e)})

    freed_mb = round(freed_bytes / 1024 / 1024, 2)
    return {
        "success": True,
        "deleted_count": len(deleted_files),
        "freed_mb": freed_mb,
        "files": deleted_files,
    }
