#!/bin/bash
# 分析服务器资源使用情况
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
echo "🔍 服务器资源使用情况分析"
echo "========================================"
echo ""

for node_info in "Node1:$NODE1_IP:master" "Node2:$NODE2_IP:slave"; do
    IFS=":" read -r node_name node_ip node_type <<< "$node_info"
    echo "【$node_name - $node_ip】"
    echo "----------------------------------------"
    
    echo "1. 系统内存详情："
    ssh_exec $node_ip "free -h"
    echo ""
    
    echo "2. 容器内存限制验证："
    mysql_name="hifate-mysql-$node_type"
    redis_name="hifate-redis-$node_type"
    ssh_exec $node_ip "echo 'MySQL ($mysql_name):' && docker inspect $mysql_name 2>/dev/null | grep -A 3 '\"Memory\"' | grep '\"Limit\"' | awk '{limit=\$2/1024/1024/1024; printf \"  %.2f GB\\n\", limit}' || echo '  未找到'"
    ssh_exec $node_ip "echo 'Redis ($redis_name):' && docker inspect $redis_name 2>/dev/null | grep -A 3 '\"Memory\"' | grep '\"Limit\"' | awk '{limit=\$2/1024/1024/1024; printf \"  %.2f GB\\n\", limit}' || echo '  未找到'"
    echo ""
    
    echo "3. 容器实际内存使用："
    ssh_exec $node_ip "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | grep hifate | head -10"
    echo ""
    
    echo "4. 系统进程内存占用TOP10："
    ssh_exec $node_ip "ps aux --sort=-%mem | head -11 | awk '{printf \"  %-20s %6s %6s\\n\", \$11, \$4\"%\", \$6/1024\"MB\"}'"
    echo ""
    
    echo "5. Docker容器总内存使用："
    ssh_exec $node_ip "docker stats --no-stream --format '{{.MemUsage}}' \$(docker ps -q) 2>/dev/null | awk -F'/' '{print \$1}' | sed 's/MiB//' | awk '{sum+=\$1} END {if(sum>0) printf \"  总使用: %.0f MiB (%.2f GB)\\n\", sum, sum/1024; else print \"  无法计算\"}'"
    echo ""
done

echo "========================================"
echo "📊 问题分析"
echo "========================================"
echo ""
echo "可能的原因："
echo "1. ❌ 内存限制只是上限，不会主动释放已使用的内存"
echo "2. ❌ MySQL和Redis配置优化需要重启容器才能生效"
echo "3. ⚠️  系统缓存(buff/cache)占用内存（这是正常的）"
echo "4. ⚠️  容器需要重启才能应用新的内存限制和配置优化"
echo ""
echo "解决方案："
echo "1. 重启MySQL和Redis容器以应用配置优化"
echo "2. 重启所有微服务容器以应用新的内存限制"
echo "3. 清理系统缓存（可选，系统会自动管理）"
echo ""
