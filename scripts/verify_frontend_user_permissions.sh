#!/bin/bash
# 验证 frontend-user 权限配置
# 使用：bash scripts/verify_frontend_user_permissions.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
FRONTEND_USER="frontend-user"
FRONTEND_DIR="/opt/hifate-frontend"
PROJECT_DIR="/opt/HiFate-bazi"

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
    
    # 测试 1: 可以访问 /opt/hifate-frontend
    echo ""
    echo "测试 1: frontend-user 可以访问 $FRONTEND_DIR"
    if ssh_exec $host "su - $FRONTEND_USER -c 'cd $FRONTEND_DIR && pwd'" 2>/dev/null; then
        echo "  ✅ 通过：可以进入目录"
    else
        echo "  ❌ 失败：无法进入目录"
    fi
    
    # 测试 2: 可以读写文件
    echo ""
    echo "测试 2: frontend-user 可以在 $FRONTEND_DIR 创建文件"
    TEST_FILE="$FRONTEND_DIR/.test_\$\$"
    if ssh_exec $host "su - $FRONTEND_USER -c 'touch $TEST_FILE && rm -f $TEST_FILE && echo ok'" 2>/dev/null | grep -q "ok"; then
        echo "  ✅ 通过：可以创建和删除文件"
    else
        echo "  ❌ 失败：无法创建文件"
    fi
    
    # 测试 3: 无法访问 /opt/HiFate-bazi
    echo ""
    echo "测试 3: frontend-user 无法访问 $PROJECT_DIR"
    OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c 'ls $PROJECT_DIR 2>&1'" 2>/dev/null || echo "")
    if echo "$OUTPUT" | grep -q "Permission denied\|cannot access\|No such file"; then
        echo "  ✅ 通过：无法访问（符合预期）"
        echo "    输出: $(echo "$OUTPUT" | head -1)"
    else
        echo "  ❌ 失败：仍然可以访问"
        echo "    输出: $OUTPUT"
    fi
    
    # 测试 4: 无法列出 /opt 下的其他目录
    echo ""
    echo "测试 4: frontend-user 无法列出 /opt 下的其他目录"
    OPT_OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c 'ls /opt 2>&1'" 2>/dev/null || echo "")
    if echo "$OPT_OUTPUT" | grep -q "Permission denied\|cannot access"; then
        echo "  ✅ 通过：无法列出（符合预期）"
        echo "    输出: Permission denied"
    elif echo "$OPT_OUTPUT" | grep -q "hifate-frontend"; then
        if echo "$OPT_OUTPUT" | grep -q "HiFate-bazi"; then
            echo "  ❌ 失败：可以看到 HiFate-bazi（不应该看到）"
            echo "    输出: $OPT_OUTPUT"
        else
            echo "  ✅ 通过：只能看到 hifate-frontend，看不到 HiFate-bazi"
            echo "    输出: $OPT_OUTPUT"
        fi
    else
        echo "  ⚠️  检查输出: $OPT_OUTPUT"
    fi
    
    # 测试 5: 检查权限
    echo ""
    echo "测试 5: 检查目录权限"
    OPT_PERM=$(ssh_exec $host "stat -c '%a' /opt" 2>/dev/null || echo "")
    FRONTEND_PERM=$(ssh_exec $host "stat -c '%a' $FRONTEND_DIR" 2>/dev/null || echo "")
    PROJECT_PERM=$(ssh_exec $host "stat -c '%a' $PROJECT_DIR" 2>/dev/null || echo "")
    echo "  /opt 权限: $OPT_PERM (应为 751)"
    echo "  $FRONTEND_DIR 权限: $FRONTEND_PERM (应为 775)"
    echo "  $PROJECT_DIR 权限: $PROJECT_PERM (应为 750)"
    
    if [ "$OPT_PERM" = "751" ] && [ "$FRONTEND_PERM" = "775" ] && [ "$PROJECT_PERM" = "750" ]; then
        echo "  ✅ 通过：所有权限设置正确"
    else
        echo "  ⚠️  警告：部分权限设置可能不正确"
    fi
    
    echo ""
}

echo "=========================================="
echo "验证 frontend-user 权限配置"
echo "=========================================="
echo ""

# 验证 Node1
verify_node $NODE1_PUBLIC_IP "Node1"

# 验证 Node2
verify_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "验证完成"
echo "=========================================="

