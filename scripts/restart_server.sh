#!/bin/bash
# 重启服务器脚本

echo "=========================================="
echo "重启服务器脚本"
echo "=========================================="
echo ""

# 1. 查找并停止现有服务
echo "1. 查找运行中的服务..."
PIDS=$(ps aux | grep -E "python.*server/start.py|uvicorn.*main:app" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "   ℹ️  未找到运行中的服务"
else
    echo "   📋 找到进程: $PIDS"
    echo "   🛑 停止服务..."
    for PID in $PIDS; do
        kill $PID 2>/dev/null
        echo "      ✅ 已停止进程 $PID"
    done
    sleep 2
fi

# 2. 检查端口是否释放
echo ""
echo "2. 检查端口8001..."
if lsof -ti:8001 > /dev/null 2>&1; then
    echo "   ⚠️  端口8001仍被占用，强制释放..."
    lsof -ti:8001 | xargs kill -9 2>/dev/null
    sleep 1
fi

# 3. 启动服务
echo ""
echo "3. 启动服务器..."
cd "$(dirname "$0")/.."
python3 server/start.py &
SERVER_PID=$!

# 4. 等待服务启动
echo "   ⏳ 等待服务启动（5秒）..."
sleep 5

# 5. 检查服务状态
echo ""
echo "4. 检查服务状态..."
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "   ✅ 服务启动成功"
    echo "   📋 进程ID: $SERVER_PID"
    echo ""
    echo "5. 测试静态文件访问..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/frontend/login.html)
    if [ "$RESPONSE" = "200" ]; then
        echo "   ✅ 静态文件可以访问（中间件修复成功！）"
    else
        echo "   ❌ 静态文件仍被拦截（HTTP $RESPONSE）"
        echo "   ⚠️  可能需要检查中间件配置"
    fi
else
    echo "   ❌ 服务启动失败"
    echo "   📋 查看日志: tail -f logs/server_8001.log"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 服务器重启完成"
echo "=========================================="

