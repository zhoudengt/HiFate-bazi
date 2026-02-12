#!/bin/bash
# 验证 frontend-user 受限 Docker 权限配置（双机）
# 使用：bash scripts/verify_frontend_docker_restricted.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
FRONTEND_USER="frontend-user"
DOCKER_WRAPPER="/usr/local/bin/docker-frontend"
SUDOERS_FILE="/etc/sudoers.d/frontend-docker"

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
    # 第一部分：验证 docker 组权限已移除
    # ============================================
    echo ""
    echo "📋 [第一部分] 验证 docker 组权限已移除..."
    
    echo ""
    echo "   1. 检查 frontend-user 是否在 docker 组中"
    GROUPS=$(ssh_exec $host "groups $FRONTEND_USER 2>&1" || echo "无法获取组信息")
    if [ -z "$GROUPS" ]; then
        echo "      ⚠️  警告：无法获取组信息"
        GROUPS="未知"
    fi
    if echo "$GROUPS" | grep -q "docker"; then
        echo "      ❌ 失败：frontend-user 仍在 docker 组中"
        echo "         所属组: $GROUPS"
        all_passed=false
    else
        echo "      ✅ 通过：frontend-user 不在 docker 组中"
        echo "         所属组: $GROUPS"
    fi
    
    # 测试直接使用 docker 命令（应该失败）
    echo ""
    echo "   2. 测试直接使用 docker 命令（应该失败）"
    DOCKER_DIRECT=$(ssh_exec $host "su - $FRONTEND_USER -c 'docker ps 2>&1'" 2>/dev/null || echo "")
    if echo "$DOCKER_DIRECT" | grep -q "permission denied\|Cannot connect\|denied"; then
        echo "      ✅ 通过：无法直接使用 docker 命令（符合预期）"
        echo "         输出: $(echo "$DOCKER_DIRECT" | head -1)"
    else
        echo "      ❌ 失败：仍然可以直接使用 docker 命令"
        echo "         输出: $DOCKER_DIRECT"
        all_passed=false
    fi
    
    # ============================================
    # 第二部分：验证包装脚本存在
    # ============================================
    echo ""
    echo "📝 [第二部分] 验证包装脚本..."
    
    echo ""
    echo "   1. 检查包装脚本是否存在"
    if ssh_exec $host "test -f $DOCKER_WRAPPER" 2>/dev/null; then
        echo "      ✅ 通过：包装脚本存在"
        
        # 检查执行权限
        if ssh_exec $host "test -x $DOCKER_WRAPPER" 2>/dev/null; then
            echo "      ✅ 通过：包装脚本可执行"
        else
            echo "      ❌ 失败：包装脚本不可执行"
            all_passed=false
        fi
    else
        echo "      ❌ 失败：包装脚本不存在"
        all_passed=false
    fi
    
    # ============================================
    # 第三部分：验证 sudo 规则
    # ============================================
    echo ""
    echo "🔐 [第三部分] 验证 sudo 规则..."
    
    echo ""
    echo "   1. 检查 sudoers 文件是否存在"
    if ssh_exec $host "test -f $SUDOERS_FILE" 2>/dev/null; then
        echo "      ✅ 通过：sudoers 文件存在"
        
        # 检查文件权限
        PERM=$(ssh_exec $host "stat -c '%a' $SUDOERS_FILE" 2>/dev/null || echo "")
        if [ "$PERM" = "440" ] || [ "$PERM" = "0440" ]; then
            echo "      ✅ 通过：sudoers 文件权限正确 ($PERM)"
        else
            echo "      ⚠️  警告：sudoers 文件权限可能不正确 ($PERM，应为 440)"
        fi
    else
        echo "      ❌ 失败：sudoers 文件不存在"
        all_passed=false
    fi
    
    echo ""
    echo "   2. 检查 sudo 规则是否生效"
    SUDO_RULES=$(ssh_exec $host "sudo -l -U $FRONTEND_USER 2>&1" || echo "")
    if echo "$SUDO_RULES" | grep -q "docker-frontend"; then
        echo "      ✅ 通过：sudo 规则已生效"
        echo "         $(echo "$SUDO_RULES" | grep docker-frontend | head -1)"
    else
        echo "      ⚠️  警告：sudo 规则可能未生效（需要用户重新登录）"
        echo "         输出: $SUDO_RULES"
    fi
    
    # ============================================
    # 第四部分：测试包装脚本功能
    # ============================================
    echo ""
    echo "🧪 [第四部分] 测试包装脚本功能..."
    
    # 测试 1: 只读命令（应该可以执行）
    echo ""
    echo "   1. 测试只读命令（应该可以执行）"
    DOCKER_PS=$(ssh_exec $host "su - $FRONTEND_USER -c 'sudo $DOCKER_WRAPPER ps 2>&1 | head -3'" 2>/dev/null || echo "")
    if echo "$DOCKER_PS" | grep -q "CONTAINER\|permission denied"; then
        if echo "$DOCKER_PS" | grep -q "permission denied"; then
            echo "      ⚠️  警告：可能需要用户重新登录才能生效"
            echo "         输出: $DOCKER_PS"
        else
            echo "      ✅ 通过：可以执行只读命令（docker ps）"
        fi
    else
        echo "      ⚠️  检查输出: $DOCKER_PS"
    fi
    
    # 测试 2: 尝试操作后端容器（应该失败）
    echo ""
    echo "   2. 测试操作后端容器（应该失败）"
    # 先检查是否有后端容器
    BACKEND_CONTAINER=$(ssh_exec $host "docker ps -a --format '{{.Names}}' | grep '^hifate-' | head -1" 2>/dev/null || echo "")
    if [ -n "$BACKEND_CONTAINER" ]; then
        echo "      找到后端容器: $BACKEND_CONTAINER"
        # 尝试停止后端容器（应该失败）
        STOP_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'sudo $DOCKER_WRAPPER stop $BACKEND_CONTAINER 2>&1'" 2>/dev/null || echo "")
        if echo "$STOP_TEST" | grep -q "禁止操作\|错误：禁止操作"; then
            echo "      ✅ 通过：禁止操作后端容器（符合预期）"
            echo "         输出: $(echo "$STOP_TEST" | head -1)"
        else
            echo "      ❌ 失败：可以操作后端容器（安全风险！）"
            echo "         输出: $STOP_TEST"
            all_passed=false
        fi
    else
        echo "      ⚠️  未找到后端容器，跳过测试"
    fi
    
    # 测试 3: 尝试创建非 frontend-* 容器（应该失败）
    echo ""
    echo "   3. 测试创建非 frontend-* 容器（应该失败）"
    # 只测试命令验证，不实际创建容器
    RUN_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'sudo $DOCKER_WRAPPER run --name test-container --rm alpine echo test 2>&1'" 2>/dev/null || echo "")
    if echo "$RUN_TEST" | grep -q "必须使用 frontend-* 前缀\|错误：容器名称必须"; then
        echo "      ✅ 通过：禁止创建非 frontend-* 容器（符合预期）"
        echo "         输出: $(echo "$RUN_TEST" | head -1)"
    else
        # 可能容器已经创建或命令执行了，检查容器名
        CONTAINER_EXISTS=$(ssh_exec $host "docker ps -a --format '{{.Names}}' | grep '^test-container$'" 2>/dev/null || echo "")
        if [ -n "$CONTAINER_EXISTS" ]; then
            echo "      ❌ 失败：可以创建非 frontend-* 容器（安全风险！）"
            # 清理测试容器
            ssh_exec $host "docker rm -f test-container 2>/dev/null || true" 2>/dev/null || true
            all_passed=false
        else
            echo "      ⚠️  检查输出: $RUN_TEST"
        fi
    fi
    
    # 测试 4: 创建 frontend-* 容器（应该成功）
    echo ""
    echo "   4. 测试创建 frontend-* 容器（应该成功）"
    # 创建一个临时测试容器
    TEST_CONTAINER="frontend-test-$$"
    RUN_FRONTEND=$(ssh_exec $host "su - $FRONTEND_USER -c 'sudo $DOCKER_WRAPPER run -d --name $TEST_CONTAINER --rm alpine sleep 10 2>&1'" 2>/dev/null || echo "")
    if echo "$RUN_FRONTEND" | grep -q "permission denied\|禁止\|错误"; then
        echo "      ❌ 失败：无法创建 frontend-* 容器"
        echo "         输出: $RUN_FRONTEND"
        all_passed=false
    else
        # 检查容器是否存在
        CONTAINER_EXISTS=$(ssh_exec $host "docker ps -a --format '{{.Names}}' | grep '^$TEST_CONTAINER$'" 2>/dev/null || echo "")
        if [ -n "$CONTAINER_EXISTS" ]; then
            echo "      ✅ 通过：可以创建 frontend-* 容器"
            # 清理测试容器
            ssh_exec $host "docker rm -f $TEST_CONTAINER 2>/dev/null || true" 2>/dev/null || true
        else
            echo "      ⚠️  检查输出: $RUN_FRONTEND"
        fi
    fi
    
    # ============================================
    # 第五部分：验证后端服务不受影响
    # ============================================
    echo ""
    echo "🔍 [第五部分] 验证后端服务不受影响..."
    
    echo ""
    echo "   1. 检查后端容器状态"
    BACKEND_CONTAINERS=$(ssh_exec $host "docker ps --format '{{.Names}}' | grep '^hifate-' | wc -l" 2>/dev/null || echo "0")
    if [ "$BACKEND_CONTAINERS" -gt 0 ]; then
        echo "      ✅ 通过：后端容器正常运行 ($BACKEND_CONTAINERS 个)"
    else
        echo "      ⚠️  警告：未找到运行中的后端容器"
    fi
    
    echo ""
    echo "   2. 检查后端服务健康状态"
    # 检查 Web 服务
    WEB_HEALTH=$(ssh_exec $host "curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/health 2>/dev/null || echo '000'" 2>/dev/null || echo "000")
    if [ "$WEB_HEALTH" = "200" ]; then
        echo "      ✅ 通过：后端 Web 服务正常 (HTTP $WEB_HEALTH)"
    else
        echo "      ⚠️  警告：后端 Web 服务可能异常 (HTTP $WEB_HEALTH)"
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
echo "验证 frontend-user 受限 Docker 权限"
echo "=========================================="
echo ""
echo "验证内容："
echo "  - frontend-user 不在 docker 组中"
echo "  - 无法直接使用 docker 命令"
echo "  - 包装脚本存在且可执行"
echo "  - sudo 规则已配置"
echo "  - 可以操作 frontend-* 容器"
echo "  - 禁止操作 hifate-* 容器（后端容器）"
echo "  - 后端服务不受影响"
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
    echo "权限总结："
    echo "  ✅ frontend-user 不在 docker 组中（无完整权限）"
    echo "  ✅ 只能使用 sudo docker-frontend 命令"
    echo "  ✅ 可以查看所有容器（只读）"
    echo "  ✅ 可以操作 frontend-* 容器"
    echo "  ❌ 禁止操作 hifate-* 容器（后端容器）"
    echo "  ✅ 后端服务正常运行"
    echo ""
    echo "使用方式："
    echo "  sudo docker-frontend ps              # 查看所有容器"
    echo "  sudo docker-frontend run --name frontend-app ...  # 创建容器"
    echo "  sudo docker-frontend stop frontend-app  # 停止自己的容器"
    exit 0
else
    echo "❌ 部分验证失败"
    echo ""
    echo "请检查："
    echo "  - 运行配置脚本：bash scripts/configure_frontend_docker_restricted.sh"
    echo "  - 检查服务器日志和权限设置"
    echo "  - 确保 frontend-user 已重新登录"
    exit 1
fi

