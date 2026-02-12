#!/bin/bash
# 直接重启双机后端Docker容器并监控内存
set -e

NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
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
echo "🔄 重启双机后端Docker容器"
echo "========================================"

# 重启Node1
echo "🔄 重启 Node1 容器..."
ssh_exec $NODE1_IP "cd $PROJECT_DIR/deploy/docker && \
    source $PROJECT_DIR/.env && \
    docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml \
    --env-file $PROJECT_DIR/.env restart mysql redis" || \
ssh_exec $NODE1_IP "docker restart hifate-mysql-master hifate-redis-master 2>/dev/null || true"

# 重启Node2
echo "🔄 重启 Node2 容器..."
ssh_exec $NODE2_IP "cd $PROJECT_DIR/deploy/docker && \
    source $PROJECT_DIR/.env && \
    docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \
    --env-file $PROJECT_DIR/.env restart mysql redis" || \
ssh_exec $NODE2_IP "docker restart hifate-mysql-slave hifate-redis-slave 2>/dev/null || true"

echo "⏳ 等待容器启动（15秒）..."
sleep 15

echo ""
echo "========================================"
echo "📊 内存使用情况报告"
echo "========================================"
echo ""

# Node1内存报告
echo "【Node1 - $NODE1_IP】"
echo "----------------------------------------"
echo "系统内存："
ssh_exec $NODE1_IP "free -h | head -2"
echo ""
echo "容器内存使用："
ssh_exec $NODE1_IP "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | grep -E 'NAME|hifate-' | head -15"
echo ""

# Node2内存报告
echo "【Node2 - $NODE2_IP】"
echo "----------------------------------------"
echo "系统内存："
ssh_exec $NODE2_IP "free -h | head -2"
echo ""
echo "容器内存使用："
ssh_exec $NODE2_IP "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | grep -E 'NAME|hifate-' | head -15"
echo ""

# 内存使用分析
echo "========================================"
echo "📈 内存使用分析"
echo "========================================"
echo ""

echo "【Node1 内存分配】"
ssh_exec $NODE1_IP "echo '容器内存限制:' && \
    docker inspect \$(docker ps --format '{{.Names}}' | grep hifate) 2>/dev/null | \
    grep -A 2 'Memory' | grep -E 'Limit|Reservation' | \
    awk '{name=\$1; limit=\$2/1024/1024/1024; print name \" \" limit \"GB\"}' | \
    sort -k2 -rn | head -10 || echo '无法获取'"

echo ""
echo "【Node2 内存分配】"
ssh_exec $NODE2_IP "echo '容器内存限制:' && \
    docker inspect \$(docker ps --format '{{.Names}}' | grep hifate) 2>/dev/null | \
    grep -A 2 'Memory' | grep -E 'Limit|Reservation' | \
    awk '{name=\$1; limit=\$2/1024/1024/1024; print name \" \" limit \"GB\"}' | \
    sort -k2 -rn | head -10 || echo '无法获取'"

echo ""
echo "========================================"
echo "✅ 重启完成"
echo "========================================"

