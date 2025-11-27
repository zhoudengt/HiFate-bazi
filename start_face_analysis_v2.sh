#!/bin/bash
# -*- coding: utf-8 -*-
# 启动面相分析V2服务

set -e

echo "========================================"
echo "启动面相分析V2服务"
echo "========================================"

# 切换到项目根目录
cd "$(dirname "$0")"

# 激活虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python3 -m venv .venv"
    exit 1
fi

source .venv/bin/activate

# 检查依赖
echo "📦 检查依赖..."
python3 -c "import mediapipe" 2>/dev/null || {
    echo "⚠️  MediaPipe未安装，正在安装..."
    bash scripts/setup_mediapipe.sh
}

# 启动主服务（包含API）
echo "🚀 启动主服务..."
.venv/bin/python server/main.py &
MAIN_PID=$!

echo "✅ 服务启动成功！"
echo ""
echo "访问地址："
echo "  - 前端页面: http://localhost:8001/face-analysis-v2.html"
echo "  - API文档: http://localhost:8001/docs"
echo "  - 健康检查: http://localhost:8001/api/v2/face/health"
echo ""
echo "服务PID: $MAIN_PID"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待中断信号
wait $MAIN_PID

