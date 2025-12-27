#!/bin/bash
# 配置 frontend-user 的 Docker 权限和目录权限（双机）
# 整合功能：
#   - 配置目录权限（/opt/hifate-frontend）
#   - 授权 Docker 访问
#   - 创建前端专用 Docker 网络
# 使用：bash scripts/configure_frontend_docker_permissions.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
FRONTEND_USER="frontend-user"
FRONTEND_DIR="/opt/hifate-frontend"
PROJECT_DIR="/opt/HiFate-bazi"
FRONTEND_NETWORK="frontend-network"

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
    
    echo "🔧 配置 $node_name ($host) 的 frontend-user Docker 权限..."
    echo "=========================================="
    
    # ============================================
    # 第一部分：用户和目录权限配置
    # ============================================
    echo ""
    echo "📁 [第一部分] 配置目录权限..."
    
    # 1. 检查 frontend-user 是否存在
    if ! ssh_exec $host "id $FRONTEND_USER" 2>/dev/null; then
        echo "   ⚠️  frontend-user 用户不存在，创建用户..."
        ssh_exec $host "useradd -m -s /bin/bash $FRONTEND_USER" 2>/dev/null || echo "     用户可能已存在"
    else
        echo "   ✅ frontend-user 用户已存在"
    fi
    
    # 2. 创建 /opt/hifate-frontend 目录（如果不存在）
    echo ""
    echo "   1. 创建/检查 $FRONTEND_DIR 目录..."
    ssh_exec $host "mkdir -p $FRONTEND_DIR"
    echo "      ✅ 目录已创建/存在"
    
    # 3. 设置 /opt/hifate-frontend 目录权限（775: rwxrwxr-x）
    echo ""
    echo "   2. 设置 $FRONTEND_DIR 目录权限..."
    ssh_exec $host "chmod 775 $FRONTEND_DIR"
    ssh_exec $host "chown root:root $FRONTEND_DIR"
    
    # 使用 ACL 给 frontend-user 完整权限（推荐方案）
    echo ""
    echo "   3. 使用 ACL 给 frontend-user 完整权限..."
    if ssh_exec $host "which setfacl" 2>/dev/null; then
        ssh_exec $host "setfacl -R -m u:$FRONTEND_USER:rwx $FRONTEND_DIR" 2>/dev/null || true
        ssh_exec $host "setfacl -R -d -m u:$FRONTEND_USER:rwx $FRONTEND_DIR" 2>/dev/null || true
        echo "      ✅ ACL 权限已设置"
    else
        echo "      ⚠️  setfacl 不可用，使用组权限方案..."
        ssh_exec $host "groupadd -f hifate-frontend-group" 2>/dev/null || true
        ssh_exec $host "usermod -a -G hifate-frontend-group $FRONTEND_USER" 2>/dev/null || true
        ssh_exec $host "chgrp -R hifate-frontend-group $FRONTEND_DIR" 2>/dev/null || true
        ssh_exec $host "chmod -R 775 $FRONTEND_DIR"
        echo "      ✅ 组权限已设置"
    fi
    
    # 4. 设置 /opt 目录权限（751: drwxr-x--x）
    echo ""
    echo "   4. 设置 /opt 目录权限（751: 允许执行但不允许列出）..."
    ssh_exec $host "chmod 751 /opt"
    ssh_exec $host "chown root:root /opt"
    echo "      ✅ /opt 权限已设置为 751"
    
    # 5. 设置 /opt/HiFate-bazi 目录权限（750: drwxr-x---）
    echo ""
    echo "   5. 禁止 frontend-user 访问 $PROJECT_DIR..."
    if ssh_exec $host "test -d $PROJECT_DIR" 2>/dev/null; then
        ssh_exec $host "chmod 750 $PROJECT_DIR"
        ssh_exec $host "chown root:root $PROJECT_DIR"
        
        # 递归设置子目录权限（只设置目录，不改变文件权限，避免影响服务）
        ssh_exec $host "find $PROJECT_DIR -type d -exec chmod 750 {} \\; 2>/dev/null || true"
        echo "      ✅ $PROJECT_DIR 权限已设置为 750"
    else
        echo "      ⚠️  $PROJECT_DIR 不存在，跳过"
    fi
    
    # 6. 禁止访问 /opt 下的其他目录
    echo ""
    echo "   6. 设置 /opt 下其他目录的权限..."
    ssh_exec $host "find /opt -maxdepth 1 -type d ! -path /opt ! -path $FRONTEND_DIR -exec chmod 750 {} \\; 2>/dev/null || true"
    ssh_exec $host "find /opt -maxdepth 1 -type d ! -path /opt ! -path $FRONTEND_DIR -exec chown root:root {} \\; 2>/dev/null || true"
    echo "      ✅ 其他目录权限已设置"
    
    # ============================================
    # 第二部分：Docker 权限配置
    # ============================================
    echo ""
    echo "🐳 [第二部分] 配置 Docker 权限..."
    
    # 1. 检查 docker 组是否存在
    echo ""
    echo "   1. 检查 docker 组是否存在..."
    if ssh_exec $host "getent group docker" 2>/dev/null; then
        echo "      ✅ docker 组存在"
    else
        echo "      ⚠️  docker 组不存在，创建 docker 组..."
        ssh_exec $host "groupadd docker" 2>/dev/null || echo "        组可能已存在"
    fi
    
    # 2. 检查 frontend-user 是否已在 docker 组中
    echo ""
    echo "   2. 检查 frontend-user 是否在 docker 组中..."
    CURRENT_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    if echo "$CURRENT_GROUPS" | grep -q "docker"; then
        echo "      ✅ frontend-user 已在 docker 组中"
        echo "        所属组: $CURRENT_GROUPS"
    else
        echo "      ⚠️  frontend-user 不在 docker 组中，正在添加..."
        ssh_exec $host "usermod -a -G docker $FRONTEND_USER" 2>/dev/null || {
            echo "      ❌ 添加失败，尝试使用 gpasswd..."
            ssh_exec $host "gpasswd -a $FRONTEND_USER docker" 2>/dev/null || {
                echo "      ❌ 添加失败"
                return 1
            }
        }
        
        # 验证
        NEW_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
        if echo "$NEW_GROUPS" | grep -q "docker"; then
            echo "      ✅ 已添加，frontend-user 现在在 docker 组中"
            echo "        新所属组: $NEW_GROUPS"
        else
            echo "      ❌ 添加失败，frontend-user 仍不在 docker 组中"
            return 1
        fi
    fi
    
    # 3. 检查 /var/run/docker.sock 权限
    echo ""
    echo "   3. 检查 /var/run/docker.sock 权限..."
    SOCK_INFO=$(ssh_exec $host "ls -l /var/run/docker.sock 2>/dev/null" || echo "")
    echo "      $SOCK_INFO"
    
    # 确保 docker.sock 的组是 docker
    if echo "$SOCK_INFO" | grep -q "docker"; then
        echo "      ✅ docker.sock 权限正确"
    else
        echo "      ⚠️  设置 docker.sock 组为 docker..."
        ssh_exec $host "chgrp docker /var/run/docker.sock" 2>/dev/null || true
        ssh_exec $host "chmod 660 /var/run/docker.sock" 2>/dev/null || true
        echo "      ✅ docker.sock 权限已设置"
    fi
    
    # ============================================
    # 第三部分：创建前端专用 Docker 网络
    # ============================================
    echo ""
    echo "🌐 [第三部分] 创建前端专用 Docker 网络..."
    
    # 检查网络是否已存在
    echo ""
    echo "   1. 检查网络 $FRONTEND_NETWORK 是否已存在..."
    if ssh_exec $host "docker network ls | grep -q $FRONTEND_NETWORK" 2>/dev/null; then
        echo "      ✅ 网络 $FRONTEND_NETWORK 已存在"
    else
        echo "      ⚠️  网络 $FRONTEND_NETWORK 不存在，正在创建..."
        ssh_exec $host "docker network create $FRONTEND_NETWORK" 2>/dev/null || {
            echo "      ❌ 创建网络失败（可能需要 root 权限）"
            echo "      ⚠️  将在后续步骤中由 root 创建"
        }
        if ssh_exec $host "docker network ls | grep -q $FRONTEND_NETWORK" 2>/dev/null; then
            echo "      ✅ 网络 $FRONTEND_NETWORK 已创建"
        fi
    fi
    
    # ============================================
    # 第四部分：验证配置
    # ============================================
    echo ""
    echo "✅ [第四部分] 验证配置..."
    
    # 验证 /opt/hifate-frontend 权限
    PERM=$(ssh_exec $host "stat -c '%a' $FRONTEND_DIR" 2>/dev/null || echo "")
    echo ""
    echo "   1. 目录权限验证："
    echo "      $FRONTEND_DIR 权限: $PERM"
    
    # 验证 frontend-user 可以访问 /opt/hifate-frontend
    if ssh_exec $host "su - $FRONTEND_USER -c 'test -r $FRONTEND_DIR && test -w $FRONTEND_DIR && test -x $FRONTEND_DIR'" 2>/dev/null; then
        echo "      ✅ frontend-user 可以读写执行 $FRONTEND_DIR"
    else
        echo "      ❌ frontend-user 无法访问 $FRONTEND_DIR"
    fi
    
    # 验证 frontend-user 无法访问 /opt/HiFate-bazi
    if ssh_exec $host "su - $FRONTEND_USER -c 'test -r $PROJECT_DIR'" 2>/dev/null; then
        echo "      ❌ frontend-user 仍然可以访问 $PROJECT_DIR（需要修复）"
    else
        echo "      ✅ frontend-user 无法访问 $PROJECT_DIR"
    fi
    
    # 验证 docker 命令
    echo ""
    echo "   2. Docker 权限验证："
    DOCKER_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker ps 2>&1'" 2>/dev/null || echo "")
    if echo "$DOCKER_TEST" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "      ❌ 仍然无法执行 docker 命令"
        echo "         输出: $(echo "$DOCKER_TEST" | head -1)"
        echo "      ⚠️  可能需要重启 Docker 服务或用户重新登录"
    else
        echo "      ✅ 可以执行 docker 命令"
        echo "         输出: $(echo "$DOCKER_TEST" | head -3)"
    fi
    
    # 验证网络
    echo ""
    echo "   3. Docker 网络验证："
    if ssh_exec $host "docker network ls | grep -q $FRONTEND_NETWORK" 2>/dev/null; then
        NETWORK_INFO=$(ssh_exec $host "docker network inspect $FRONTEND_NETWORK --format '{{.Name}}' 2>/dev/null" || echo "")
        echo "      ✅ 网络 $FRONTEND_NETWORK 存在: $NETWORK_INFO"
    else
        echo "      ⚠️  网络 $FRONTEND_NETWORK 不存在（需要 root 创建）"
    fi
    
    echo ""
    echo "=========================================="
}

