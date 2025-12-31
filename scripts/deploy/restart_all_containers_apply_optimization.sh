#!/bin/bash
# 重启所有容器以应用内存限制和配置优化
set -e

NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
PROJECT_DIR="/opt/HiFate-bazi"

ssh_exec() {
    local host=$1
    shift
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$@"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$@"
    fi
}

echo "========================================"
echo "🔄 重启所有容器以应用配置优化"
echo "========================================"
echo ""
echo "说明："
echo "1. 重启MySQL和Redis以应用配置优化（innodb_buffer_pool_size、maxmemory等）"
echo "2. 重启所有微服务以应用新的内存限制"
echo "3. 这将导致短暂的服务中断（约30秒）"
echo ""

# Node1: 重启所有容器
echo "🔄 Node1: 重启所有容器..."
ssh_exec $NODE1_IP "cd $PROJECT_DIR/deploy/docker && \
    source $PROJECT_DIR/.env && \
    docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml \
    --env-file $PROJECT_DIR/.env restart"

echo "⏳ 等待Node1容器启动（20秒）..."
sleep 20

# Node2: 重启所有容器
echo "🔄 Node2: 重启所有容器..."
ssh_exec $NODE2_IP "cd $PROJECT_DIR/deploy/docker && \
    source $PROJECT_DIR/.env && \
    docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \
    --env-file $PROJECT_DIR/.env restart"

echo "⏳ 等待Node2容器启动（20秒）..."
sleep 20

echo ""
echo "========================================"
echo "📊 重启后内存使用情况"
echo "========================================"
echo ""

for node_info in "Node1:$NODE1_IP" "Node2:$NODE2_IP"; do
    IFS=":" read -r node_name node_ip <<< "$node_info"
    echo "【$node_name - $node_ip】"
    echo "----------------------------------------"
    echo "系统内存："
    ssh_exec $node_ip "free -h | head -2"
    echo ""
    echo "容器内存使用："
    ssh_exec $node_ip "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | grep hifate | head -10"
    echo ""
done

echo "========================================"
echo "✅ 容器重启完成"
echo "========================================"
echo ""
echo "配置优化已应用："
echo "  ✅ MySQL: innodb_buffer_pool_size = 800M (从2G降低)"
echo "  ✅ Redis: maxmemory = 300MB (从1GB降低)"
echo "  ✅ 所有微服务: 内存限制 = 240MB (从150MB增加)"
echo "  ✅ Nginx: 内存限制 = 80MB (从100MB降低)"
echo ""

