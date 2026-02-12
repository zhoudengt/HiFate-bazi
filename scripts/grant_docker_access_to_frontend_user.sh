#!/bin/bash
# 授权 frontend-user 使用 Docker（双机）
# 使用：bash scripts/grant_docker_access_to_frontend_user.sh

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

grant_docker_access() {
    local host=$1
    local node_name=$2
    
    echo "🔓 在 $node_name ($host) 上授权 frontend-user 使用 Docker..."
    echo "----------------------------------------"
    
    # 1. 检查 docker 组是否存在
    echo "1. 检查 docker 组是否存在..."
    if ssh_exec $host "getent group docker" 2>/dev/null; then
        echo "   ✅ docker 组存在"
    else
        echo "   ⚠️  docker 组不存在，创建 docker 组..."
        ssh_exec $host "groupadd docker" 2>/dev/null || echo "   组可能已存在"
    fi
    
    # 2. 检查 frontend-user 是否已在 docker 组中
    echo ""
    echo "2. 检查 frontend-user 是否在 docker 组中..."
    CURRENT_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    if echo "$CURRENT_GROUPS" | grep -q "docker"; then
        echo "   ✅ frontend-user 已在 docker 组中"
        echo "   所属组: $CURRENT_GROUPS"
    else
        echo "   ⚠️  frontend-user 不在 docker 组中，正在添加..."
        ssh_exec $host "usermod -a -G docker $FRONTEND_USER" 2>/dev/null || {
            echo "   ❌ 添加失败，尝试使用 gpasswd..."
            ssh_exec $host "gpasswd -a $FRONTEND_USER docker" 2>/dev/null || {
                echo "   ❌ 添加失败"
                return 1
            }
        }
        
        # 验证
        NEW_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
        if echo "$NEW_GROUPS" | grep -q "docker"; then
            echo "   ✅ 已添加，frontend-user 现在在 docker 组中"
            echo "   新所属组: $NEW_GROUPS"
        else
            echo "   ❌ 添加失败，frontend-user 仍不在 docker 组中"
            return 1
        fi
    fi
    
    # 3. 检查 /var/run/docker.sock 权限
    echo ""
    echo "3. 检查 /var/run/docker.sock 权限..."
    SOCK_INFO=$(ssh_exec $host "ls -l /var/run/docker.sock 2>/dev/null" || echo "")
    echo "   $SOCK_INFO"
    
    # 确保 docker.sock 的组是 docker
    if echo "$SOCK_INFO" | grep -q "docker"; then
        echo "   ✅ docker.sock 权限正确"
    else
        echo "   ⚠️  设置 docker.sock 组为 docker..."
        ssh_exec $host "chgrp docker /var/run/docker.sock" 2>/dev/null || true
        ssh_exec $host "chmod 660 /var/run/docker.sock" 2>/dev/null || true
        echo "   ✅ docker.sock 权限已设置"
    fi
    
    # 4. 验证 docker 命令
    echo ""
    echo "4. 验证 frontend-user 可以执行 docker 命令..."
    DOCKER_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker ps 2>&1'" 2>/dev/null || echo "")
    if echo "$DOCKER_TEST" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "   ❌ 仍然无法执行 docker 命令"
        echo "   输出: $(echo "$DOCKER_TEST" | head -1)"
        echo "   ⚠️  可能需要重启 Docker 服务或用户重新登录"
    else
        echo "   ✅ 可以执行 docker 命令"
        echo "   输出: $(echo "$DOCKER_TEST" | head -3)"
    fi
    
    # 5. 显示当前权限
    echo ""
    echo "5. 当前权限总结："
    FINAL_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    echo "   frontend-user 所属组: $FINAL_GROUPS"
    
    echo ""
}

echo "=========================================="
echo "授权 frontend-user 使用 Docker（双机）"
echo "=========================================="
echo ""
echo "⚠️  注意："
echo "  - frontend-user 将可以执行所有 docker 命令"
echo "  - frontend-user 可以看到所有 Docker 容器"
echo "  - frontend-user 可以部署、停止、删除容器"
echo "  - 请确保 frontend-user 只部署自己的容器"
echo ""

# 授权 Node1
grant_docker_access $NODE1_PUBLIC_IP "Node1"

# 授权 Node2
grant_docker_access $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "完成"
echo "=========================================="
echo "✅ frontend-user 已授权使用 Docker（双机）"
echo ""
echo "验证命令（在服务器上执行）："
echo "  su - frontend-user"
echo "  docker ps"
echo "  docker images"
echo ""
echo "⚠️  安全提示："
echo "  - frontend-user 现在拥有完整的 Docker 权限"
echo "  - 建议：只允许 frontend-user 部署到特定网络或使用命名空间"
echo "  - 建议：定期检查 frontend-user 部署的容器"
echo ""

