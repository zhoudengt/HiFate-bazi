#!/bin/bash
# 重启容器以应用配置优化（排除Nginx）
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
echo "🔄 重启容器以应用配置优化"
echo "========================================"
echo ""

# Node1: 重启MySQL、Redis和所有微服务
echo "🔄 Node1: 重启MySQL、Redis和微服务..."
ssh_exec $NODE1_IP "cd $PROJECT_DIR/deploy/docker && \
    source $PROJECT_DIR/.env && \
    docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml \
    --env-file $PROJECT_DIR/.env restart mysql redis bazi-core bazi-fortune bazi-analyzer rule-service fortune-analyzer payment-service fortune-rule intent-service prompt-optimizer desk-fengshui auth-service web"

echo "⏳ 等待Node1容器启动（25秒）..."
sleep 25

# Node2: 重启MySQL、Redis和所有微服务
echo "🔄 Node2: 重启MySQL、Redis和微服务..."
ssh_exec $NODE2_IP "cd $PROJECT_DIR/deploy/docker && \
    source $PROJECT_DIR/.env && \
    docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \
    --env-file $PROJECT_DIR/.env restart mysql redis bazi-core bazi-fortune bazi-analyzer rule-service fortune-analyzer payment-service fortune-rule intent-service prompt-optimizer desk-fengshui auth-service web"

echo "⏳ 等待Node2容器启动（25秒）..."
sleep 25

echo ""
echo "========================================"
echo "📊 重启后内存使用情况对比"
echo "========================================"
echo ""

for node_info in "Node1:$NODE1_IP" "Node2:$NODE2_IP"; do
    IFS=":" read -r node_name node_ip <<< "$node_info"
    echo "【$node_name - $node_ip】"
    echo "----------------------------------------"
    echo "系统内存："
    ssh_exec $node_ip "free -h | head -2"
    echo ""
    echo "MySQL内存使用："
    mysql_name="hifate-mysql-${node_name,,}"
    ssh_exec $node_ip "docker stats --no-stream --format '{{.MemUsage}}' $mysql_name 2>/dev/null || echo '未找到'"
    echo ""
    echo "Redis内存使用："
    redis_name="hifate-redis-${node_name,,}"
    ssh_exec $node_ip "docker stats --no-stream --format '{{.MemUsage}}' $redis_name 2>/dev/null || echo '未找到'"
    echo ""
    echo "所有容器内存使用："
    ssh_exec $node_ip "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | grep hifate | head -15"
    echo ""
done

echo "========================================"
echo "✅ 容器重启完成"
echo "========================================"
echo ""
echo "配置优化已应用："
echo "  ✅ MySQL: innodb_buffer_pool_size = 800M (从2G降低，需要重启生效)"
echo "  ✅ Redis: maxmemory = 300MB (从1GB降低，需要重启生效)"
echo "  ✅ 所有微服务: 内存限制 = 240MB"
echo ""
echo "预期效果："
echo "  - MySQL内存使用应降低（从~500MB降到~400MB）"
echo "  - Redis内存使用应降低（从~20MB降到~15MB）"
echo "  - 系统总内存使用应降低约200-300MB"
echo ""

