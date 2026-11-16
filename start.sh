#!/bin/bash
# All-in-One 一键启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""
BACKEND_PID_FILE="$SCRIPT_DIR/.allinone-backend.pid"
FRONTEND_PID_FILE="$SCRIPT_DIR/.allinone-frontend.pid"

cleanup() {
  trap - INT TERM EXIT
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null
    rm -f "$BACKEND_PID_FILE"
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null
    rm -f "$FRONTEND_PID_FILE"
  fi
}

trap cleanup INT TERM EXIT

check_existing_process() {
  local label="$1"
  local pid_file="$2"
  local expected="$3"
  [ -f "$pid_file" ] || return 0

  local pid command
  pid="$(cat "$pid_file")"
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  if [[ "$pid" =~ ^[0-9]+$ ]] && [[ "$command" == *"$expected"* ]]; then
    echo "❌ ${label}已在运行 (PID $pid)，请先执行 ./stop.sh"
    exit 1
  fi
  rm -f "$pid_file"
}

check_existing_process "后端" "$BACKEND_PID_FILE" "uvicorn"
check_existing_process "前端" "$FRONTEND_PID_FILE" "vite"

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
nohup ./venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &
BACKEND_PID=$!
printf '%s\n' "$BACKEND_PID" > "$BACKEND_PID_FILE"

# 等待后端就绪
BACKEND_READY=0
for i in $(seq 1 10); do
  sleep 1
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "❌ 后端进程已退出，日志："
    cat uvicorn.log
    break
  fi
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端启动成功 → http://localhost:8000"
    echo "   📖 API 文档 → http://localhost:8000/docs"
    BACKEND_READY=1
    break
  fi
  if [ $i -eq 10 ]; then
    echo "❌ 后端启动失败，请检查 backend/uvicorn.log"
    cat uvicorn.log
  fi
done
[ "$BACKEND_READY" -eq 1 ] || exit 1

# 启动前端（--host 0.0.0.0 支持局域网 IP 访问）
echo "🖥  启动前端 (Vue3 @ port 5173)..."
cd "$SCRIPT_DIR/frontend"
nohup ./node_modules/.bin/vite --host 0.0.0.0 --port 5173 > ../frontend.log 2>&1 &
FRONTEND_PID=$!
printf '%s\n' "$FRONTEND_PID" > "$FRONTEND_PID_FILE"

FRONTEND_READY=0
for i in $(seq 1 10); do
  sleep 1
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "❌ 前端进程已退出，日志："
    cat ../frontend.log
    break
  fi
  if curl -s http://localhost:5173 > /dev/null 2>&1; then
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
    echo "✅ 前端启动成功 → http://localhost:5173"
    [ -n "$LOCAL_IP" ] && echo "   📡 局域网访问 → http://${LOCAL_IP}:5173"
    FRONTEND_READY=1
    break
  fi
  if [ $i -eq 10 ]; then
    echo "❌ 前端启动失败，请检查 frontend.log"
    cat ../frontend.log
  fi
done
[ "$FRONTEND_READY" -eq 1 ] || exit 1

echo ""
echo "按 Ctrl+C 停止所有服务，或执行 ./stop.sh"

wait
