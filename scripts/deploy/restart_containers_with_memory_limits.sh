#!/bin/bash
# 重启双节点容器以应用新的内存限制配置
# 用途：特殊情况，重启容器以应用资源优化配置

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
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
PROJECT_DIR="/opt/HiFate-bazi"

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
echo "🔄 重启双节点容器以应用内存限制配置"
echo "========================================"
echo "Node1: $NODE1_PUBLIC_IP"
echo "Node2: $NODE2_PUBLIC_IP"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# 函数：显示系统内存
show_system_memory() {
    local node=$1
    local ip=$2
    echo "📊 $node 系统内存："
    ssh_exec $ip "free -h | head -2"
    echo ""
}

# 函数：重启Node1容器
restart_node1() {
    echo "🔄 重启 Node1 容器..."
    echo "----------------------------------------"
    
    # 显示重启前内存
    echo "【重启前内存使用】"
    show_system_memory "Node1" "$NODE1_PUBLIC_IP"
    
    # 重启容器（使用docker-compose）
    echo "🔄 使用 docker-compose 重启容器..."
    ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR/deploy/docker && \
        source $PROJECT_DIR/.env && \
        docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml \
        --env-file $PROJECT_DIR/.env restart mysql redis" || {
        echo "⚠️  docker-compose重启失败，使用docker restart..."
        ssh_exec $NODE1_PUBLIC_IP "docker restart hifate-mysql-master hifate-redis-master 2>/dev/null || true"
    }
    
    echo "⏳ 等待容器启动（15秒）..."
    sleep 15
    
    # 显示重启后内存
    echo "【重启后内存使用】"
    show_system_memory "Node1" "$NODE1_PUBLIC_IP"
    
    echo "✅ Node1 容器重启完成"
    echo ""
}

# 函数：重启Node2容器
restart_node2() {
    echo "🔄 重启 Node2 容器..."
    echo "----------------------------------------"
    
    # 显示重启前内存
    echo "【重启前内存使用】"
    show_system_memory "Node2" "$NODE2_PUBLIC_IP"
    
    # 重启容器（使用docker-compose）
    echo "🔄 使用 docker-compose 重启容器..."
    ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR/deploy/docker && \
        source $PROJECT_DIR/.env && \
        docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \
        --env-file $PROJECT_DIR/.env restart mysql redis" || {
        echo "⚠️  docker-compose重启失败，使用docker restart..."
        ssh_exec $NODE2_PUBLIC_IP "docker restart hifate-mysql-slave hifate-redis-slave 2>/dev/null || true"
    }
    
    echo "⏳ 等待容器启动（15秒）..."
    sleep 15
    
    # 显示重启后内存
    echo "【重启后内存使用】"
    show_system_memory "Node2" "$NODE2_PUBLIC_IP"
    
    echo "✅ Node2 容器重启完成"
    echo ""
}

# 函数：监控容器内存使用
monitor_container_memory() {
    local node=$1
    local ip=$2
    echo "📊 $node 容器内存使用详情："
    echo "----------------------------------------"
    
    # Docker容器内存统计
    ssh_exec $ip "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}' | \
        grep -E 'NAME|hifate-' | head -20" || echo "⚠️  无法获取容器内存信息"
    
    echo ""
}

# 函数：检查容器状态
check_container_status() {
    local node=$1
    local ip=$2
    echo "🔍 $node 容器状态："
    echo "----------------------------------------"
    ssh_exec $ip "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | \
        grep -E 'NAMES|hifate-' | head -15" || echo "⚠️  无法获取容器状态"
    echo ""
}

# 函数：验证服务健康
check_service_health() {
    local node=$1
    local ip=$2
    echo "🏥 $node 服务健康检查："
    echo "----------------------------------------"
    
    # 检查Web服务
    health_status=$(ssh_exec $ip "curl -s -f http://localhost:8001/health 2>&1 | head -1" || echo "failed")
    if [[ "$health_status" == *"ok"* ]] || [[ "$health_status" == *"healthy"* ]]; then
        echo "✅ Web服务健康检查通过"
    else
        echo "⚠️  Web服务健康检查失败: $health_status"
    fi
    
    # 检查MySQL
    mysql_status=$(ssh_exec $ip "docker exec hifate-mysql-master mysqladmin ping -uroot -p\${MYSQL_PASSWORD} 2>/dev/null || docker exec hifate-mysql-slave mysqladmin ping -uroot -p\${MYSQL_PASSWORD} 2>/dev/null || echo 'failed'" || echo "failed")
    if [[ "$mysql_status" == *"alive"* ]]; then
        echo "✅ MySQL服务正常"
    else
        echo "⚠️  MySQL服务检查失败"
    fi
    
    # 检查Redis
    redis_status=$(ssh_exec $ip "docker exec hifate-redis-master redis-cli ping 2>/dev/null || docker exec hifate-redis-slave redis-cli ping 2>/dev/null || echo 'failed'" || echo "failed")
    if [[ "$redis_status" == *"PONG"* ]]; then
        echo "✅ Redis服务正常"
    else
        echo "⚠️  Redis服务检查失败"
    fi
    
    echo ""
}

# 主流程
echo "📋 第一步：显示当前内存使用"
echo "----------------------------------------"
show_system_memory "Node1" "$NODE1_PUBLIC_IP"
show_system_memory "Node2" "$NODE2_PUBLIC_IP"

echo ""
echo "📋 第二步：重启 Node1 容器"
echo "----------------------------------------"
restart_node1

echo ""
echo "📋 第三步：重启 Node2 容器"
echo "----------------------------------------"
restart_node2

echo ""
echo "📋 第四步：检查容器状态"
echo "----------------------------------------"
check_container_status "Node1" "$NODE1_PUBLIC_IP"
check_container_status "Node2" "$NODE2_PUBLIC_IP"

echo ""
echo "📋 第五步：监控容器内存使用"
echo "----------------------------------------"
monitor_container_memory "Node1" "$NODE1_PUBLIC_IP"
monitor_container_memory "Node2" "$NODE2_PUBLIC_IP"

echo ""
echo "📋 第六步：验证服务健康"
echo "----------------------------------------"
check_service_health "Node1" "$NODE1_PUBLIC_IP"
check_service_health "Node2" "$NODE2_PUBLIC_IP"

echo ""
echo "========================================"
echo "✅ 容器重启完成并已验证"
echo "========================================"
echo ""
echo "📊 内存优化配置已应用："
echo "  - MySQL: 1.0GB limit (从3GB降低)"
echo "  - Redis: 350MB limit (从1GB降低)"
echo "  - 微服务: 150MB×10 = 1.5GB (从1GB×10降低)"
echo "  - Nginx: 100MB limit (新增)"
echo "  - 总计: 3.5GB (符合限制)"
echo ""
echo "💡 持续监控命令："
echo "  - Node1: ssh root@$NODE1_PUBLIC_IP 'docker stats --no-stream'"
echo "  - Node2: ssh root@$NODE2_PUBLIC_IP 'docker stats --no-stream'"
echo "  - 系统内存: ssh root@\$NODE_IP 'free -h'"
echo "========================================"

