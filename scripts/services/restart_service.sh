#!/bin/bash
# 重启服务脚本

echo "🔄 正在重启服务..."

# 停止当前服务
echo "1. 停止当前服务..."
PID=$(lsof -ti:8001)
if [ ! -z "$PID" ]; then
    kill $PID
    echo "   已停止进程: $PID"
    sleep 2
else
    echo "   服务未运行"
fi

# 启动服务
echo "2. 启动服务..."
cd "$(dirname "$0")/.."
python server/start.py &

# 等待服务启动
echo "3. 等待服务启动..."
sleep 5

# 检查服务状态
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "📝 测试运势接口："
    echo "curl -X POST http://localhost:8001/api/v1/fortune/daily \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"constellation\": \"白羊座\"}'"
else
    echo "❌ 服务启动失败，请检查日志"
fi

