#!/bin/bash
# 验证 Rootless Docker 隔离效果
# 使用：bash scripts/verify_rootless_docker.sh

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

verify_node() {
    local host=$1
    local node_name=$2
    
    echo "=========================================="
    echo "验证 $node_name ($host) 隔离效果"
    echo "=========================================="
    
    # 设置环境变量
    ENV_SETUP="export XDG_RUNTIME_DIR=\$HOME/.docker/run && export PATH=\$HOME/bin:\$PATH && export DOCKER_HOST=unix://\$HOME/.docker/run/docker.sock"
    
    # 1. 验证无法直接使用 docker 命令（root Docker）
    echo ""
    echo "1. 验证无法直接使用 docker 命令（root Docker）..."
    DOCKER_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker ps 2>&1' 2>/dev/null" || echo "无法执行")
    if echo "$DOCKER_TEST" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "   ✅ 无法访问 root Docker（正确）"
    else
        echo "   ❌ 仍然可以访问 root Docker（有问题）"
        echo "   输出: $DOCKER_TEST"
    fi
    
    # 2. 验证可以使用 Rootless Docker
    echo ""
    echo "2. 验证可以使用 Rootless Docker..."
    ROOTLESS_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker version --format \"{{.Server.Version}}\" 2>&1' 2>/dev/null" || echo "无法连接")
    if echo "$ROOTLESS_TEST" | grep -qE "^[0-9]+\.[0-9]+\.[0-9]+"; then
        echo "   ✅ Rootless Docker 可用，版本: $ROOTLESS_TEST"
    else
        echo "   ❌ Rootless Docker 不可用"
        echo "   输出: $ROOTLESS_TEST"
        return 1
    fi
    
    # 3. 验证无法看到后端容器
    echo ""
    echo "3. 验证无法看到后端容器..."
    
    # 先检查后端容器（作为 root）
    BACKEND_CONTAINERS=$(ssh_exec $host "docker ps --format '{{.Names}}' | grep -E 'hifate-|backend-' | head -5" 2>/dev/null || echo "")
    if [ -n "$BACKEND_CONTAINERS" ]; then
        echo "   后端容器（root Docker）:"
        echo "$BACKEND_CONTAINERS" | sed 's/^/     - /'
    else
        echo "   ⚠️  未找到后端容器（可能未运行）"
    fi
    
    # 检查 Rootless Docker 中的容器
    ROOTLESS_CONTAINERS=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker ps --format \"{{.Names}}\" 2>&1' 2>/dev/null" || echo "")
    if echo "$ROOTLESS_CONTAINERS" | grep -qE "hifate-|backend-"; then
        echo "   ❌ Rootless Docker 可以看到后端容器（有问题）"
        echo "   容器列表: $ROOTLESS_CONTAINERS"
    else
        echo "   ✅ Rootless Docker 无法看到后端容器（正确）"
        if [ -n "$ROOTLESS_CONTAINERS" ]; then
            echo "   Rootless Docker 容器:"
            echo "$ROOTLESS_CONTAINERS" | sed 's/^/     - /'
        else
            echo "   （当前没有 Rootless Docker 容器）"
        fi
    fi
    
    # 4. 验证无法访问后端 Docker socket
    echo ""
    echo "4. 验证无法访问后端 Docker socket..."
    SOCKET_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'test -r /var/run/docker.sock && echo \"可读\" || echo \"不可读\"' 2>/dev/null" || echo "无法检查")
    if [ "$SOCKET_TEST" = "不可读" ]; then
        echo "   ✅ 无法访问后端 Docker socket（正确）"
    else
        echo "   ❌ 可以访问后端 Docker socket（有问题）"
    fi
    
    # 5. 验证 Rootless Docker socket 存在
    echo ""
    echo "5. 验证 Rootless Docker socket 存在..."
    ROOTLESS_SOCKET=$(ssh_exec $host "su - $FRONTEND_USER -c 'test -S \$HOME/.docker/run/docker.sock && echo \"存在\" || echo \"不存在\"' 2>/dev/null" || echo "无法检查")
    if [ "$ROOTLESS_SOCKET" = "存在" ]; then
        echo "   ✅ Rootless Docker socket 存在（正确）"
    else
        echo "   ❌ Rootless Docker socket 不存在（有问题）"
    fi
    
    # 6. 验证网络隔离
    echo ""
    echo "6. 验证网络隔离..."
    
    # 后端网络
    BACKEND_NETWORKS=$(ssh_exec $host "docker network ls --format '{{.Name}}' | grep -E 'backend-|hifate-' | head -5" 2>/dev/null || echo "")
    if [ -n "$BACKEND_NETWORKS" ]; then
        echo "   后端网络（root Docker）:"
        echo "$BACKEND_NETWORKS" | sed 's/^/     - /'
    fi
    
    # Rootless Docker 网络
    ROOTLESS_NETWORKS=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker network ls --format \"{{.Name}}\" 2>&1' 2>/dev/null" || echo "")
    if echo "$ROOTLESS_NETWORKS" | grep -qE "backend-|hifate-"; then
        echo "   ❌ Rootless Docker 可以看到后端网络（有问题）"
    else
        echo "   ✅ Rootless Docker 无法看到后端网络（正确）"
        echo "   Rootless Docker 网络:"
        echo "$ROOTLESS_NETWORKS" | sed 's/^/     - /'
    fi
    
    echo ""
    echo "✅ $node_name 验证完成"
    echo ""
}

echo "=========================================="
echo "验证 Rootless Docker 隔离效果（双机）"
echo "=========================================="
echo ""
echo "验证内容："
echo "  - 无法访问 root Docker"
echo "  - 可以使用 Rootless Docker"
echo "  - 无法看到后端容器"
echo "  - 无法访问后端 Docker socket"
echo "  - 网络隔离正常"
echo ""

# 验证 Node1
verify_node $NODE1_PUBLIC_IP "Node1"

# 验证 Node2
verify_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "✅ 验证完成"
echo "=========================================="
echo ""
echo "下一步：测试功能"
echo "   bash scripts/test_rootless_functionality.sh"
echo ""

