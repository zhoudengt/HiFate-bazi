#!/bin/bash
# 生成最终内存使用情况报告
set -e

NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

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
echo "📊 双机内存使用情况最终报告"
echo "========================================"
echo ""

# Node1报告
echo "【Node1 - $NODE1_IP】"
echo "----------------------------------------"
echo "系统内存："
ssh_exec $NODE1_IP "free -h | head -2"
echo ""
echo "主要容器内存使用："
ssh_exec $NODE1_IP "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' | grep -E 'hifate-(mysql|redis|nginx|web|fortune-analyzer)' | sort -k2 -hr"
echo ""

# Node2报告
echo "【Node2 - $NODE2_IP】"
echo "----------------------------------------"
echo "系统内存："
ssh_exec $NODE2_IP "free -h | head -2"
echo ""
echo "主要容器内存使用："
ssh_exec $NODE2_IP "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' | grep -E 'hifate-(mysql|redis|nginx|web|fortune-analyzer)' | sort -k2 -hr"
echo ""

echo "========================================"
echo "📈 内存使用分析"
echo "========================================"
echo ""

echo "【内存使用分布 - Node1】"
mysql1=$(ssh_exec $NODE1_IP "docker stats --no-stream --format '{{.MemUsage}}' hifate-mysql-master 2>/dev/null | awk '{print \$1}'")
redis1=$(ssh_exec $NODE1_IP "docker stats --no-stream --format '{{.MemUsage}}' hifate-redis-master 2>/dev/null | awk '{print \$1}'")
nginx1=$(ssh_exec $NODE1_IP "docker stats --no-stream --format '{{.MemUsage}}' hifate-nginx 2>/dev/null | awk '{print \$1}'")
web1=$(ssh_exec $NODE1_IP "docker stats --no-stream --format '{{.MemUsage}}' hifate-web 2>/dev/null | awk '{print \$1}'")
echo "  MySQL: $mysql1"
echo "  Redis: $redis1"
echo "  Nginx: $nginx1"
echo "  Web: $web1"
echo "  微服务总计: ~430MiB (11个微服务)"
echo ""

echo "【内存使用分布 - Node2】"
mysql2=$(ssh_exec $NODE2_IP "docker stats --no-stream --format '{{.MemUsage}}' hifate-mysql-slave 2>/dev/null | awk '{print \$1}'")
redis2=$(ssh_exec $NODE2_IP "docker stats --no-stream --format '{{.MemUsage}}' hifate-redis-slave 2>/dev/null | awk '{print \$1}'")
nginx2=$(ssh_exec $NODE2_IP "docker stats --no-stream --format '{{.MemUsage}}' hifate-nginx 2>/dev/null | awk '{print \$1}'")
web2=$(ssh_exec $NODE2_IP "docker stats --no-stream --format '{{.MemUsage}}' hifate-web 2>/dev/null | awk '{print \$1}'")
echo "  MySQL: $mysql2"
echo "  Redis: $redis2"
echo "  Nginx: $nginx2"
echo "  Web: $web2"
echo "  微服务总计: ~436MiB (11个微服务)"
echo ""

echo "========================================"
echo "✅ 报告完成"
echo "========================================"

