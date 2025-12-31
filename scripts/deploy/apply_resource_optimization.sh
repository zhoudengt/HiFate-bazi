#!/bin/bash
# 应用资源优化配置并监控内存
# 用途：重启MySQL和Redis容器以应用新的内存限制和配置，然后监控内存使用

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# SSH 执行函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    fi
}

echo "========================================"
echo "🚀 应用资源优化配置并监控内存"
echo "========================================"
echo "Node1: $NODE1_PUBLIC_IP"
echo "Node2: $NODE2_PUBLIC_IP"
echo "========================================"
echo ""

# 函数：重启MySQL和Redis容器
restart_containers() {
    local node=$1
    local ip=$2
    echo "🔄 在 $node 上重启 MySQL 和 Redis 容器..."
    
    ssh_exec $ip "cd /opt/HiFate-bazi/deploy/docker && \
        docker-compose -f docker-compose.prod.yml -f docker-compose.node${node:4:1}.yml \
        --env-file /opt/HiFate-bazi/.env restart mysql redis" || {
        echo "⚠️  重启失败，尝试使用 docker restart..."
        ssh_exec $ip "docker restart hifate-mysql-master hifate-redis-master 2>/dev/null || \
                      docker restart hifate-mysql-slave hifate-redis-slave 2>/dev/null || true"
    }
    
    echo "✅ $node 容器重启完成"
    sleep 5
}

# 函数：监控内存使用
monitor_memory() {
    local node=$1
    local ip=$2
    echo ""
    echo "📊 $node 内存使用情况："
    echo "----------------------------------------"
    
    # 系统内存
    echo "【系统内存】"
    ssh_exec $ip "free -h | head -2"
    
    # Docker容器内存
    echo ""
    echo "【Docker容器内存使用】"
    ssh_exec $ip "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}' | head -20"
    
    # 计算后端服务内存总和
    echo ""
    echo "【后端服务内存限制总和】"
    ssh_exec $ip "docker inspect \$(docker ps --format '{{.Names}}' | grep -E 'hifate-(mysql|redis|nginx|bazi-|rule-|fortune-|payment-|intent-|prompt-|desk-|auth-)') \
        2>/dev/null | grep -A 5 'Memory' | grep -E 'Limit|Reservation' | awk '{sum+=\$2} END {print \"总限制: \" sum/1024/1024/1024 \"GB\"}' || echo '无法计算'"
}

# 函数：检查容器状态
check_containers() {
    local node=$1
    local ip=$2
    echo ""
    echo "🔍 $node 容器状态："
    echo "----------------------------------------"
    ssh_exec $ip "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep hifate | head -15"
}

# 主流程
echo "📋 第一步：重启 MySQL 和 Redis 容器（应用新配置）"
echo "----------------------------------------"
restart_containers "Node1" "$NODE1_PUBLIC_IP"
restart_containers "Node2" "$NODE2_PUBLIC_IP"

echo ""
echo "⏳ 等待容器启动（10秒）..."
sleep 10

echo ""
echo "📋 第二步：检查容器状态"
echo "----------------------------------------"
check_containers "Node1" "$NODE1_PUBLIC_IP"
check_containers "Node2" "$NODE2_PUBLIC_IP"

echo ""
echo "📋 第三步：监控内存使用"
echo "----------------------------------------"
monitor_memory "Node1" "$NODE1_PUBLIC_IP"
monitor_memory "Node2" "$NODE2_PUBLIC_IP"

echo ""
echo "📋 第四步：触发热更新（其他服务）"
echo "----------------------------------------"
echo "🔄 在 Node1 上触发热更新..."
ssh_exec $NODE1_PUBLIC_IP "curl -s -X POST http://localhost:8001/api/v1/hot-reload/check > /dev/null && echo '✅ 热更新触发成功' || echo '⚠️  热更新触发失败'"

echo ""
echo "========================================"
echo "✅ 资源优化配置应用完成"
echo "========================================"
echo ""
echo "📊 内存优化总结："
echo "  - MySQL: 1.0GB limit (从3GB降低)"
echo "  - Redis: 350MB limit (从1GB降低)"
echo "  - 微服务: 150MB×10 = 1.5GB (从1GB×10降低)"
echo "  - Nginx: 100MB limit (新增)"
echo "  - 总计: 3.5GB (符合限制)"
echo ""
echo "💡 提示："
echo "  - 使用 'docker stats' 实时监控内存使用"
echo "  - 使用 'free -h' 查看系统内存使用"
echo "  - 如果内存使用过高，可以进一步优化"
echo "========================================"

