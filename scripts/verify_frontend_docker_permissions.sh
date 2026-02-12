#!/bin/bash
# 验证 frontend-user 的 Docker 权限和目录权限配置（双机）
# 使用：bash scripts/verify_frontend_docker_permissions.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
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

verify_node() {
    local host=$1
    local node_name=$2
    
    echo "=========================================="
    echo "验证 $node_name ($host)"
    echo "=========================================="
    
    local all_passed=true
    
    # ============================================
    # 第一部分：目录权限验证
    # ============================================
    echo ""
    echo "📁 [第一部分] 目录权限验证..."
    
    # 测试 1: 可以访问 /opt/hifate-frontend
    echo ""
    echo "   1. frontend-user 可以访问 $FRONTEND_DIR"
    if ssh_exec $host "su - $FRONTEND_USER -c 'cd $FRONTEND_DIR && pwd'" 2>/dev/null; then
        echo "      ✅ 通过：可以进入目录"
    else
        echo "      ❌ 失败：无法进入目录"
        all_passed=false
    fi
    
    # 测试 2: 可以读写文件
    echo ""
    echo "   2. frontend-user 可以在 $FRONTEND_DIR 创建文件"
    TEST_FILE="$FRONTEND_DIR/.test_\$\$"
    if ssh_exec $host "su - $FRONTEND_USER -c 'touch $TEST_FILE && rm -f $TEST_FILE && echo ok'" 2>/dev/null | grep -q "ok"; then
        echo "      ✅ 通过：可以创建和删除文件"
    else
        echo "      ❌ 失败：无法创建文件"
        all_passed=false
    fi
    
    # 测试 3: 无法访问 /opt/HiFate-bazi
    echo ""
    echo "   3. frontend-user 无法访问 $PROJECT_DIR"
    OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c 'ls $PROJECT_DIR 2>&1'" 2>/dev/null || echo "")
    if echo "$OUTPUT" | grep -q "Permission denied\|cannot access\|No such file"; then
        echo "      ✅ 通过：无法访问（符合预期）"
        echo "         输出: $(echo "$OUTPUT" | head -1)"
    else
        echo "      ❌ 失败：仍然可以访问"
        echo "         输出: $OUTPUT"
        all_passed=false
    fi
    
    # 测试 4: 无法列出 /opt 下的其他目录
    echo ""
    echo "   4. frontend-user 无法列出 /opt 下的其他目录"
    OPT_OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c 'ls /opt 2>&1'" 2>/dev/null || echo "")
    if echo "$OPT_OUTPUT" | grep -q "Permission denied\|cannot access"; then
        echo "      ✅ 通过：无法列出（符合预期）"
        echo "         输出: Permission denied"
    elif echo "$OPT_OUTPUT" | grep -q "hifate-frontend"; then
        if echo "$OPT_OUTPUT" | grep -q "HiFate-bazi"; then
            echo "      ❌ 失败：可以看到 HiFate-bazi（不应该看到）"
            echo "         输出: $OPT_OUTPUT"
            all_passed=false
        else
            echo "      ✅ 通过：只能看到 hifate-frontend，看不到 HiFate-bazi"
            echo "         输出: $OPT_OUTPUT"
        fi
    else
        echo "      ⚠️  检查输出: $OPT_OUTPUT"
    fi
    
    # 测试 5: 检查权限
    echo ""
    echo "   5. 检查目录权限"
    OPT_PERM=$(ssh_exec $host "stat -c '%a' /opt" 2>/dev/null || echo "")
    FRONTEND_PERM=$(ssh_exec $host "stat -c '%a' $FRONTEND_DIR" 2>/dev/null || echo "")
    PROJECT_PERM=$(ssh_exec $host "stat -c '%a' $PROJECT_DIR" 2>/dev/null || echo "")
    echo "      /opt 权限: $OPT_PERM (应为 751)"
    echo "      $FRONTEND_DIR 权限: $FRONTEND_PERM (应为 775)"
    echo "      $PROJECT_DIR 权限: $PROJECT_PERM (应为 750)"
    
    if [ "$OPT_PERM" = "751" ] && [ "$FRONTEND_PERM" = "775" ] && [ "$PROJECT_PERM" = "750" ]; then
        echo "      ✅ 通过：所有权限设置正确"
    else
        echo "      ⚠️  警告：部分权限设置可能不正确"
        if [ "$OPT_PERM" != "751" ]; then
            all_passed=false
        fi
        if [ "$FRONTEND_PERM" != "775" ]; then
            all_passed=false
        fi
        if [ "$PROJECT_PERM" != "750" ]; then
            all_passed=false
        fi
    fi
    
    # ============================================
    # 第二部分：Docker 权限验证
    # ============================================
    echo ""
    echo "🐳 [第二部分] Docker 权限验证..."
    
    # 测试 1: 检查是否在 docker 组中
    echo ""
    echo "   1. frontend-user 是否在 docker 组中"
    GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    if echo "$GROUPS" | grep -q "docker"; then
        echo "      ✅ 通过：frontend-user 在 docker 组中"
        echo "         所属组: $GROUPS"
    else
        echo "      ❌ 失败：frontend-user 不在 docker 组中"
        all_passed=false
    fi
    
    # 测试 2: 测试 docker ps
    echo ""
    echo "   2. 测试 docker ps 命令"
    DOCKER_PS=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker ps 2>&1'" 2>/dev/null || echo "")
    if echo "$DOCKER_PS" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "      ❌ 失败：无法执行 docker ps"
        echo "         输出: $(echo "$DOCKER_PS" | head -1)"
        all_passed=false
    else
        CONTAINER_COUNT=$(echo "$DOCKER_PS" | grep -c "CONTAINER\|Up\|Exited" || echo "0")
        echo "      ✅ 通过：可以执行 docker ps"
        echo "         可以看到容器数量: $((CONTAINER_COUNT - 1))"
    fi
    
    # 测试 3: 测试 docker images
    echo ""
    echo "   3. 测试 docker images 命令"
    DOCKER_IMAGES=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker images 2>&1 | head -5'" 2>/dev/null || echo "")
    if echo "$DOCKER_IMAGES" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "      ❌ 失败：无法执行 docker images"
        all_passed=false
    else
        echo "      ✅ 通过：可以执行 docker images"
    fi
    
    # 测试 4: 测试 docker run（只测试，不实际运行）
    echo ""
    echo "   4. 测试 docker run 权限（dry-run）"
    DOCKER_RUN_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker run --help 2>&1 | head -1'" 2>/dev/null || echo "")
    if echo "$DOCKER_RUN_TEST" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "      ❌ 失败：无法执行 docker run"
        all_passed=false
    else
        echo "      ✅ 通过：可以执行 docker run（可以部署容器）"
    fi
    
    # 测试 5: 显示 docker.sock 权限
    echo ""
    echo "   5. 检查 /var/run/docker.sock 权限"
    SOCK_INFO=$(ssh_exec $host "ls -l /var/run/docker.sock 2>/dev/null" || echo "")
    echo "      $SOCK_INFO"
    if echo "$SOCK_INFO" | grep -q "docker.*docker"; then
        echo "      ✅ 通过：docker.sock 权限正确"
    else
        echo "      ⚠️  警告：docker.sock 权限可能需要调整"
    fi
    
    # ============================================
    # 第三部分：Docker 网络验证
    # ============================================
    echo ""
    echo "🌐 [第三部分] Docker 网络验证..."
    
    # 测试 1: 检查前端网络是否存在
    echo ""
    echo "   1. 检查前端网络 $FRONTEND_NETWORK 是否存在"
    if ssh_exec $host "docker network ls | grep -q $FRONTEND_NETWORK" 2>/dev/null; then
        NETWORK_INFO=$(ssh_exec $host "docker network inspect $FRONTEND_NETWORK --format '{{.Name}}' 2>/dev/null" || echo "")
        echo "      ✅ 通过：网络 $FRONTEND_NETWORK 存在"
        echo "         网络信息: $NETWORK_INFO"
    else
        echo "      ⚠️  警告：网络 $FRONTEND_NETWORK 不存在（需要创建）"
        echo "         可以使用以下命令创建："
        echo "         docker network create $FRONTEND_NETWORK"
    fi
    
    # ============================================
    # 第四部分：使用指南文件验证
    # ============================================
    echo ""
    echo "📝 [第四部分] 使用指南文件验证..."
    
    # 测试 1: 检查 docker-compose.yml 是否存在
    echo ""
    echo "   1. 检查 docker-compose.yml 是否存在"
    if ssh_exec $host "test -f $FRONTEND_DIR/docker-compose.yml" 2>/dev/null; then
        echo "      ✅ 通过：docker-compose.yml 存在"
    else
        echo "      ⚠️  警告：docker-compose.yml 不存在（可选）"
        echo "         可以使用以下命令创建："
        echo "         bash scripts/create_frontend_docker_guide.sh"
    fi
    
    # 测试 2: 检查 README.md 是否存在
    echo ""
    echo "   2. 检查 README.md 是否存在"
    if ssh_exec $host "test -f $FRONTEND_DIR/README.md" 2>/dev/null; then
        echo "      ✅ 通过：README.md 存在"
    else
        echo "      ⚠️  警告：README.md 不存在（可选）"
        echo "         可以使用以下命令创建："
        echo "         bash scripts/create_frontend_docker_guide.sh"
    fi
    
    # ============================================
    # 总结
    # ============================================
    echo ""
    echo "=========================================="
    if [ "$all_passed" = true ]; then
        echo "✅ $node_name 验证通过"
    else
        echo "❌ $node_name 验证失败（部分测试未通过）"
    fi
    echo "=========================================="
    echo ""
    
    if [ "$all_passed" = false ]; then
        return 1
    fi
}

