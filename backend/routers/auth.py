"""用户认证路由"""
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from database import get_db
from models.auth import User, SessionToken

router = APIRouter(prefix="/api/auth", tags=["认证"])

# 登录/重置限流：每分钟最多 5 次
_login_rate_limit: dict[str, list[float]] = {}
_reset_rate_limit: dict[str, list[float]] = {}


def _check_rate(bucket: dict[str, list[float]], client_ip: str, limit: int = 5) -> bool:
    now = time.time()
    hits = [t for t in bucket.get(client_ip, []) if now - t < 60]
    if len(hits) >= limit:
        bucket[client_ip] = hits
        return False
    hits.append(now)
    bucket[client_ip] = hits
    return True

# Token 有效期（小时）
TOKEN_TTL_HOURS = 24
TOKEN_REFRESH_THRESHOLD_HOURS = 12
SESSION_COOKIE = "aio_session"
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1


def _hash_secret(secret: str, purpose: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        f"{purpose}:{secret}".encode(),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=32,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${derived.hex()}"


def _verify_secret(stored: str, secret: str, purpose: str, legacy_prefix: str) -> bool:
    if stored.startswith("scrypt$"):
        try:
            _, n, r, p, salt_hex, expected_hex = stored.split("$", 5)
            actual = hashlib.scrypt(
                f"{purpose}:{secret}".encode(),
                salt=bytes.fromhex(salt_hex),
                n=int(n),
                r=int(r),
                p=int(p),
                dklen=len(bytes.fromhex(expected_hex)),
            )
            return hmac.compare_digest(actual.hex(), expected_hex)
        except (ValueError, TypeError):
            return False
    legacy = hashlib.sha256(f"{legacy_prefix}{secret}".encode()).hexdigest()
    return hmac.compare_digest(stored, legacy)


def _hash_password(password: str) -> str:
    return _hash_secret(password, "password")


def _verify_password(stored: str, password: str) -> bool:
    return _verify_secret(stored, password, "password", "aio_salt_")


def _hash_security_code(code: str) -> str:
    return _hash_secret(code, "security-code")


def _verify_security_code(stored: str, code: str) -> bool:
    return _verify_secret(stored, code, "security-code", "aio_sc_")


def _request_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()
    return request.cookies.get(SESSION_COOKIE, "")


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=TOKEN_TTL_HOURS * 3600,
        httponly=True,
        secure=request.url.scheme == "https" or forwarded_proto == "https",
        samesite="lax",
        path="/",
    )


def _cleanup_expired_tokens(db: Session):
    """清理过期的 token 记录"""
    db.query(SessionToken).filter(SessionToken.expires_at < datetime.now()).delete()
    db.commit()


def verify_token(request: Request, db: Session = Depends(get_db)):
    """FastAPI 依赖注入：验证 token，返回 user 对象"""
    token = _request_token(request)

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

    # 只在有效期不足一半时刷新，避免每个请求都写 SQLite。
    if row.expires_at - datetime.now() < timedelta(hours=TOKEN_REFRESH_THRESHOLD_HOURS):
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
def login(request: Request, response: Response, data: dict, db: Session = Depends(get_db)):
    """用户登录"""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate(_login_rate_limit, client_ip):
        raise HTTPException(429, "登录次数过于频繁，请 1 分钟后再试")

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = db.query(User).filter(User.username == username).first()
    if not user or not _verify_password(user.password_hash, password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 旧版 SHA-256 哈希在成功登录后原地升级。
    if not user.password_hash.startswith("scrypt$"):
        user.password_hash = _hash_password(password)

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
    _set_session_cookie(response, request, token)

    return {
        "token": token,
        "user": {"id": user.id, "username": user.username},
    }


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """用户登出"""
    token = _request_token(request)
    db.query(SessionToken).filter(SessionToken.token == token).delete()
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"message": "已登出"}


@router.get("/me")
def get_me(request: Request, response: Response, user: User = Depends(verify_token)):
    """获取当前登录用户信息"""
    token = _request_token(request)
    if token:
        _set_session_cookie(response, request, token)
    return {"id": user.id, "username": user.username}


@router.put("/password")
def change_password(data: dict, user: User = Depends(verify_token), db: Session = Depends(get_db)):
    """修改密码"""
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="旧密码和新密码不能为空")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="新密码至少 8 个字符")

    if not _verify_password(user.password_hash, old_password):
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

    if not _verify_password(user.password_hash, password):
        raise HTTPException(status_code=400, detail="密码错误")

    user.security_code = _hash_security_code(new_code)
    user.updated_at = datetime.now()
    db.commit()

    return {"message": "安全码设置成功"}


@router.post("/reset-password")
def reset_password(request: Request, data: dict, db: Session = Depends(get_db)):
    """通过安全码重置密码（无需登录）"""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate(_reset_rate_limit, client_ip):
        raise HTTPException(429, "重置尝试过于频繁，请 1 分钟后再试")

    username = data.get("username", "").strip()
    security_code = data.get("security_code", "")
    new_password = data.get("new_password", "")

    if not username or not security_code or not new_password:
        raise HTTPException(status_code=400, detail="用户名、安全码和新密码不能为空")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="新密码至少 8 个字符")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.security_code or not _verify_security_code(user.security_code, security_code):
        raise HTTPException(status_code=401, detail="用户名或安全码错误")

    user.password_hash = _hash_password(new_password)
    user.updated_at = datetime.now()

    # 重置密码后清除该用户所有 token
    db.query(SessionToken).filter(SessionToken.user_id == user.id).delete()
    db.commit()

    return {"message": "密码重置成功，请使用新密码登录"}
