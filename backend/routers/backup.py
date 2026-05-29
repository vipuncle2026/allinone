"""统一备份与恢复 API"""
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from database import get_session_factory, get_engine
from services import backup_service
from services.upload_utils import MAX_ZIP_FILE_SIZE

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/export")
def export_all():
    """导出所有模块数据为 JSON（含系统表：users、backup_logs）"""
    sess = get_session_factory()()
    try:
        data = backup_service.export_all_data(sess)
        json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        file_size = len(json_bytes)

        counts = data.get("record_counts", {})
        total_records = data.get("total_records", 0)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"allinone_backup_{ts}.json"
        backup_service.save_log(sess, "export", file_name=filename, file_size=file_size, record_count=total_records,
                                detail=json.dumps(counts, ensure_ascii=False))

        data["filename"] = filename
        data["file_size"] = file_size
        return data
    finally:
        sess.close()


@router.get("/export/full")
def export_full():
    """完整备份：数据库 JSON + allinone.db + uploads 文件，打包为 zip 下载"""
    buf, total_records = backup_service.build_full_backup_zip()
    file_size = len(buf.getvalue())
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"allinone_full_backup_{ts}.zip"

    sess = get_session_factory()()
    try:
        backup_service.save_log(sess, "export_full", file_name=filename, file_size=file_size,
                                record_count=total_records,
                                detail=f"完整备份（含 .db + 文件），大小 {backup_service.format_size(file_size)}")
    finally:
        sess.close()

    return StreamingResponse(
        buf,
        media_type='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'X-Filename': filename,
        }
    )


@router.post("/import")
async def import_all(file: UploadFile = File(...)):
    """从 JSON 文件导入所有模块数据（合并模式：存在则跳过）"""
    if not file.filename.endswith('.json'):
        raise HTTPException(400, "仅支持 .json 文件")

    try:
        content = await file.read()
        payload = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "JSON 格式错误")

    if payload.get("version") != backup_service.BACKUP_VERSION:
        raise HTTPException(400, f"不支持的备份版本: {payload.get('version')}，当前版本: {backup_service.BACKUP_VERSION}")

    modules = payload.get("modules", {})
    if not modules:
        raise HTTPException(400, "备份数据中无模块数据")

    sess = get_session_factory()()
    try:
        stats = backup_service.import_module_data(sess, modules)
        backup_service.save_log(sess, "import", file_name=file.filename, file_size=len(content),
                                record_count=stats["imported"],
                                detail=f"新增{stats['imported']} 跳过{stats['skipped']} 失败{stats['errors']}")
    except Exception as e:
        sess.rollback()
        raise HTTPException(500, f"导入失败: {str(e)}")
    finally:
        sess.close()

    return {
        "success": True,
        "message": f"导入完成：新增 {stats['imported']} 条，跳过 {stats['skipped']} 条，失败 {stats['errors']} 条",
        "stats": stats,
    }


@router.post("/import/full")
async def import_full(file: UploadFile = File(...)):
    """完整恢复：从 zip 备份包还原数据和文件"""
    if not file.filename.endswith('.zip'):
        raise HTTPException(400, "仅支持 .zip 格式的完整备份文件")

    try:
        content = await file.read()
    except Exception:
        raise HTTPException(400, "文件读取失败")

    if len(content) > MAX_ZIP_FILE_SIZE:
        raise HTTPException(400, f"备份文件过大（最大 {MAX_ZIP_FILE_SIZE // 1024 // 1024 // 1024}GB），"
                            f"当前: {len(content) / 1024 / 1024 / 1024:.1f}GB")

    return backup_service.restore_full_backup(content, file.filename)


@router.get("/info")
def backup_info():
    """返回备份数据预览（各模块记录数）"""
    from pathlib import Path

    sess = get_session_factory()()
    try:
        tables = [
            ("finance_accounts", "财务管理"),
            ("finance_transactions", "收支记录"),
            ("finance_bill_imports", "账单导入批次"),
            ("finance_category_rules", "分类规则"),
            ("asset_snapshots", "资产快照"),
            ("cycling_activities", "骑行活动"),
            ("bikes", "骑行车辆"),
            ("bike_maintenance", "车辆维护"),
            ("hiking_activities", "徒步活动"),
            ("running_activities", "跑步活动"),
            ("travel_trips", "旅行计划"),
            ("travel_expenses", "旅行支出"),
            ("travel_mileages", "旅行里程"),
            ("fund_library", "基金库"),
            ("fund_favorites", "自选基金"),
            ("fund_groups", "基金分组"),
            ("fund_snapshots", "持仓快照"),
            ("fund_snapshot_items", "持仓快照明细"),
            ("vehicles", "机动车"),
            ("fuel_records", "加油/充电记录"),
            ("vehicle_expenses", "车辆费用"),
            ("important_items", "重要物品"),
        ]
        result = []
        for table_name, label in tables:
            count = sess.execute(text(f"SELECT COUNT(*) FROM [{table_name}]")).scalar()
            result.append({"table": table_name, "label": label, "count": count})

        total = sum(r["count"] for r in result)

        db_url = str(get_engine().url)
        db_path = Path(db_url.removeprefix('sqlite:///'))
        db_size = 0
        if db_path.exists():
            db_size = db_path.stat().st_size

        return {
            "tables": result,
            "total_records": total,
            "db": {
                "name": db_path.name,
                "size": db_size,
                "size_display": backup_service.format_size(db_size),
            }
        }
    finally:
        sess.close()


@router.get("/logs")
def get_backup_logs(limit: int = 8):
    """获取备份操作记录，默认最近8条"""
    from models.backup import BackupLog
    sess = get_session_factory()()
    try:
        logs = sess.query(BackupLog).order_by(BackupLog.created_at.desc()).limit(limit).all()
        return [
            {
                "id": log.id,
                "operation": log.operation,
                "file_name": log.file_name or "",
                "file_size": log.file_size or 0,
                "file_size_display": backup_service.format_size(log.file_size) if log.file_size else "",
                "record_count": log.record_count or 0,
                "detail": log.detail or "",
                "created_at": log.created_at.isoformat() if log.created_at else "",
            }
            for log in logs
        ]
    finally:
        sess.close()


@router.delete("/logs")
def clear_backup_logs():
    """清除全部操作记录"""
    from models.backup import BackupLog
    sess = get_session_factory()()
    try:
        count = sess.query(BackupLog).count()
        if count > 0:
            sess.execute(text("DELETE FROM backup_logs"))
            sess.commit()
        return {"success": True, "message": f"已清除 {count} 条操作记录", "count": count}
    except Exception as e:
        sess.rollback()
        raise HTTPException(500, f"清除失败: {str(e)}")
    finally:
        sess.close()


@router.delete("/logs/{log_id}")
def delete_backup_log(log_id: int):
    """删除一条操作记录"""
    from models.backup import BackupLog
    sess = get_session_factory()()
    try:
        log = sess.query(BackupLog).filter(BackupLog.id == log_id).first()
        if not log:
            raise HTTPException(404, "记录不存在")
        sess.delete(log)
        sess.commit()
        return {"success": True, "message": "已删除"}
    finally:
        sess.close()


@router.post("/reset")
def reset_data():
    """数据初始化：清空所有业务表数据，保留备份日志"""
    return backup_service.reset_all_data()


@router.post("/cleanup-orphan-files")
def cleanup_orphan_files():
    """清理 uploads/ 目录中不再被任何活动记录引用的孤儿文件"""
    return backup_service.do_cleanup_orphan_files()