echo "=========================================="
echo "验证 frontend-user Docker 权限和目录权限"
echo "=========================================="
echo ""
echo "验证内容："
echo "  - 目录权限（/opt/hifate-frontend 可访问，/opt/HiFate-bazi 不可访问）"
echo "  - Docker 权限（frontend-user 在 docker 组中，可以执行 docker 命令）"
echo "  - Docker 网络（前端专用网络 $FRONTEND_NETWORK）"
echo "  - 使用指南文件（docker-compose.yml 和 README.md）"
echo ""

# 验证 Node1
verify_node $NODE1_PUBLIC_IP "Node1"
NODE1_RESULT=$?

# 验证 Node2
verify_node $NODE2_PUBLIC_IP "Node2"
NODE2_RESULT=$?

echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""

if [ $NODE1_RESULT -eq 0 ] && [ $NODE2_RESULT -eq 0 ]; then
    echo "✅ 所有验证通过（双机）"
    echo ""
    echo "frontend-user 现在可以："
    echo "  - 访问 $FRONTEND_DIR 目录（读写执行）"
    echo "  - 无法访问 $PROJECT_DIR 目录"
    echo "  - 执行 docker 命令（查看、部署、管理容器）"
    echo "  - 使用前端专用网络 $FRONTEND_NETWORK"
    echo ""
    echo "使用规范："
    echo "  - 前端容器必须使用 frontend-* 前缀命名"
    echo "  - 前端容器必须使用 $FRONTEND_NETWORK 网络"
    echo "  - 禁止操作 hifate-* 前缀的容器（后端容器）"
    echo "  - 禁止占用后端服务端口（8001, 9001-9010, 3306, 6379）"
    exit 0
else
    echo "❌ 部分验证失败"
    echo ""
    echo "请检查以下内容："
    echo "  - 运行配置脚本：bash scripts/configure_frontend_docker_permissions.sh"
    echo "  - 运行使用指南脚本：bash scripts/create_frontend_docker_guide.sh"
    echo "  - 检查服务器日志和权限设置"
    exit 1
fi

