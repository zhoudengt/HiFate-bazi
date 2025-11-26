#!/bin/bash
# 停止办公桌风水微服务

set -e

echo "🛑 停止办公桌风水微服务..."

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 服务配置
SERVICE_NAME="desk_fengshui"
SERVICE_PORT=9010
PID_FILE="logs/${SERVICE_NAME}_${SERVICE_PORT}.pid"

# 检查PID文件
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  服务未运行（未找到PID文件）"
    exit 0
fi

# 读取PID
SERVICE_PID=$(cat "$PID_FILE")

# 检查进程是否存在
if ! ps -p "$SERVICE_PID" > /dev/null 2>&1; then
    echo "⚠️  服务未运行（进程不存在）"
    rm -f "$PID_FILE"
    exit 0
fi

# 停止服务
echo "停止服务: ${SERVICE_NAME} (PID: $SERVICE_PID)"
kill -15 "$SERVICE_PID"

# 等待进程结束
for i in {1..10}; do
    if ! ps -p "$SERVICE_PID" > /dev/null 2>&1; then
        echo "✅ 服务已停止"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# 强制kill
echo "⚠️  服务未响应，强制停止..."
kill -9 "$SERVICE_PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "✅ 服务已强制停止"

