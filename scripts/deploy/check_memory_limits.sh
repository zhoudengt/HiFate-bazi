#!/bin/bash
# 检查Docker容器内存限制是否真的生效
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
echo "🔍 检查Docker容器内存限制是否生效"
echo "========================================"
echo ""

for node_info in "Node1:$NODE1_IP:master" "Node2:$NODE2_IP:slave"; do
    IFS=":" read -r node_name node_ip node_type <<< "$node_info"
    echo "【$node_name - $node_ip】"
    echo "----------------------------------------"
    
    echo "1. 系统内存："
    ssh_exec $node_ip "free -h | head -2"
    echo ""
    
    echo "2. Docker容器内存限制（通过docker inspect）："
    echo "MySQL:"
    mysql_name="hifate-mysql-$node_type"
    ssh_exec $node_ip "docker inspect $mysql_name 2>/dev/null | jq -r '.[0].HostConfig.Memory // \"未设置\"' | awk '{if(\$1==\"未设置\") print \"  未设置内存限制\"; else printf \"  %d MB (%.2f GB)\\n\", \$1/1024/1024, \$1/1024/1024/1024}'"
    
    echo "Redis:"
    redis_name="hifate-redis-$node_type"
    ssh_exec $node_ip "docker inspect $redis_name 2>/dev/null | jq -r '.[0].HostConfig.Memory // \"未设置\"' | awk '{if(\$1==\"未设置\") print \"  未设置内存限制\"; else printf \"  %d MB (%.2f GB)\\n\", \$1/1024/1024, \$1/1024/1024/1024}'"
    
    echo "微服务（示例：bazi-core）:"
    ssh_exec $node_ip "docker inspect hifate-bazi-core 2>/dev/null | jq -r '.[0].HostConfig.Memory // \"未设置\"' | awk '{if(\$1==\"未设置\") print \"  未设置内存限制\"; else printf \"  %d MB\\n\", \$1/1024/1024}'"
    echo ""
    
    echo "3. Docker容器实际内存使用："
    ssh_exec $node_ip "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | grep hifate | head -15"
    echo ""
    
    echo "4. 计算Docker容器总内存限制："
    ssh_exec $node_ip "echo '计算所有hifate容器的内存限制总和...' && \
        docker ps --format '{{.Names}}' | grep hifate | while read name; do
            limit=\$(docker inspect \$name 2>/dev/null | jq -r '.[0].HostConfig.Memory // 0')
            if [ \"\$limit\" != \"0\" ] && [ \"\$limit\" != \"null\" ]; then
                echo \"\$name: \$limit\"
            fi
        done | awk '{sum+=\$2} END {printf \"  总限制: %.0f MB (%.2f GB)\\n\", sum/1024/1024, sum/1024/1024/1024}'"
    echo ""
    
    echo "5. 系统进程内存占用（非Docker）："
    ssh_exec $node_ip "ps aux --sort=-%mem | head -6 | tail -5 | awk '{printf \"  %-20s %6s %10s\\n\", \$11, \$4\"%\", \$6/1024\"MB\"}'"
    echo ""
done

echo "========================================"
echo "📊 问题诊断"
echo "========================================"
echo ""
echo "如果内存限制未生效，可能的原因："
echo "1. docker update 命令可能没有正确应用限制"
echo "2. 需要重新创建容器（而不是重启）才能应用限制"
echo "3. 系统进程（如systemd-bench）占用了大量内存"
echo ""

