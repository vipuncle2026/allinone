from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import argparse
import time
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

from database import init_db, get_upload_dir, get_data_dir
from routers import cycling, fund, finance, hiking, vehicle, travel, backup, auth, dashboard, item, search, settings, running


# ── 简易限流器（基于 IP + 时间窗口）────────────────────────────────────────
class SimpleLimiter:
    """简单的内存限流器，无外部依赖"""
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window = 60  # 1分钟窗口
        self.hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # 清理过期记录
        self.hits[client_ip] = [t for t in self.hits[client_ip] if now - t < self.window]
        if len(self.hits[client_ip]) >= self.requests_per_minute:
            return False
        self.hits[client_ip].append(now)
        return True

    def limit(self, rpm: int):
        """装饰器工厂"""
        def decorator(func):
            async def wrapper(request: Request, *args, **kwargs):
                client_ip = request.client.host if request.client else "unknown"
                if not self.is_allowed(client_ip):
                    raise HTTPException(429, "请求过于频繁，请稍后再试")
                return await func(request, *args, **kwargs)
            return wrapper
        return decorator

# 全局限流器
simple_limiter = SimpleLimiter(requests_per_minute=60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 确保数据目录存在
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    init_db()
    # 启动定时快照后台任务
    snapshot_task = asyncio.create_task(_daily_snapshot_task())
    # 启动 Token 定时清理任务（每 6 小时清一次过期 token）
    cleanup_task = asyncio.create_task(_token_cleanup_task())
    yield
    snapshot_task.cancel()
    cleanup_task.cancel()
    for t in (snapshot_task, cleanup_task):
        try:
            await t
        except asyncio.CancelledError:
            pass


async def _token_cleanup_task():
    """每 6 小时清理一次过期 token，防止 session_tokens 表无限增长"""
    while True:
        try:
            await asyncio.sleep(6 * 3600)
            from database import get_session_factory
            from routers.auth import _cleanup_expired_tokens
            db = get_session_factory()()
            try:
                _cleanup_expired_tokens(db)
                print(f"[TokenCleanup] 过期 token 清理完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            finally:
                db.close()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[TokenCleanup] 清理异常: {e}")


async def _daily_snapshot_task():
    """每天 15:10 自动执行持仓快照（股票收盘 15:00，等10分钟让净值更新）"""
    while True:
        try:
            now = datetime.now()
            # 计算今天或明天的 15:10
            target = now.replace(hour=15, minute=10, second=0, microsecond=0)
            if now >= target:
                # 今天已过 15:10，等到明天
                target += timedelta(days=1)
            sleep_secs = (target - now).total_seconds()
            print(f"[SnapshotTask] 下次自动快照: {target.strftime('%Y-%m-%d %H:%M:%S')}，还需等待 {sleep_secs/3600:.1f}h")
            await asyncio.sleep(sleep_secs)

            # 到时间了，执行快照
            print(f"[SnapshotTask] 开始自动持仓快照 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            from database import get_session_factory
            db = get_session_factory()()
            try:
                # 先刷新净值（调用公共函数，避免重复实现）
                try:
                    from routers.fund import refresh_all_navs
                    result = await refresh_all_navs(db)
                    print(f"[SnapshotTask] 净值刷新完成: {result.get('message', '')}")
                except Exception as e:
                    print(f"[SnapshotTask] 净值刷新异常: {e}")

                # 执行快照
                from routers.fund import _do_take_snapshot
                result = await _do_take_snapshot(db)
                print(f"[SnapshotTask] 快照结果: {result}")
            finally:
                db.close()
        except asyncio.CancelledError:
            print("[SnapshotTask] 定时快照任务已取消")
            raise
        except Exception as e:
            print(f"[SnapshotTask] 异常: {e}")
            await asyncio.sleep(3600)  # 出错后 1 小时重试


app = FastAPI(
    title="All-in-One 个人管理系统",
    description="财务 / 基金 / 骑行 / 徒步 / 物品管理",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
# allow_origins=["*"] 与 allow_credentials=True 不能同时使用（浏览器规范）
# 明确列出允许的来源：开发环境（Vite 5173）+ Electron（file://）+ 本地后端
_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "file://",  # Electron webContents 可能发 file:// origin
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 认证路由（无需 token）
app.include_router(auth.router)

# 业务路由（需要 token 认证）
app.include_router(cycling.router, dependencies=[Depends(auth.verify_token)])
app.include_router(fund.router, dependencies=[Depends(auth.verify_token)])
app.include_router(finance.router, dependencies=[Depends(auth.verify_token)])
app.include_router(hiking.router, dependencies=[Depends(auth.verify_token)])
app.include_router(vehicle.router, dependencies=[Depends(auth.verify_token)])
app.include_router(travel.router, dependencies=[Depends(auth.verify_token)])
app.include_router(backup.router, dependencies=[Depends(auth.verify_token)])
app.include_router(dashboard.router, dependencies=[Depends(auth.verify_token)])
app.include_router(item.router, dependencies=[Depends(auth.verify_token)])
app.include_router(search.router, dependencies=[Depends(auth.verify_token)])
app.include_router(settings.router, dependencies=[Depends(auth.verify_token)])
app.include_router(running.router, dependencies=[Depends(auth.verify_token)])

# 上传目录（支持环境变量 UPLOAD_DIR，Electron 桌面端会设置）
UPLOAD_DIR = get_upload_dir()
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── 前端静态文件服务（Electron 桌面端 / 独立部署）───────────────────────
FRONTEND_DIST = os.environ.get("FRONTEND_DIST", "")
if FRONTEND_DIST and os.path.isdir(FRONTEND_DIST):
    _fe_dist = Path(FRONTEND_DIST).resolve()

    @app.middleware("http")
    async def spa_fallback_middleware(request: Request, call_next):
        """非 API / 非 uploads / 非 health 的请求，由前端 SPA 处理"""
        path = request.url.path
        # API、uploads、health 等路径交给后端正常处理
        if path.startswith("/api/") or path.startswith("/uploads") or path == "/health":
            return await call_next(request)
        # 尝试返回静态文件，否则返回 index.html（SPA fallback）
        file_path = _fe_dist / path.lstrip("/")
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_fe_dist / "index.html"))


@app.get("/")
def root():
    # 如果有前端 dist，中间件已经处理了，这里只用于 API 模式
    return {"status": "ok", "message": "All-in-One API 运行中"}


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="All-in-One 后端服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--data-dir", default=None, help="数据目录（DB + uploads）")
    args = parser.parse_args()

    # --data-dir 优先级最高，覆盖环境变量
    if args.data_dir:
        data_dir = os.path.abspath(args.data_dir)
        os.environ["DB_PATH"] = os.path.join(data_dir, "allinone.db")
        os.environ["UPLOAD_DIR"] = os.path.join(data_dir, "uploads")

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
