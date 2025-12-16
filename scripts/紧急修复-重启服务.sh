#!/bin/bash
# 紧急修复：重启服务以应用中间件修复

echo "=========================================="
echo "紧急修复：重启服务"
echo "=========================================="
echo ""

# 查找服务进程
echo "1. 查找服务进程..."
PIDS=$(ps aux | grep -E "python.*server/start.py|uvicorn.*main:app" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "   ⚠️  未找到运行中的服务"
    echo "   启动服务..."
    cd "$(dirname "$0")/.."
    nohup python3 server/start.py > logs/server_8001.log 2>&1 &
    echo "   ✅ 服务已启动（后台运行）"
    echo "   📋 查看日志: tail -f logs/server_8001.log"
    sleep 5
else
    echo "   📋 找到进程: $PIDS"
    echo ""
    echo "2. 停止服务..."
    for PID in $PIDS; do
        echo "   停止进程 $PID..."
        kill $PID 2>/dev/null
    done
    
    echo "   等待进程退出（3秒）..."
    sleep 3
    
    # 强制杀死（如果还在运行）
    for PID in $PIDS; do
        if kill -0 $PID 2>/dev/null; then
            echo "   强制停止进程 $PID..."
            kill -9 $PID 2>/dev/null
        fi
    done
    
    echo ""
    echo "3. 启动服务..."
    cd "$(dirname "$0")/.."
    nohup python3 server/start.py > logs/server_8001.log 2>&1 &
    NEW_PID=$!
    echo "   ✅ 服务已启动（进程ID: $NEW_PID）"
    echo "   📋 查看日志: tail -f logs/server_8001.log"
    
    echo ""
    echo "4. 等待服务就绪（5秒）..."
    sleep 5
fi

# 验证服务
echo ""
echo "5. 验证服务..."
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "   ✅ 服务健康检查通过"
    
    echo ""
    echo "6. 测试登录页面..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/frontend/login.html)
    CONTENT=$(curl -s http://localhost:8001/frontend/login.html | head -n 1)
    
    if [ "$RESPONSE" = "200" ]; then
        if [[ "$CONTENT" == *"<!DOCTYPE html>"* ]] || [[ "$CONTENT" == *"<html"* ]]; then
            echo "   ✅ 登录页面可以访问（HTML内容正常）"
            echo ""
            echo "=========================================="
            echo "✅ 修复成功！现在可以访问登录页面了"
            echo "=========================================="
            echo ""
            echo "🌐 访问: http://localhost:8001/frontend/login.html"
        else
            echo "   ⚠️  返回状态200，但内容异常: ${CONTENT:0:100}"
        fi
    else
        echo "   ❌ 登录页面仍被拦截（HTTP $RESPONSE）"
        echo "   📋 检查日志: tail -20 logs/server_8001.log"
    fi
else
    echo "   ❌ 服务健康检查失败"
    echo "   📋 查看日志: tail -20 logs/server_8001.log"
fi

