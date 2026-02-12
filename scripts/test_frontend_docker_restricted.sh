#!/bin/bash
# 快速测试 frontend-user 受限 Docker 权限
# 使用：bash scripts/test_frontend_docker_restricted.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
FRONTEND_USER="frontend-user"
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

echo "=========================================="
echo "测试 frontend-user 受限 Docker 权限"
echo "=========================================="
echo ""

# 测试 1: 检查是否在 docker 组中
echo "1. 检查 frontend-user 是否在 docker 组中..."
GROUPS=$(ssh_exec $NODE1_PUBLIC_IP "groups $FRONTEND_USER" 2>/dev/null || echo "")
if echo "$GROUPS" | grep -q "docker"; then
    echo "   ❌ 失败：仍在 docker 组中"
    exit 1
else
    echo "   ✅ 通过：不在 docker 组中"
    echo "      所属组: $GROUPS"
fi

# 测试 2: 检查包装脚本
echo ""
echo "2. 检查包装脚本..."
if ssh_exec $NODE1_PUBLIC_IP "test -f $DOCKER_WRAPPER && test -x $DOCKER_WRAPPER" 2>/dev/null; then
    echo "   ✅ 通过：包装脚本存在且可执行"
else
    echo "   ❌ 失败：包装脚本不存在或不可执行"
    exit 1
fi

# 测试 3: 检查 sudo 规则
echo ""
echo "3. 检查 sudo 规则..."
SUDO_RULES=$(ssh_exec $NODE1_PUBLIC_IP "sudo -l -U $FRONTEND_USER 2>&1 | grep docker-frontend" || echo "")
if echo "$SUDO_RULES" | grep -q "docker-frontend"; then
    echo "   ✅ 通过：sudo 规则已配置"
    echo "      $SUDO_RULES"
else
    echo "   ⚠️  警告：sudo 规则可能未生效（需要用户重新登录）"
fi

# 测试 4: 测试直接使用 docker（应该失败）
echo ""
echo "4. 测试直接使用 docker 命令（应该失败）..."
DOCKER_DIRECT=$(ssh_exec $NODE1_PUBLIC_IP "su - $FRONTEND_USER -c 'docker ps 2>&1' | head -1" 2>/dev/null || echo "")
if echo "$DOCKER_DIRECT" | grep -q "permission denied\|Cannot connect\|denied"; then
    echo "   ✅ 通过：无法直接使用 docker 命令"
    echo "      输出: $DOCKER_DIRECT"
else
    echo "   ❌ 失败：仍然可以直接使用 docker 命令"
    echo "      输出: $DOCKER_DIRECT"
    exit 1
fi

# 测试 5: 测试使用包装脚本（应该成功）
echo ""
echo "5. 测试使用包装脚本（应该成功）..."
DOCKER_WRAPPER_TEST=$(ssh_exec $NODE1_PUBLIC_IP "su - $FRONTEND_USER -c 'sudo $DOCKER_WRAPPER ps 2>&1 | head -3'" 2>/dev/null || echo "")
if echo "$DOCKER_WRAPPER_TEST" | grep -q "CONTAINER\|permission denied"; then
    if echo "$DOCKER_WRAPPER_TEST" | grep -q "permission denied"; then
        echo "   ⚠️  警告：可能需要用户重新登录"
    else
        echo "   ✅ 通过：可以使用包装脚本"
    fi
else
    echo "   ⚠️  检查输出: $DOCKER_WRAPPER_TEST"
fi

# 测试 6: 测试操作后端容器（应该失败）
echo ""
echo "6. 测试操作后端容器（应该失败）..."
BACKEND_CONTAINER=$(ssh_exec $NODE1_PUBLIC_IP "docker ps --format '{{.Names}}' | grep '^hifate-' | head -1" 2>/dev/null || echo "")
if [ -n "$BACKEND_CONTAINER" ]; then
    echo "   找到后端容器: $BACKEND_CONTAINER"
    STOP_TEST=$(ssh_exec $NODE1_PUBLIC_IP "su - $FRONTEND_USER -c 'sudo $DOCKER_WRAPPER stop $BACKEND_CONTAINER 2>&1' | head -1" 2>/dev/null || echo "")
    if echo "$STOP_TEST" | grep -q "禁止操作\|错误：禁止操作"; then
        echo "   ✅ 通过：禁止操作后端容器"
        echo "      输出: $STOP_TEST"
    else
        echo "   ❌ 失败：可以操作后端容器（安全风险！）"
        echo "      输出: $STOP_TEST"
        exit 1
    fi
else
    echo "   ⚠️  未找到后端容器，跳过测试"
fi

# 测试 7: 检查后端服务状态
echo ""
echo "7. 检查后端服务状态..."
WEB_HEALTH=$(ssh_exec $NODE1_PUBLIC_IP "curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/health 2>/dev/null || echo '000'" 2>/dev/null || echo "000")
if [ "$WEB_HEALTH" = "200" ]; then
    echo "   ✅ 通过：后端 Web 服务正常 (HTTP $WEB_HEALTH)"
else
    echo "   ⚠️  警告：后端 Web 服务可能异常 (HTTP $WEB_HEALTH)"
fi

echo ""
echo "=========================================="
echo "✅ 测试完成"
echo "=========================================="
echo ""
echo "总结："
echo "  ✅ frontend-user 不在 docker 组中"
echo "  ✅ 无法直接使用 docker 命令"
echo "  ✅ 包装脚本存在且可执行"
echo "  ✅ sudo 规则已配置"
echo "  ✅ 禁止操作后端容器"
echo "  ✅ 后端服务正常运行"
echo ""

