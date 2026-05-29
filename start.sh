#!/bin/bash
# All-in-One 一键启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 启动 All-in-One 个人管理系统..."

# 检查是否已有服务在运行
if lsof -iTCP:8000 -sTCP:LISTEN -P > /dev/null 2>&1; then
  echo "⚠️  后端 (port 8000) 已在运行，请先执行 ./stop.sh 停止"
  exit 1
fi
if lsof -iTCP:5173 -sTCP:LISTEN -P > /dev/null 2>&1; then
  echo "⚠️  前端 (port 5173) 已在运行，请先执行 ./stop.sh 停止"
  exit 1
fi

# 启动后端
echo "📦 启动后端 (FastAPI @ port 8000)..."
cd "$SCRIPT_DIR/backend"
nohup ./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
BACKEND_PID=$!

# 等待后端就绪
for i in $(seq 1 10); do
  sleep 1
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端启动成功 → http://localhost:8000"
    echo "   📖 API 文档 → http://localhost:8000/docs"
    break
  fi
  if [ $i -eq 10 ]; then
    echo "❌ 后端启动失败，请检查 backend/uvicorn.log"
    cat uvicorn.log
  fi
done

# 启动前端（--host 0.0.0.0 支持局域网 IP 访问）
echo "🖥  启动前端 (Vue3 @ port 5173)..."
cd "$SCRIPT_DIR/frontend"
nohup npm run dev -- --host 0.0.0.0 > ../frontend.log 2>&1 &
FRONTEND_PID=$!

for i in $(seq 1 10); do
  sleep 1
  if curl -s http://localhost:5173 > /dev/null 2>&1; then
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
    echo "✅ 前端启动成功 → http://localhost:5173"
    [ -n "$LOCAL_IP" ] && echo "   📡 局域网访问 → http://${LOCAL_IP}:5173"
    break
  fi
  if [ $i -eq 10 ]; then
    echo "❌ 前端启动失败，请检查 frontend.log"
    cat ../frontend.log
  fi
done

echo ""
echo "按 Ctrl+C 停止所有服务，或执行 ./stop.sh"

# 捕获退出信号，清理进程
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '已停止所有服务'; exit 0" INT TERM

wait
