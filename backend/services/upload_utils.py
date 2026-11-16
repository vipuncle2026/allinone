"""文件上传与恢复的公共安全工具函数"""

import os
import uuid
from pathlib import Path, PurePosixPath
from typing import Tuple
import zipfile
from fastapi import HTTPException


def safe_upload_path(upload_dir: str, ext: str) -> str:
    """生成安全的上传路径，使用 UUID 文件名防止路径穿越和同名覆盖。

    Args:
        upload_dir: 目标上传目录（如 uploads/cycling）
        ext: 文件扩展名（不含点号，如 "gpx"、"fit"）

    Returns:
        拼接后的绝对路径，如 /path/to/uploads/cycling/a1b2c3d4e5f6.gpx
    """
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    return str(Path(upload_dir) / filename)


def resolve_upload_path(path: str, *, require_exists: bool = False) -> Path:
    """把数据库/API 中的上传文件引用解析到 uploads 根目录内。"""
    if not path or "\x00" in path:
        raise HTTPException(400, "非法的上传文件路径")

    normalized = path.replace("\\", "/")
    if normalized.startswith("uploads/"):
        normalized = normalized[len("uploads/"):]

    relative = PurePosixPath(normalized)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise HTTPException(400, "非法的上传文件路径")

    base = Path(os.getenv("UPLOAD_DIR") or "").resolve() if os.getenv("UPLOAD_DIR") else None
    if base is None:
        from database import get_upload_dir
        base = Path(get_upload_dir()).resolve()

    resolved = (base / Path(*relative.parts)).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise HTTPException(400, "非法的上传文件路径")

    if require_exists and not resolved.is_file():
        raise HTTPException(404, "上传文件不存在")
    return resolved


def safe_remove_upload(path: str) -> bool:
    """仅删除 uploads 根目录内的普通文件。"""
    try:
        target = resolve_upload_path(path)
    except HTTPException:
        return False
    if not target.is_file():
        return False
    try:
        target.unlink()
        return True
    except OSError:
        return False


def safe_extract_path(upload_dir: str, entry_name: str) -> str:
    """校验备份 ZIP 中的 uploads 条目并返回上传根目录内的目标路径。

    Args:
        upload_dir: 允许解压的 uploads 根目录
        entry_name: zip 条目中的文件名（如 uploads/cycling/xxx.gpx）

    Returns:
        校验通过后的安全绝对路径

    Raises:
        HTTPException: 路径尝试逃逸 data_dir 时抛出 400
    """
    if "\x00" in entry_name or "\\" in entry_name:
        raise HTTPException(400, f"非法的备份文件路径: {entry_name}")

    entry = PurePosixPath(entry_name)
    try:
        relative = entry.relative_to("uploads")
    except ValueError:
        raise HTTPException(400, f"非法的备份文件路径: {entry_name}")

    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise HTTPException(400, f"非法的备份文件路径: {entry_name}")

    base = Path(upload_dir).resolve()
    resolved = (base / Path(*relative.parts)).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise HTTPException(400, f"非法的备份文件路径: {entry_name}")
    return str(resolved)


# ─── ZIP 恢复大小限制配置 ────────────────────────────────────────────

MAX_ZIP_FILE_SIZE = 2 * 1024 * 1024 * 1024   # ZIP 文件本身最大 2GB
MAX_SINGLE_EXTRACT = 200 * 1024 * 1024        # 单文件解压上限 200MB
MAX_TOTAL_EXTRACT = 5 * 1024 * 1024 * 1024    # 总解压上限 5GB
MAX_ZIP_ENTRIES = 10000                        # 最大文件数量


def validate_zip_limits(zf: zipfile.ZipFile) -> Tuple[int, int]:
    """校验 zip 文件大小限制，在真正解压之前拦截压缩炸弹。

    Args:
        zf: 已打开的 ZipFile 对象

    Returns:
        (file_count, total_uncompressed_size) 用于日志记录

    Raises:
        HTTPException: 超出限制时抛出 400
    """
    file_count = 0
    total_size = 0

    for info in zf.infolist():
        if info.is_dir():
            continue

        file_count += 1
        total_size += info.file_size

        if file_count > MAX_ZIP_ENTRIES:
            raise HTTPException(
                400,
                f"备份文件数量超出限制（最多 {MAX_ZIP_ENTRIES} 个），当前: {file_count}"
            )

        if info.file_size > MAX_SINGLE_EXTRACT:
            raise HTTPException(
                400,
                f"备份中存在超大文件（最大单文件 {MAX_SINGLE_EXTRACT // 1024 // 1024}MB），"
                f"当前: {info.filename} ({info.file_size // 1024 // 1024}MB)"
            )

    if total_size > MAX_TOTAL_EXTRACT:
        raise HTTPException(
            400,
            f"备份总解压大小超出限制（最大 {MAX_TOTAL_EXTRACT // 1024 // 1024 // 1024}GB），"
            f"当前: {total_size // 1024 // 1024}MB"
        )

    return file_count, total_size


def safe_remove(path: str) -> None:
    """安全删除文件，文件不存在时静默跳过。"""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def suggest_title(data: dict) -> str:
    """根据解析出的活动数据生成统一命名：MM月DD日 XX.XXkm 骑行

    手动导入与 iGPSPORT 自动同步共用同一套命名规则，避免同一活动出现两种标题。
    """
    from datetime import datetime

    dist = data.get("distance_km") or 0
    ts = data.get("start_time")
    prefix = f"{dist}km 骑行" if dist else "骑行"
    if ts:
        try:
            dt = ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts))
            return f"{dt.strftime('%m月%d日')} {prefix}"
        except Exception:
            pass
    return prefix
