#!/bin/bash
# 启动办公桌风水微服务

set -e

echo "🚀 启动办公桌风水微服务..."

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 服务配置
SERVICE_NAME="desk_fengshui"
SERVICE_PORT=9010
PID_FILE="logs/${SERVICE_NAME}_${SERVICE_PORT}.pid"
LOG_FILE="logs/${SERVICE_NAME}_${SERVICE_PORT}.log"

# 检查是否已启动
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  服务已在运行 (PID: $OLD_PID)"
        echo "   如需重启，请先运行: ./scripts/stop_desk_fengshui_service.sh"
        exit 1
    else
        echo "⚠️  发现旧的PID文件，清理中..."
        rm -f "$PID_FILE"
    fi
fi

# 启动服务
echo "启动服务: ${SERVICE_NAME} (端口: ${SERVICE_PORT})"
nohup python3.9 services/desk_fengshui/grpc_server.py --port $SERVICE_PORT \
    > "$LOG_FILE" 2>&1 &

SERVICE_PID=$!
echo $SERVICE_PID > "$PID_FILE"

# 等待服务启动
sleep 2

# 检查服务状态
if ps -p "$SERVICE_PID" > /dev/null 2>&1; then
    echo "✅ 服务启动成功"
    echo "   PID: $SERVICE_PID"
    echo "   端口: $SERVICE_PORT"
    echo "   日志: $LOG_FILE"
else
    echo "❌ 服务启动失败，请查看日志: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi

