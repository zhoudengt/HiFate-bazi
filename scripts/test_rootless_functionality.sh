#!/bin/bash
# 测试 Rootless Docker 功能
# 使用：bash scripts/test_rootless_functionality.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
FRONTEND_USER="frontend-user"
TEST_CONTAINER="frontend-test-nginx"

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

test_node() {
    local host=$1
    local node_name=$2
    
    echo "=========================================="
    echo "测试 $node_name ($host) Rootless Docker 功能"
    echo "=========================================="
    
    # 设置环境变量
    ENV_SETUP="export XDG_RUNTIME_DIR=\$HOME/.docker/run && export PATH=\$HOME/bin:\$PATH && export DOCKER_HOST=unix://\$HOME/.docker/run/docker.sock"
    
    # 1. 清理测试容器（如果存在）
    echo ""
    echo "1. 清理旧的测试容器..."
    ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker rm -f $TEST_CONTAINER 2>/dev/null' || true" 2>/dev/null
    echo "   ✅ 清理完成"
    
    # 2. 测试创建容器
    echo ""
    echo "2. 测试创建容器..."
    CREATE_OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker run -d --name $TEST_CONTAINER --network frontend-network -p 8080:80 nginx:alpine 2>&1' 2>/dev/null" || echo "创建失败")
    
    if echo "$CREATE_OUTPUT" | grep -qE "^[a-f0-9]{64}$|^[a-f0-9]{12}$"; then
        echo "   ✅ 容器创建成功"
        CONTAINER_ID=$(echo "$CREATE_OUTPUT" | head -1)
        echo "   容器 ID: $CONTAINER_ID"
    else
        echo "   ❌ 容器创建失败"
        echo "   输出: $CREATE_OUTPUT"
        return 1
    fi
    
    # 等待容器启动
    sleep 2
    
    # 3. 测试查看容器
    echo ""
    echo "3. 测试查看容器..."
    CONTAINER_LIST=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker ps --format \"{{.Names}}\\t{{.Status}}\" | grep $TEST_CONTAINER' 2>/dev/null" || echo "")
    if [ -n "$CONTAINER_LIST" ]; then
        echo "   ✅ 容器运行中:"
        echo "   $CONTAINER_LIST" | sed 's/^/     /'
    else
        echo "   ❌ 容器未运行"
        return 1
    fi
    
    # 4. 测试网络连接
    echo ""
    echo "4. 测试网络连接..."
    NETWORK_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker network inspect frontend-network --format \"{{range .Containers}}{{.Name}} {{end}}\" 2>&1' 2>/dev/null" || echo "")
    if echo "$NETWORK_TEST" | grep -q "$TEST_CONTAINER"; then
        echo "   ✅ 容器已连接到 frontend-network"
    else
        echo "   ⚠️  容器网络连接可能有问题"
        echo "   输出: $NETWORK_TEST"
    fi
    
    # 5. 测试端口映射（检查端口是否监听）
    echo ""
    echo "5. 测试端口映射..."
    PORT_TEST=$(ssh_exec $host "netstat -tlnp 2>/dev/null | grep ':8080 ' || ss -tlnp 2>/dev/null | grep ':8080 '" || echo "无法检查")
    if echo "$PORT_TEST" | grep -q "8080"; then
        echo "   ✅ 端口 8080 已监听"
    else
        echo "   ⚠️  端口 8080 可能未监听（Rootless Docker 端口映射可能需要特殊配置）"
    fi
    
    # 6. 测试容器日志
    echo ""
    echo "6. 测试容器日志..."
    LOG_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker logs $TEST_CONTAINER 2>&1 | head -3' 2>/dev/null" || echo "无法获取")
    if [ -n "$LOG_TEST" ] && [ "$LOG_TEST" != "无法获取" ]; then
        echo "   ✅ 可以查看容器日志"
        echo "   日志（前3行）:"
        echo "$LOG_TEST" | sed 's/^/     /'
    else
        echo "   ⚠️  无法查看容器日志"
    fi
    
    # 7. 测试停止容器
    echo ""
    echo "7. 测试停止容器..."
    STOP_OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker stop $TEST_CONTAINER 2>&1' 2>/dev/null" || echo "停止失败")
    if echo "$STOP_OUTPUT" | grep -q "$TEST_CONTAINER"; then
        echo "   ✅ 容器已停止"
    else
        echo "   ⚠️  容器停止可能失败"
        echo "   输出: $STOP_OUTPUT"
    fi
    
    # 8. 测试启动容器
    echo ""
    echo "8. 测试启动容器..."
    START_OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker start $TEST_CONTAINER 2>&1' 2>/dev/null" || echo "启动失败")
    if echo "$START_OUTPUT" | grep -q "$TEST_CONTAINER"; then
        echo "   ✅ 容器已启动"
    else
        echo "   ⚠️  容器启动可能失败"
        echo "   输出: $START_OUTPUT"
    fi
    
    # 9. 测试删除容器
    echo ""
    echo "9. 测试删除容器..."
    RM_OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c '$ENV_SETUP && docker rm -f $TEST_CONTAINER 2>&1' 2>/dev/null" || echo "删除失败")
    if echo "$RM_OUTPUT" | grep -q "$TEST_CONTAINER"; then
        echo "   ✅ 容器已删除"
    else
        echo "   ⚠️  容器删除可能失败"
        echo "   输出: $RM_OUTPUT"
    fi
    
    echo ""
    echo "✅ $node_name 功能测试完成"
    echo ""
}

echo "=========================================="
echo "测试 Rootless Docker 功能（双机）"
echo "=========================================="
echo ""
echo "测试内容："
echo "  - 创建容器"
echo "  - 查看容器"
echo "  - 网络连接"
echo "  - 端口映射"
echo "  - 容器日志"
echo "  - 停止/启动容器"
echo "  - 删除容器"
echo ""

# 测试 Node1
test_node $NODE1_PUBLIC_IP "Node1"

# 测试 Node2
test_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "✅ 功能测试完成"
echo "=========================================="
echo ""
echo "下一步：更新文档"
echo ""

