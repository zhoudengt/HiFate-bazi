#!/bin/bash
# 重启服务器脚本 - 彻底清理端口占用

cd "$(dirname "$0")"

echo "正在停止现有服务器..."

# ✅ 彻底清理所有占用8001端口的进程
PIDS=$(lsof -ti:8001 2>/dev/null)
if [ ! -z "$PIDS" ]; then
    echo "找到占用端口8001的进程: $PIDS"
    
    # 先尝试优雅关闭（SIGTERM）
    for PID in $PIDS; do
        echo "  正在停止进程 $PID..."
        kill $PID 2>/dev/null
    done
    
    # 等待3秒让进程优雅退出
    sleep 3
    
    # 检查是否还有进程占用端口
    REMAINING_PIDS=$(lsof -ti:8001 2>/dev/null)
    if [ ! -z "$REMAINING_PIDS" ]; then
        echo "  仍有进程占用端口，强制终止..."
        # 强制杀死所有剩余进程
        for PID in $REMAINING_PIDS; do
            echo "    强制终止进程 $PID..."
            kill -9 $PID 2>/dev/null
        done
        sleep 2
    fi
    
    # 再次检查确保端口已释放
    FINAL_CHECK=$(lsof -ti:8001 2>/dev/null)
    if [ -z "$FINAL_CHECK" ]; then
        echo "✓ 所有进程已停止，端口8001已释放"
    else
        echo "⚠️  警告：仍有进程占用端口: $FINAL_CHECK"
        echo "  尝试使用 sudo 强制清理..."
        for PID in $FINAL_CHECK; do
            sudo kill -9 $PID 2>/dev/null || true
        done
        sleep 1
    fi
else
    echo "未找到运行中的服务器"
fi

# 额外清理：查找可能的uvicorn进程
echo "清理可能的uvicorn残留进程..."
pkill -f "uvicorn.*8001" 2>/dev/null || true
pkill -f "server/start.py" 2>/dev/null || true
sleep 1

# 最终确认端口已释放
FINAL_PIDS=$(lsof -ti:8001 2>/dev/null)
if [ ! -z "$FINAL_PIDS" ]; then
    echo "⚠️  警告：端口8001仍被占用，进程: $FINAL_PIDS"
    echo "  请手动检查并终止这些进程"
    exit 1
fi

echo ""
echo "正在启动服务器..."
# 使用虚拟环境启动
.venv/bin/python server/start.py > logs/web_app_8001.log 2>&1 &

# 等待服务器启动
sleep 5

# 检查是否启动成功
if lsof -ti:8001 > /dev/null 2>&1; then
    echo "✓ 服务器已启动（端口 8001）"
    echo "日志文件: logs/web_app_8001.log"
    echo ""
    echo "新功能路由："
    echo "  - LLM 生成: POST /api/v1/bazi/llm-generate"
    echo "  - 对话接口: POST /api/v1/bazi/chat/create"
    echo "  - 一事一卦: POST /api/v1/bazi/yigua/divinate"
else
    echo "✗ 服务器启动失败，请查看日志: logs/web_app_8001.log"
    tail -20 logs/web_app_8001.log
    exit 1
fi

