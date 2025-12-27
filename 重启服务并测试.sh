#!/bin/bash
# 重启服务并测试统一接口

echo "=========================================="
echo "1. 查找并停止现有服务"
echo "=========================================="

# 查找占用8001端口的进程
PID=$(lsof -ti :8001 2>/dev/null | head -1)

if [ -n "$PID" ]; then
    echo "找到服务进程: $PID"
    echo "停止服务..."
    kill $PID
    sleep 2
    
    # 如果还在运行，强制停止
    if kill -0 $PID 2>/dev/null; then
        echo "强制停止服务..."
        kill -9 $PID
        sleep 1
    fi
    echo "✅ 服务已停止"
else
    echo "⚠️ 未找到运行在8001端口的服务"
fi

echo ""
echo "=========================================="
echo "2. 启动服务"
echo "=========================================="

cd "$(dirname "$0")"

# 激活虚拟环境并启动服务
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "⚠️ 未找到虚拟环境，使用系统Python"
fi

# 后台启动服务
echo "启动服务（后台运行）..."
nohup python server/main.py > logs/server.log 2>&1 &
SERVER_PID=$!

echo "服务进程ID: $SERVER_PID"
echo "等待服务启动（5秒）..."
sleep 5

# 检查服务是否启动成功
if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✅ 服务已启动"
else
    echo "❌ 服务启动失败，请查看 logs/server.log"
    exit 1
fi

echo ""
echo "=========================================="
echo "3. 测试统一接口"
echo "=========================================="

# 等待服务完全启动
sleep 2

# 测试接口
echo "调用统一接口..."
curl -X POST "http://localhost:8001/api/v1/bazi/data" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1979-07-22",
    "solar_time": "07:15",
    "gender": "male",
    "modules": {
      "bazi": true,
      "wangshuai": true,
      "xishen_jishen": true,
      "dayun": {"mode": "count", "count": 8},
      "special_liunian": {"count": 8}
    },
    "use_cache": true,
    "parallel": true,
    "verify_consistency": true
  }' 2>&1 | python3 -m json.tool 2>/dev/null || cat

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo "服务进程ID: $SERVER_PID"
echo "日志文件: logs/server.log"
echo ""
echo "如需停止服务，执行: kill $SERVER_PID"

