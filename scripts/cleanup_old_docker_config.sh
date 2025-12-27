#!/bin/bash
# 清理旧的 Docker 配置（sudo、包装脚本）
# 使用：bash scripts/cleanup_old_docker_config.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
FRONTEND_USER="frontend-user"
SUDOERS_FILE="/etc/sudoers.d/frontend-docker"
DOCKER_WRAPPER="/usr/local/bin/docker-frontend"

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

cleanup_node() {
    local host=$1
    local node_name=$2
    
    echo "=========================================="
    echo "在 $node_name ($host) 上清理旧配置"
    echo "=========================================="
    
    # 1. 备份旧配置
    echo ""
    echo "1. 备份旧配置..."
    BACKUP_DIR="/root/frontend_docker_config_backup_$(date +%Y%m%d_%H%M%S)"
    ssh_exec $host "mkdir -p $BACKUP_DIR" 2>/dev/null || true
    
    # 备份 sudoers 文件
    if ssh_exec $host "test -f $SUDOERS_FILE" 2>/dev/null; then
        ssh_exec $host "cp $SUDOERS_FILE $BACKUP_DIR/frontend-docker.sudoers 2>/dev/null" || true
        echo "   ✅ sudoers 文件已备份到 $BACKUP_DIR"
    else
        echo "   ⚠️  sudoers 文件不存在，跳过备份"
    fi
    
    # 备份包装脚本
    if ssh_exec $host "test -f $DOCKER_WRAPPER" 2>/dev/null; then
        ssh_exec $host "cp $DOCKER_WRAPPER $BACKUP_DIR/docker-frontend.sh 2>/dev/null" || true
        echo "   ✅ 包装脚本已备份到 $BACKUP_DIR"
    else
        echo "   ⚠️  包装脚本不存在，跳过备份"
    fi
    
    # 2. 移除 sudoers 配置
    echo ""
    echo "2. 移除 sudoers 配置..."
    if ssh_exec $host "test -f $SUDOERS_FILE" 2>/dev/null; then
        ssh_exec $host "rm -f $SUDOERS_FILE" 2>/dev/null || {
            echo "   ❌ 移除 sudoers 文件失败"
            return 1
        }
        echo "   ✅ sudoers 文件已移除"
    else
        echo "   ⚠️  sudoers 文件不存在，跳过"
    fi
    
    # 3. 移除包装脚本
    echo ""
    echo "3. 移除包装脚本..."
    if ssh_exec $host "test -f $DOCKER_WRAPPER" 2>/dev/null; then
        ssh_exec $host "rm -f $DOCKER_WRAPPER" 2>/dev/null || {
            echo "   ❌ 移除包装脚本失败"
            return 1
        }
        echo "   ✅ 包装脚本已移除"
    else
        echo "   ⚠️  包装脚本不存在，跳过"
    fi
    
    # 4. 验证 frontend-user 不在 docker 组中
    echo ""
    echo "4. 验证 frontend-user 不在 docker 组中..."
    GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    if echo "$GROUPS" | grep -q "docker"; then
        echo "   ⚠️  frontend-user 仍在 docker 组中，正在移除..."
        ssh_exec $host "gpasswd -d $FRONTEND_USER docker" 2>/dev/null || {
            echo "   ❌ 从 docker 组移除失败"
        }
        echo "   ✅ 已从 docker 组移除"
    else
        echo "   ✅ frontend-user 不在 docker 组中（正确）"
    fi
    
    # 5. 验证无法直接使用 docker 命令
    echo ""
    echo "5. 验证无法直接使用 docker 命令（应该失败）..."
    DOCKER_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker ps 2>&1' 2>/dev/null" || echo "无法执行")
    if echo "$DOCKER_TEST" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "   ✅ 无法直接使用 docker 命令（正确）"
    else
        echo "   ⚠️  仍然可以使用 docker 命令（可能仍在 docker 组中）"
    fi
    
    # 6. 验证可以使用 Rootless Docker
    echo ""
    echo "6. 验证可以使用 Rootless Docker（应该成功）..."
    ROOTLESS_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'export XDG_RUNTIME_DIR=\$HOME/.docker/run && export PATH=\$HOME/bin:\$PATH && export DOCKER_HOST=unix://\$HOME/.docker/run/docker.sock && docker ps 2>&1' 2>/dev/null" || echo "无法执行")
    if echo "$ROOTLESS_TEST" | grep -q "CONTAINER\|NAMES\|^$"; then
        echo "   ✅ 可以使用 Rootless Docker"
    else
        echo "   ⚠️  Rootless Docker 可能未启动"
        echo "   输出: $ROOTLESS_TEST"
    fi
    
    echo ""
    echo "✅ $node_name 清理完成"
    echo "   备份位置: $BACKUP_DIR"
    echo ""
}

echo "=========================================="
echo "清理旧的 Docker 配置（双机）"
echo "=========================================="
echo ""
echo "功能："
echo "  - 移除 sudo 配置（/etc/sudoers.d/frontend-docker）"
echo "  - 移除包装脚本（/usr/local/bin/docker-frontend）"
echo "  - 确认 frontend-user 不在 docker 组中"
echo "  - 验证只能使用 Rootless Docker"
echo ""
echo "⚠️  注意："
echo "  - 会备份旧配置到 /root/frontend_docker_config_backup_*"
echo "  - 不会影响 Rootless Docker 功能"
echo ""

# 清理 Node1
cleanup_node $NODE1_PUBLIC_IP "Node1"

# 清理 Node2
cleanup_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "✅ 清理完成"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 配置网络: bash scripts/configure_rootless_network.sh"
echo "  2. 验证隔离: bash scripts/verify_rootless_docker.sh"
echo ""

