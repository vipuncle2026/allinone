#!/bin/bash
# All-in-One 一键停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID_FILE="$SCRIPT_DIR/.allinone-backend.pid"
FRONTEND_PID_FILE="$SCRIPT_DIR/.allinone-frontend.pid"

echo "🛑 停止 All-in-One 个人管理系统..."

KILLED=0

stop_managed_process() {
  local label="$1"
  local pid_file="$2"
  local expected="$3"
  [ -f "$pid_file" ] || return
  local pid command
  pid="$(cat "$pid_file")"
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  if [[ "$pid" =~ ^[0-9]+$ ]] && [[ "$command" == *"$expected"* ]]; then
    kill "$pid" 2>/dev/null
    echo "✅ 已停止${label} (PID $pid)"
    KILLED=1
  elif [ -n "$command" ]; then
    echo "⚠️  忽略过期的${label} PID 文件（PID $pid 已属于其他进程）"
  fi
  rm -f "$pid_file"
}

stop_managed_process "后端" "$BACKEND_PID_FILE" "uvicorn"
stop_managed_process "前端" "$FRONTEND_PID_FILE" "vite"

if [ $KILLED -eq 0 ]; then
  echo "ℹ️  没有发现运行中的服务"
else
  echo ""
  LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
  echo "所有服务已停止 ✅"
  [ -n "$LOCAL_IP" ] && echo "（之前访问地址：http://${LOCAL_IP}:5173）"
fi
