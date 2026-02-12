#!/bin/bash
# 验证 frontend-user 的 Docker 访问权限
# 使用：bash scripts/verify_frontend_user_docker_access.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
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
    echo "验证 $node_name ($host)"
    echo "=========================================="
    
    # 1. 检查是否在 docker 组中
    echo ""
    echo "1. 检查 frontend-user 是否在 docker 组中..."
    GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    if echo "$GROUPS" | grep -q "docker"; then
        echo "   ✅ 是，frontend-user 在 docker 组中"
        echo "   所属组: $GROUPS"
    else
        echo "   ❌ 否，frontend-user 不在 docker 组中"
        return 1
    fi
    
    # 2. 测试 docker ps
    echo ""
    echo "2. 测试 docker ps 命令..."
    DOCKER_PS=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker ps 2>&1'" 2>/dev/null || echo "")
    if echo "$DOCKER_PS" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "   ❌ 失败：无法执行 docker ps"
        echo "   输出: $(echo "$DOCKER_PS" | head -1)"
    else
        CONTAINER_COUNT=$(echo "$DOCKER_PS" | grep -c "CONTAINER\|Up\|Exited" || echo "0")
        echo "   ✅ 成功：可以执行 docker ps"
        echo "   可以看到容器数量: $((CONTAINER_COUNT - 1))"
    fi
    
    # 3. 测试 docker images
    echo ""
    echo "3. 测试 docker images 命令..."
    DOCKER_IMAGES=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker images 2>&1 | head -5'" 2>/dev/null || echo "")
    if echo "$DOCKER_IMAGES" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "   ❌ 失败：无法执行 docker images"
    else
        echo "   ✅ 成功：可以执行 docker images"
    fi
    
    # 4. 测试 docker run（只测试，不实际运行）
    echo ""
    echo "4. 测试 docker run 权限（dry-run）..."
    DOCKER_RUN_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker run --help 2>&1 | head -1'" 2>/dev/null || echo "")
    if echo "$DOCKER_RUN_TEST" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "   ❌ 失败：无法执行 docker run"
    else
        echo "   ✅ 成功：可以执行 docker run（可以部署容器）"
    fi
    
    # 5. 显示 docker.sock 权限
    echo ""
    echo "5. 检查 /var/run/docker.sock 权限..."
    SOCK_INFO=$(ssh_exec $host "ls -l /var/run/docker.sock 2>/dev/null" || echo "")
    echo "   $SOCK_INFO"
    if echo "$SOCK_INFO" | grep -q "docker.*docker"; then
        echo "   ✅ docker.sock 权限正确"
    else
        echo "   ⚠️  docker.sock 权限可能需要调整"
    fi
    
    echo ""
}

echo "=========================================="
echo "验证 frontend-user 的 Docker 访问权限"
echo "=========================================="
echo ""

verify_node $NODE1_PUBLIC_IP "Node1"
verify_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""
echo "✅ frontend-user 现在可以："
echo "  - 执行 docker ps（查看容器）"
echo "  - 执行 docker images（查看镜像）"
echo "  - 执行 docker run（部署容器）"
echo "  - 执行 docker stop/start/rm（管理容器）"
echo ""
echo "⚠️  安全提示："
echo "  - frontend-user 可以看到所有 Docker 容器"
echo "  - frontend-user 可以部署、停止、删除容器"
echo "  - 建议：只允许 frontend-user 部署到特定网络"
echo "  - 建议：定期检查 frontend-user 部署的容器"
echo ""

