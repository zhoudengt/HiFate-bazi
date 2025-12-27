#!/bin/bash
# 检查 Docker Rootless 系统要求
# 使用：bash scripts/check_rootless_requirements.sh

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
    
    echo "=========================================="
    echo "检查 $node_name ($host) 系统要求"
    echo "=========================================="
    
    # 1. 检查系统版本
    echo ""
    echo "1. 检查系统版本..."
    OS_INFO=$(ssh_exec $host "cat /etc/os-release | grep -E '^NAME=|^VERSION=' | head -2" || echo "")
    echo "   $OS_INFO"
    
    # 2. 检查 systemd 支持
    echo ""
    echo "2. 检查 systemd 支持..."
    if ssh_exec $host "systemctl --version > /dev/null 2>&1" 2>/dev/null; then
        SYSTEMD_VERSION=$(ssh_exec $host "systemctl --version | head -1" || echo "")
        echo "   ✅ systemd 已安装: $SYSTEMD_VERSION"
    else
        echo "   ❌ systemd 未安装或不可用"
        return 1
    fi
    
    # 3. 检查 user namespaces 支持
    echo ""
    echo "3. 检查 user namespaces 支持..."
    if ssh_exec $host "test -f /proc/sys/user/max_user_namespaces && [ \$(cat /proc/sys/user/max_user_namespaces) -gt 0 ]" 2>/dev/null; then
        MAX_NAMESPACES=$(ssh_exec $host "cat /proc/sys/user/max_user_namespaces" || echo "0")
        echo "   ✅ user namespaces 已启用: max_user_namespaces=$MAX_NAMESPACES"
    else
        echo "   ⚠️  user namespaces 可能未启用"
        echo "   需要设置: sysctl user.max_user_namespaces=28633"
    fi
    
    # 4. 检查 frontend-user 是否存在
    echo ""
    echo "4. 检查 frontend-user 是否存在..."
    if ssh_exec $host "id $FRONTEND_USER > /dev/null 2>&1" 2>/dev/null; then
        USER_INFO=$(ssh_exec $host "id $FRONTEND_USER" || echo "")
        echo "   ✅ frontend-user 存在: $USER_INFO"
    else
        echo "   ❌ frontend-user 不存在"
        return 1
    fi
    
    # 5. 检查 frontend-user 是否在 docker 组中
    echo ""
    echo "5. 检查 frontend-user 是否在 docker 组中..."
    GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    if echo "$GROUPS" | grep -q "docker"; then
        echo "   ⚠️  frontend-user 在 docker 组中（需要移除）"
    else
        echo "   ✅ frontend-user 不在 docker 组中（正确）"
    fi
    
    # 6. 检查 /opt/hifate-frontend 目录
    echo ""
    echo "6. 检查 /opt/hifate-frontend 目录..."
    if ssh_exec $host "test -d /opt/hifate-frontend" 2>/dev/null; then
        DIR_PERMS=$(ssh_exec $host "ls -ld /opt/hifate-frontend" || echo "")
        echo "   ✅ 目录存在: $DIR_PERMS"
    else
        echo "   ⚠️  目录不存在，将创建"
    fi
    
    # 7. 检查是否已安装 Docker Rootless
    echo ""
    echo "7. 检查是否已安装 Docker Rootless..."
    if ssh_exec $host "su - $FRONTEND_USER -c 'test -f \$HOME/bin/dockerd-rootless.sh' 2>/dev/null" 2>/dev/null; then
        echo "   ⚠️  Docker Rootless 已安装（可能需要重新配置）"
    else
        echo "   ✅ Docker Rootless 未安装（需要安装）"
    fi
    
    # 8. 检查 Rootless Docker 服务状态
    echo ""
    echo "8. 检查 Rootless Docker 服务状态..."
    SERVICE_STATUS=$(ssh_exec $host "su - $FRONTEND_USER -c 'systemctl --user status docker 2>&1 | head -3' || echo '未运行'" || echo "无法检查")
    echo "   $SERVICE_STATUS"
    
    echo ""
    echo "✅ $node_name 检查完成"
    echo ""
}

echo "=========================================="
echo "检查 Docker Rootless 系统要求（双机）"
echo "=========================================="
echo ""

# 检查 Node1
check_node $NODE1_PUBLIC_IP "Node1"

# 检查 Node2
check_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "✅ 检查完成"
echo "=========================================="
echo ""
echo "如果发现问题，请先解决后再继续安装。"
echo ""