echo "=========================================="
echo "配置 frontend-user Docker 权限（双机）"
echo "=========================================="
echo ""
echo "目标："
echo "  - frontend-user 可以访问 $FRONTEND_DIR（读写执行）"
echo "  - frontend-user 无法访问 $PROJECT_DIR"
echo "  - frontend-user 可以使用 Docker（在 docker 组中）"
echo "  - 创建前端专用 Docker 网络 $FRONTEND_NETWORK"
echo ""
echo "⚠️  注意："
echo "  - frontend-user 可以看到所有 Docker 容器"
echo "  - 通过命名规范限制：只能操作 frontend-* 前缀的容器"
echo "  - 后端容器使用 hifate-* 前缀，禁止操作"
echo ""

# 配置 Node1
configure_node $NODE1_PUBLIC_IP "Node1"

# 配置 Node2
configure_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "完成"
echo "=========================================="
echo "✅ frontend-user Docker 权限配置完成（双机）"
echo ""
echo "权限总结："
echo "  - /opt/hifate-frontend: 775 (rwxrwxr-x) + ACL/组权限"
echo "  - /opt: 751 (drwxr-x--x) - 允许执行但不允许列出"
echo "  - /opt/HiFate-bazi: 750 (drwxr-x---) - 完全禁止其他用户访问"
echo "  - Docker 权限: frontend-user 在 docker 组中"
echo "  - Docker 网络: $FRONTEND_NETWORK（前端专用）"
echo ""
echo "使用规范："
echo "  - 前端容器必须使用 frontend-* 前缀命名"
echo "  - 前端容器必须使用 $FRONTEND_NETWORK 网络"
echo "  - 禁止操作 hifate-* 前缀的容器（后端容器）"
echo "  - 禁止占用后端服务端口（8001, 9001-9010, 3306, 6379）"
echo ""
echo "验证命令（在服务器上执行）："
echo "  su - frontend-user"
echo "  cd /opt/hifate-frontend"
echo "  docker ps"
echo "  docker network ls | grep $FRONTEND_NETWORK"
echo ""

