#!/bin/bash
# All-in-One 一键停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🛑 停止 All-in-One 个人管理系统..."

KILLED=0

# 停止后端 (uvicorn @ 8000)
BACKEND_PIDS=$(lsof -iTCP:8000 -sTCP:LISTEN -P -t 2>/dev/null)
if [ -n "$BACKEND_PIDS" ]; then
  kill $BACKEND_PIDS 2>/dev/null
  echo "✅ 已停止后端 (port 8000)"
  KILLED=1
fi

# 停止前端 (vite @ 5173 / 5174)
for PORT in 5173 5174; do
  PIDS=$(lsof -iTCP:$PORT -sTCP:LISTEN -P -t 2>/dev/null)
  if [ -n "$PIDS" ]; then
    kill $PIDS 2>/dev/null
    echo "✅ 已停止前端 (port $PORT)"
    KILLED=1
  fi
done

if [ $KILLED -eq 0 ]; then
  echo "ℹ️  没有发现运行中的服务"
else
  echo ""
  LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
  echo "所有服务已停止 ✅"
  [ -n "$LOCAL_IP" ] && echo "（之前访问地址：http://${LOCAL_IP}:5173）"
fi
