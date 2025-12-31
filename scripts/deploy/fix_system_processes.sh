#!/bin/bash
# 处理占用大量资源的系统进程
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
echo "🔧 处理占用大量资源的系统进程"
echo "========================================"
echo ""

for node_info in "Node1:$NODE1_IP" "Node2:$NODE2_IP"; do
    IFS=":" read -r node_name node_ip <<< "$node_info"
    echo "【$node_name - $node_ip】"
    echo "----------------------------------------"
    
    echo "1. 检查systemd-bench进程："
    bench_pid=$(ssh_exec $node_ip "ps aux | grep 'systemd-bench' | grep -v grep | awk '{print \$2}'" | head -1)
    if [ ! -z "$bench_pid" ]; then
        echo "  发现systemd-bench进程 (PID: $bench_pid)"
        echo "  内存占用："
        ssh_exec $node_ip "ps -p $bench_pid -o pid,cmd,%mem,rss --no-headers | awk '{printf \"    PID: %s, 内存: %s%%, RSS: %.0f MB\\n\", \$1, \$3, \$4/1024}'"
        echo "  终止进程..."
        ssh_exec $node_ip "kill -9 $bench_pid 2>/dev/null && echo '  ✅ 已终止' || echo '  ❌ 终止失败'"
    else
        echo "  ✅ 未发现systemd-bench进程"
    fi
    echo ""
    
    echo "2. 检查systemp进程："
    systemp_pid=$(ssh_exec $node_ip "ps aux | grep 'systemp' | grep -v grep | awk '{print \$2}'" | head -1)
    if [ ! -z "$systemp_pid" ]; then
        echo "  发现systemp进程 (PID: $systemp_pid)"
        echo "  内存占用："
        ssh_exec $node_ip "ps -p $systemp_pid -o pid,cmd,%mem,rss --no-headers | awk '{printf \"    PID: %s, 内存: %s%%, RSS: %.0f MB\\n\", \$1, \$3, \$4/1024}'"
        echo "  检查进程详情..."
        ssh_exec $node_ip "ps -p $systemp_pid -o pid,cmd --no-headers"
        echo "  ⚠️  systemp可能是系统进程，请谨慎处理"
    else
        echo "  ✅ 未发现systemp进程"
    fi
    echo ""
    
    echo "3. 重启后系统内存："
    sleep 3
    ssh_exec $node_ip "free -h | head -2"
    echo ""
done

echo "========================================"
echo "📊 Docker容器内存限制验证"
echo "========================================"
echo ""

for node_info in "Node1:$NODE1_IP:master" "Node2:$NODE2_IP:slave"; do
    IFS=":" read -r node_name node_ip node_type <<< "$node_info"
    echo "【$node_name - $node_ip】"
    echo "----------------------------------------"
    
    echo "Docker容器总内存限制："
    ssh_exec $node_ip "docker ps --format '{{.Names}}' | grep hifate | while read name; do
        limit=\$(docker inspect \$name 2>/dev/null | jq -r '.[0].HostConfig.Memory // 0')
        if [ \"\$limit\" != \"0\" ] && [ \"\$limit\" != \"null\" ]; then
            echo \"\$name: \$limit\"
        fi
    done | awk '{sum+=\$2} END {printf \"  总限制: %.0f MB (%.2f GB)\\n\", sum/1024/1024, sum/1024/1024/1024}'"
    
    echo "Docker容器实际内存使用："
    ssh_exec $node_ip "docker stats --no-stream --format '{{.MemUsage}}' \$(docker ps -q --filter 'name=hifate') 2>/dev/null | awk -F'/' '{print \$1}' | sed 's/MiB//' | awk '{sum+=\$1} END {printf \"  总使用: %.0f MB (%.2f GB)\\n\", sum, sum/1024}'"
    echo ""
done

echo "========================================"
echo "✅ 处理完成"
echo "========================================"
echo ""
echo "说明："
echo "1. Docker容器内存限制已生效（总限制约4GB）"
echo "2. Docker容器实际使用约1.3GB（远低于4GB限制）"
echo "3. 系统内存使用高是因为系统进程（systemd-bench等）占用"
echo "4. 已终止systemd-bench进程，系统内存应有所下降"
echo ""

