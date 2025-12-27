#!/bin/bash
# 为 frontend-user 安装 Docker Rootless
# 使用：bash scripts/install_docker_rootless_for_frontend.sh

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

install_node() {
    local host=$1
    local node_name=$2
    
    echo "=========================================="
    echo "在 $node_name ($host) 上安装 Docker Rootless"
    echo "=========================================="
    
    # 1. 检查是否已安装
    echo ""
    echo "1. 检查是否已安装 Docker Rootless..."
    if ssh_exec $host "su - $FRONTEND_USER -c 'test -f \$HOME/bin/dockerd-rootless.sh' 2>/dev/null" 2>/dev/null; then
        echo "   ⚠️  Docker Rootless 已安装，跳过安装步骤"
        echo "   如需重新安装，请先卸载："
        echo "   su - $FRONTEND_USER -c 'dockerd-rootless-setuptool.sh uninstall'"
        return 0
    fi
    
    # 2. 准备系统要求
    echo ""
    echo "2. 准备系统要求..."
    
    # 加载 ip_tables 模块
    echo "   加载 ip_tables 模块..."
    ssh_exec $host "modprobe ip_tables 2>/dev/null || true"
    
    # 确保 user namespaces 已启用
    echo "   检查 user namespaces..."
    if ! ssh_exec $host "test -f /proc/sys/user/max_user_namespaces || [ \$(cat /proc/sys/user/max_user_namespaces 2>/dev/null || echo 0) -eq 0 ]" 2>/dev/null; then
        echo "   设置 user.max_user_namespaces..."
        ssh_exec $host "sysctl -w user.max_user_namespaces=28633 2>/dev/null || true"
    fi
    
    # 3. 安装 Docker Rootless
    echo ""
    echo "3. 安装 Docker Rootless..."
    echo "   使用官方安装脚本..."
    
    # 如果系统要求不满足，跳过 iptables 检查
    INSTALL_OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c 'SKIP_IPTABLES=1 curl -fsSL https://get.docker.com/rootless | sh' 2>&1" || echo "安装失败")
    
    if echo "$INSTALL_OUTPUT" | grep -q "error\|Error\|ERROR\|失败"; then
        echo "   ❌ 安装失败"
        echo "   输出: $INSTALL_OUTPUT"
        return 1
    else
        echo "   ✅ 安装成功"
        echo "   $INSTALL_OUTPUT" | tail -5
    fi
    
    # 4. 验证安装
    echo ""
    echo "4. 验证安装..."
    if ssh_exec $host "su - $FRONTEND_USER -c 'test -f \$HOME/bin/dockerd-rootless.sh' 2>/dev/null" 2>/dev/null; then
        echo "   ✅ dockerd-rootless.sh 已安装"
        DOCKERD_PATH=$(ssh_exec $host "su - $FRONTEND_USER -c 'which dockerd-rootless.sh' 2>/dev/null" || echo "")
        echo "   路径: $DOCKERD_PATH"
    else
        echo "   ❌ dockerd-rootless.sh 未找到"
        return 1
    fi
    
    if ssh_exec $host "su - $FRONTEND_USER -c 'test -f \$HOME/bin/docker' 2>/dev/null" 2>/dev/null; then
        echo "   ✅ docker 客户端已安装"
        DOCKER_PATH=$(ssh_exec $host "su - $FRONTEND_USER -c 'which docker' 2>/dev/null" || echo "")
        echo "   路径: $DOCKER_PATH"
    else
        echo "   ⚠️  docker 客户端未找到（可能需要添加到 PATH）"
    fi
    
    # 5. 检查环境变量
    echo ""
    echo "5. 检查环境变量..."
    DOCKER_HOST=$(ssh_exec $host "su - $FRONTEND_USER -c 'echo \$DOCKER_HOST' 2>/dev/null" || echo "")
    if [ -n "$DOCKER_HOST" ]; then
        echo "   ✅ DOCKER_HOST 已设置: $DOCKER_HOST"
    else
        echo "   ⚠️  DOCKER_HOST 未设置（将在配置阶段设置）"
    fi
    
    echo ""
    echo "✅ $node_name 安装完成"
    echo ""
}

echo "=========================================="
echo "为 frontend-user 安装 Docker Rootless（双机）"
echo "=========================================="
echo ""
echo "功能："
echo "  - 为 frontend-user 安装 Docker Rootless"
echo "  - 无需 sudo/root 权限即可使用 Docker"
echo "  - 完全隔离的 Docker 环境"
echo ""
echo "⚠️  注意："
echo "  - 安装过程可能需要几分钟"
echo "  - 需要 frontend-user 有足够的权限"
echo "  - 不会影响现有后端 Docker 服务"
echo ""

# 安装 Node1
install_node $NODE1_PUBLIC_IP "Node1"

# 安装 Node2
install_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "✅ 安装完成"
echo "=========================================="
echo ""
echo "下一步：配置 Rootless Docker 环境"
echo "   bash scripts/configure_rootless_docker.sh"
echo ""

