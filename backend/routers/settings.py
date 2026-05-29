"""用户设置 API"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models.settings import UserSetting

router = APIRouter(prefix="/api/settings", tags=["用户设置"])


class SettingUpdate(BaseModel):
    value: str


@router.get("/{key}")
def get_setting(key: str, db: Session = Depends(get_db)):
    """获取指定设置值（不存在返回 None）"""
    row = db.query(UserSetting).filter(UserSetting.key == key).first()
    if not row:
        return {"key": key, "value": None}
    return {"key": key, "value": row.value}


@router.get("/cycling/defaults")
def get_cycling_defaults(db: Session = Depends(get_db)):
    """获取骑行默认参数"""
    ftp = db.query(UserSetting).filter(UserSetting.key == "cycling_default_ftp").first()
    return {
        "default_ftp": int(ftp.value) if ftp else 200,
    }


@router.put("/cycling/defaults")
def update_cycling_defaults(payload: dict, db: Session = Depends(get_db)):
    """更新骑行默认参数"""
    ftp = payload.get("default_ftp")
    if ftp is not None:
        row = db.query(UserSetting).filter(UserSetting.key == "cycling_default_ftp").first()
        now = datetime.now()
        if row:
            row.value = str(int(ftp))
            row.updated_at = now
        else:
            db.add(UserSetting(key="cycling_default_ftp", value=str(int(ftp)), updated_at=now))
        db.commit()
    return {"message": "保存成功"}


@router.put("/{key}")
def set_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db)):
    """设置指定键的值（upsert）"""
    now = datetime.now()
    row = db.query(UserSetting).filter(UserSetting.key == key).first()
    if row:
        row.value = payload.value
        row.updated_at = now
    else:
        db.add(UserSetting(key=key, value=payload.value, updated_at=now))
    db.commit()
    return {"key": key, "value": payload.value}
