#!/bin/bash
# 直接使用docker update应用内存限制
set -e

NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

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
echo "🔧 应用内存限制配置"
echo "========================================"

# Node1: 应用内存限制（同时设置memory和memoryswap）
echo "🔧 Node1: 应用内存限制..."
ssh_exec $NODE1_IP "
    docker update --memory=1g --memory-swap=1g --memory-reservation=600m hifate-mysql-master
    docker update --memory=350m --memory-swap=350m --memory-reservation=200m hifate-redis-master
    docker update --memory=100m --memory-swap=100m --memory-reservation=64m hifate-nginx
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-bazi-core
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-bazi-fortune
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-bazi-analyzer
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-rule-service
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-fortune-analyzer
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-payment-service
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-fortune-rule
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-intent-service
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-prompt-optimizer
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-desk-fengshui
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-auth-service
    echo '✅ Node1 内存限制已应用'
"

# Node2: 应用内存限制（同时设置memory和memoryswap）
echo "🔧 Node2: 应用内存限制..."
ssh_exec $NODE2_IP "
    docker update --memory=1g --memory-swap=1g --memory-reservation=600m hifate-mysql-slave
    docker update --memory=350m --memory-swap=350m --memory-reservation=200m hifate-redis-slave
    docker update --memory=100m --memory-swap=100m --memory-reservation=64m hifate-nginx
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-bazi-core
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-bazi-fortune
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-bazi-analyzer
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-rule-service
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-fortune-analyzer
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-payment-service
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-fortune-rule
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-intent-service
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-prompt-optimizer
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-desk-fengshui
    docker update --memory=150m --memory-swap=150m --memory-reservation=100m hifate-auth-service
    echo '✅ Node2 内存限制已应用'
"

echo ""
echo "⏳ 等待5秒让配置生效..."
sleep 5

echo ""
echo "========================================"
echo "📊 内存使用情况详细报告"
echo "========================================"
echo ""

# 生成详细报告
for node in "Node1:$NODE1_IP" "Node2:$NODE2_IP"; do
    IFS=':' read -r node_name node_ip <<< "$node"
    echo "【$node_name - $node_ip】"
    echo "----------------------------------------"
    echo "系统内存："
    ssh_exec $node_ip "free -h | head -2"
    echo ""
    echo "容器内存使用（实际使用 / 限制）："
    ssh_exec $node_ip "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | \
        grep hifate | sort -k3 -rn | \
        awk '{
            name=\$1
            usage=\$2
            perc=\$3
            printf \"%-30s %15s %10s\n\", name, usage, perc
        }' | \
        awk 'BEGIN {printf \"%-30s %15s %10s\n\", \"容器名称\", \"内存使用\", \"占比\"} {print}'"
    echo ""
done

echo "========================================"
echo "📈 内存使用分析"
echo "========================================"
echo ""

echo "【内存占用TOP5 - Node1】"
ssh_exec $NODE1_IP "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' | \
    grep hifate | sort -k2 -hr | head -5 | \
    awk '{printf \"  %-30s %s\n\", \$1, \$2}'"
echo ""

echo "【内存占用TOP5 - Node2】"
ssh_exec $NODE2_IP "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' | \
    grep hifate | sort -k2 -hr | head -5 | \
    awk '{printf \"  %-30s %s\n\", \$1, \$2}'"
echo ""

echo "【内存使用分布】"
echo "  Node1:"
ssh_exec $NODE1_IP "echo '  MySQL: ' \$(docker stats --no-stream --format '{{.MemUsage}}' hifate-mysql-master 2>/dev/null | awk '{print \$1}') && \
    echo '  Redis: ' \$(docker stats --no-stream --format '{{.MemUsage}}' hifate-redis-master 2>/dev/null | awk '{print \$1}') && \
    echo '  微服务总计: ' \$(docker stats --no-stream --format '{{.MemUsage}}' \$(docker ps --format '{{.Names}}' | grep -E 'hifate-(bazi-|rule-|fortune-|payment-|intent-|prompt-|desk-|auth-)') 2>/dev/null | awk '{sum+=\$1} END {print sum \"MiB\"}') && \
    echo '  Nginx: ' \$(docker stats --no-stream --format '{{.MemUsage}}' hifate-nginx 2>/dev/null | awk '{print \$1}')"
echo "  Node2:"
ssh_exec $NODE2_IP "echo '  MySQL: ' \$(docker stats --no-stream --format '{{.MemUsage}}' hifate-mysql-slave 2>/dev/null | awk '{print \$1}') && \
    echo '  Redis: ' \$(docker stats --no-stream --format '{{.MemUsage}}' hifate-redis-slave 2>/dev/null | awk '{print \$1}') && \
    echo '  微服务总计: ' \$(docker stats --no-stream --format '{{.MemUsage}}' \$(docker ps --format '{{.Names}}' | grep -E 'hifate-(bazi-|rule-|fortune-|payment-|intent-|prompt-|desk-|auth-)') 2>/dev/null | awk '{sum+=\$1} END {print sum \"MiB\"}') && \
    echo '  Nginx: ' \$(docker stats --no-stream --format '{{.MemUsage}}' hifate-nginx 2>/dev/null | awk '{print \$1}')"
echo ""

echo "========================================"
echo "✅ 内存限制配置应用完成"
echo "========================================"

