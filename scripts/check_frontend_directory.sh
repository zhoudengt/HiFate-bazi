#!/bin/bash
# 检查服务器上的 frontend 目录状态

set -e

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# SSH 执行函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    fi
}

echo "=========================================="
echo "检查服务器 frontend 目录状态"
echo "=========================================="
echo ""

# 检查 Node1
echo "📋 检查 Node1 ($NODE1_PUBLIC_IP)..."
if ssh_exec $NODE1_PUBLIC_IP "test -d $PROJECT_DIR/frontend" 2>/dev/null; then
    echo "✅ Node1: frontend 目录存在"
    ssh_exec $NODE1_PUBLIC_IP "ls -la $PROJECT_DIR/frontend | head -10"
else
    echo "❌ Node1: frontend 目录不存在"
fi

if ssh_exec $NODE1_PUBLIC_IP "test -d $PROJECT_DIR/local_frontend" 2>/dev/null; then
    echo "✅ Node1: local_frontend 目录存在"
else
    echo "❌ Node1: local_frontend 目录不存在"
fi

echo ""

# 检查 Node2
echo "📋 检查 Node2 ($NODE2_PUBLIC_IP)..."
if ssh_exec $NODE2_PUBLIC_IP "test -d $PROJECT_DIR/frontend" 2>/dev/null; then
    echo "✅ Node2: frontend 目录存在"
    ssh_exec $NODE2_PUBLIC_IP "ls -la $PROJECT_DIR/frontend | head -10"
else
    echo "❌ Node2: frontend 目录不存在"
fi

if ssh_exec $NODE2_PUBLIC_IP "test -d $PROJECT_DIR/local_frontend" 2>/dev/null; then
    echo "✅ Node2: local_frontend 目录存在"
else
    echo "❌ Node2: local_frontend 目录不存在"
fi

echo ""
echo "=========================================="
echo "检查 Git 仓库中的 frontend 目录"
echo "=========================================="

# 检查本地 Git 仓库
if [ -d "frontend" ]; then
    echo "✅ 本地: frontend 目录存在（但不在 Git 中）"
else
    echo "❌ 本地: frontend 目录不存在"
fi

if [ -d "local_frontend" ]; then
    echo "✅ 本地: local_frontend 目录存在"
else
    echo "❌ 本地: local_frontend 目录不存在"
fi

echo ""
echo "检查 Git 跟踪状态..."
if git ls-files frontend/ 2>/dev/null | head -1; then
    echo "⚠️  Git 仓库中仍有 frontend 目录的跟踪记录"
else
    echo "✅ Git 仓库中已没有 frontend 目录（已重命名为 local_frontend）"
fi

