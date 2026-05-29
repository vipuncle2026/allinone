"""用户认证路由"""
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models.auth import User, SessionToken

router = APIRouter(prefix="/api/auth", tags=["认证"])

# 登录限流：每分钟最多 5 次
_login_rate_limit: dict[str, list[float]] = {}


def _check_login_rate(client_ip: str) -> bool:
    """检查登录频率，返回 True 表示允许"""
    now = time.time()
    if client_ip not in _login_rate_limit:
        _login_rate_limit[client_ip] = []
    # 清理 1 分钟前的记录
    _login_rate_limit[client_ip] = [t for t in _login_rate_limit[client_ip] if now - t < 60]
    if len(_login_rate_limit[client_ip]) >= 5:
        return False
    _login_rate_limit[client_ip].append(now)
    return True

# Token 有效期（小时）
TOKEN_TTL_HOURS = 24


def _hash_password(password: str) -> str:
    """密码哈希（SHA-256 + salt）"""
    return hashlib.sha256(f"aio_salt_{password}".encode()).hexdigest()


def _hash_security_code(code: str) -> str:
    """安全码哈希（独立 salt 避免与密码混淆）"""
    return hashlib.sha256(f"aio_sc_{code}".encode()).hexdigest()


def _cleanup_expired_tokens(db: Session):
    """清理过期的 token 记录"""
    db.query(SessionToken).filter(SessionToken.expires_at < datetime.now()).delete()
    db.commit()


def verify_token(request: Request, db: Session = Depends(get_db)):
    """FastAPI 依赖注入：验证 token，返回 user 对象"""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""

    if not token:
        raise HTTPException(status_code=401, detail="未登录")

    row = db.query(SessionToken).filter(SessionToken.token == token).first()
    if not row:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    # expires_at 为空或已过期，视为无效 token
    if not row.expires_at or datetime.now() > row.expires_at:
        try:
            db.delete(row)
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        try:
            db.delete(row)
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(status_code=401, detail="用户不存在")

    # 刷新过期时间（滑动窗口，失败不影响认证）
    try:
        row.expires_at = datetime.now() + timedelta(hours=TOKEN_TTL_HOURS)
        db.commit()
    except Exception:
        db.rollback()
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """非严格模式：获取当前用户（未登录返回 None）"""
    try:
        return verify_token(request, db)
    except HTTPException:
        return None


@router.post("/login")
def login(request: Request, data: dict, db: Session = Depends(get_db)):
    """用户登录"""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_login_rate(client_ip):
        raise HTTPException(429, "登录次数过于频繁，请 1 分钟后再试")

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = db.query(User).filter(User.username == username).first()
    if not user or user.password_hash != _hash_password(password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 清理该用户的过期 token
    db.query(SessionToken).filter(
        SessionToken.user_id == user.id,
        SessionToken.expires_at < datetime.now(),
    ).delete()

    # 生成 token 并持久化
    token = secrets.token_hex(32)
    session = SessionToken(
        token=token,
        user_id=user.id,
        expires_at=datetime.now() + timedelta(hours=TOKEN_TTL_HOURS),
    )
    db.add(session)
    db.commit()

    return {
        "token": token,
        "user": {"id": user.id, "username": user.username},
    }


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    """用户登出"""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
    db.query(SessionToken).filter(SessionToken.token == token).delete()
    db.commit()
    return {"message": "已登出"}


@router.get("/me")
def get_me(user: User = Depends(verify_token)):
    """获取当前登录用户信息"""
    return {"id": user.id, "username": user.username}


@router.put("/password")
def change_password(data: dict, user: User = Depends(verify_token), db: Session = Depends(get_db)):
    """修改密码"""
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="旧密码和新密码不能为空")

    if len(new_password) < 4:
        raise HTTPException(status_code=400, detail="新密码至少 4 个字符")

    if user.password_hash != _hash_password(old_password):
        raise HTTPException(status_code=400, detail="旧密码错误")

    user.password_hash = _hash_password(new_password)
    user.updated_at = datetime.now()
    db.commit()

    return {"message": "密码修改成功"}


@router.put("/security-code")
def set_security_code(data: dict, user: User = Depends(verify_token), db: Session = Depends(get_db)):
    """设置/修改安全码"""
    password = data.get("password", "")
    new_code = data.get("security_code", "")

    if not password or not new_code:
        raise HTTPException(status_code=400, detail="密码和安全码不能为空")

    if len(new_code) < 4:
        raise HTTPException(status_code=400, detail="安全码至少 4 个字符")

    if user.password_hash != _hash_password(password):
        raise HTTPException(status_code=400, detail="密码错误")

    user.security_code = _hash_security_code(new_code)
    user.updated_at = datetime.now()
    db.commit()

    return {"message": "安全码设置成功"}


@router.post("/reset-password")
def reset_password(data: dict, db: Session = Depends(get_db)):
    """通过安全码重置密码（无需登录）"""
    username = data.get("username", "").strip()
    security_code = data.get("security_code", "")
    new_password = data.get("new_password", "")

    if not username or not security_code or not new_password:
        raise HTTPException(status_code=400, detail="用户名、安全码和新密码不能为空")

    if len(new_password) < 4:
        raise HTTPException(status_code=400, detail="新密码至少 4 个字符")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not user.security_code:
        raise HTTPException(status_code=400, detail="该用户未设置安全码，无法重置密码")

    if user.security_code != _hash_security_code(security_code):
        raise HTTPException(status_code=401, detail="安全码错误")

    user.password_hash = _hash_password(new_password)
    user.updated_at = datetime.now()

    # 重置密码后清除该用户所有 token
    db.query(SessionToken).filter(SessionToken.user_id == user.id).delete()
    db.commit()

    return {"message": "密码重置成功，请使用新密码登录"}
