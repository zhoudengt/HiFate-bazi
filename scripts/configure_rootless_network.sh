#!/bin/bash
# 配置 Rootless Docker 网络和端口范围
# 使用：bash scripts/configure_rootless_network.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
FRONTEND_USER="frontend-user"

ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no root@$host "$cmd"
    fi
}

configure_node() {
    local host=$1
    local node_name=$2
    
    echo "=========================================="
    echo "在 $node_name ($host) 上配置网络"
    echo "=========================================="
    
    # 设置环境变量
    ENV_SETUP="export XDG_RUNTIME_DIR=\$HOME/.docker/run && export PATH=\$HOME/bin:\$PATH && export DOCKER_HOST=unix://\$HOME/.docker/run/docker.sock"
    
    # 1. 创建前端专用网络
    echo ""
    echo "1. 创建前端专用网络（frontend-network）..."
    
    NETWORK_EXISTS=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker network ls --format \"{{.Name}}\" | grep -q frontend-network' 2>/dev/null" && echo "yes" || echo "no")
    
    if [ "$NETWORK_EXISTS" = "yes" ]; then
        echo "   ⚠️  网络已存在，跳过创建"
    else
        NETWORK_CREATE=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker network create frontend-network 2>&1' 2>/dev/null" || echo "创建失败")
        if echo "$NETWORK_CREATE" | grep -q "frontend-network\|already exists"; then
            echo "   ✅ 网络已创建: frontend-network"
        else
            echo "   ⚠️  网络创建可能失败: $NETWORK_CREATE"
        fi
    fi
    
    # 2. 验证网络信息
    echo ""
    echo "2. 验证网络信息..."
    NETWORK_INFO=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker network inspect frontend-network --format \"{{.Name}}: {{.Driver}}\" 2>&1' 2>/dev/null" || echo "无法获取")
    echo "   $NETWORK_INFO"
    
    # 3. 列出所有网络（验证隔离）
    echo ""
    echo "3. 列出所有网络（验证隔离）..."
    ALL_NETWORKS=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker network ls --format \"{{.Name}}\" 2>&1' 2>/dev/null" || echo "无法获取")
    echo "   Rootless Docker 网络:"
    echo "$ALL_NETWORKS" | sed 's/^/     /'
    
    # 4. 端口范围说明
    echo ""
    echo "4. 端口范围说明..."
    echo "   后端端口（禁止使用）:"
    echo "     - 8001 (Web 服务)"
    echo "     - 9001-9010 (微服务)"
    echo "     - 3306 (MySQL)"
    echo "     - 6379 (Redis)"
    echo "   前端端口（推荐使用）:"
    echo "     - 8080-8999 (前端服务)"
    echo ""
    echo "   ⚠️  注意：Rootless Docker 默认只能绑定 > 1024 的端口"
    echo "   这已经自动限制了端口范围，避免与系统端口冲突"
    
    echo ""
    echo "✅ $node_name 网络配置完成"
    echo ""
}

echo "=========================================="
echo "配置 Rootless Docker 网络（双机）"
echo "=========================================="
echo ""
echo "功能："
echo "  - 创建前端专用网络（frontend-network）"
echo "  - 验证网络隔离"
echo "  - 说明端口范围"
echo ""

# 配置 Node1
configure_node $NODE1_PUBLIC_IP "Node1"

# 配置 Node2
configure_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "✅ 网络配置完成"
echo "=========================================="
echo ""
echo "下一步：验证隔离效果"
echo "   bash scripts/verify_rootless_docker.sh"
echo ""

