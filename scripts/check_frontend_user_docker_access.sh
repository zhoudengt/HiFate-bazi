#!/bin/bash
# 检查 frontend-user 的 Docker 访问权限
# 使用：bash scripts/check_frontend_user_docker_access.sh

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

check_node() {
    local host=$1
    local node_name=$2
    
    echo "检查 $node_name ($host)..."
    echo "----------------------------------------"
    
    # 1. 检查是否在 docker 组中
    echo "1. frontend-user 是否在 docker 组中？"
    GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    if echo "$GROUPS" | grep -q "docker"; then
        echo "   ⚠️  是，frontend-user 在 docker 组中（有风险）"
        echo "   所属组: $GROUPS"
    else
        echo "   ✅ 否，frontend-user 不在 docker 组中（安全）"
        echo "   所属组: $GROUPS"
    fi
    
    # 2. 检查能否执行 docker 命令
    echo ""
    echo "2. frontend-user 能否执行 docker ps？"
    DOCKER_OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker ps 2>&1'" 2>/dev/null || echo "")
    if echo "$DOCKER_OUTPUT" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "   ✅ 否，无法执行 docker 命令（安全）"
    else
        echo "   ⚠️  是，可以执行 docker 命令（有风险）"
        echo "   输出: $(echo "$DOCKER_OUTPUT" | head -2)"
    fi
    
    # 3. 检查 docker.sock 权限
    echo ""
    echo "3. /var/run/docker.sock 权限？"
    SOCK_INFO=$(ssh_exec $host "ls -l /var/run/docker.sock 2>/dev/null" || echo "")
    echo "   $SOCK_INFO"
    if echo "$SOCK_INFO" | grep -q "docker.*docker"; then
        SOCK_GROUP=$(echo "$SOCK_INFO" | awk '{print $4}')
        echo "   Socket 所属组: $SOCK_GROUP"
        if [ "$SOCK_GROUP" = "docker" ] && echo "$GROUPS" | grep -q "docker"; then
            echo "   ⚠️  frontend-user 在 docker 组中，可以访问 socket（有风险）"
        else
            echo "   ✅ frontend-user 不在 docker 组中，无法访问 socket（安全）"
        fi
    fi
    
    echo ""
}

echo "=========================================="
echo "检查 frontend-user 的 Docker 访问权限"
echo "=========================================="
echo ""

check_node $NODE1_PUBLIC_IP "Node1"
check_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "结论"
echo "=========================================="
echo ""
echo "如果 frontend-user 在 docker 组中："
echo "  ⚠️  风险：可以执行 docker 命令，可以部署 Docker 容器"
echo "  ⚠️  风险：可以看到所有 Docker 容器"
echo "  ⚠️  风险：可以停止/删除/重启容器"
echo ""
echo "建议："
echo "  - 从 docker 组中移除 frontend-user: usermod -G frontend-group frontend-user"
echo "  - 确保 frontend-user 不在 docker 组中"
echo ""

