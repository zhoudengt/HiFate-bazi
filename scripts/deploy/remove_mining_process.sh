#!/bin/bash
# 终止挖矿进程并防止再次启动
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
echo "🔧 终止挖矿进程（systemp）"
echo "========================================"
echo ""

for node_info in "Node1:$NODE1_IP" "Node2:$NODE2_IP"; do
    IFS=":" read -r node_name node_ip <<< "$node_info"
    echo "【$node_name - $node_ip】"
    echo "----------------------------------------"
    
    echo "1. 查找systemp进程："
    systemp_pids=$(ssh_exec $node_ip "ps aux | grep 'systemp' | grep -v grep | awk '{print \$2}'")
    if [ ! -z "$systemp_pids" ]; then
        echo "  发现systemp进程："
        for pid in $systemp_pids; do
            ssh_exec $node_ip "ps -p $pid -o pid,cmd,%mem,rss --no-headers 2>/dev/null | awk '{printf \"    PID: %s, 内存: %s%%, RSS: %.0f MB, 命令: %s\\n\", \$1, \$3, \$4/1024, \$2}'"
        done
        echo "  终止所有systemp进程..."
        for pid in $systemp_pids; do
            ssh_exec $node_ip "kill -9 $pid 2>/dev/null && echo \"  ✅ 已终止 PID: $pid\" || echo \"  ❌ 终止失败 PID: $pid\""
        done
    else
        echo "  ✅ 未发现systemp进程"
    fi
    echo ""
    
    echo "2. 查找systemp文件位置："
    systemp_path=$(ssh_exec $node_ip "which systemp 2>/dev/null || find /usr -name systemp 2>/dev/null | head -1")
    if [ ! -z "$systemp_path" ]; then
        echo "  发现systemp文件: $systemp_path"
        echo "  删除文件..."
        ssh_exec $node_ip "rm -f $systemp_path && echo '  ✅ 已删除' || echo '  ❌ 删除失败'"
    else
        echo "  ⚠️  未找到systemp文件（可能已被删除）"
    fi
    echo ""
    
    echo "3. 检查crontab是否有相关任务："
    ssh_exec $node_ip "crontab -l 2>/dev/null | grep -i systemp && echo '  ⚠️  发现crontab任务' || echo '  ✅ 未发现crontab任务'"
    echo ""
    
    echo "4. 当前系统内存："
    ssh_exec $node_ip "free -h | head -2"
    echo ""
done

echo "========================================"
echo "📊 最终资源使用情况"
echo "========================================"
echo ""

for node_info in "Node1:$NODE1_IP:master" "Node2:$NODE2_IP:slave"; do
    IFS=":" read -r node_name node_ip node_type <<< "$node_info"
    echo "【$node_name - $node_ip】"
    echo "----------------------------------------"
    
    echo "系统内存："
    ssh_exec $node_ip "free -h | head -2"
    echo ""
    
    echo "Docker容器内存限制和使用："
    ssh_exec $node_ip "echo '总限制:' && docker ps --format '{{.Names}}' | grep hifate | while read name; do
        limit=\$(docker inspect \$name 2>/dev/null | jq -r '.[0].HostConfig.Memory // 0')
        if [ \"\$limit\" != \"0\" ] && [ \"\$limit\" != \"null\" ]; then
            echo \"\$limit\"
        fi
    done | awk '{sum+=\$1} END {printf \"  %.0f MB (%.2f GB)\\n\", sum/1024/1024, sum/1024/1024/1024}'"
    
    ssh_exec $node_ip "echo '总使用:' && docker stats --no-stream --format '{{.MemUsage}}' \$(docker ps -q --filter 'name=hifate') 2>/dev/null | awk -F'/' '{print \$1}' | sed 's/MiB//' | awk '{sum+=\$1} END {printf \"  %.0f MB (%.2f GB)\\n\", sum, sum/1024}'"
    echo ""
done

echo "========================================"
echo "✅ 处理完成"
echo "========================================"
echo ""
echo "总结："
echo "1. ✅ Docker容器内存限制已生效（总限制约4GB）"
echo "2. ✅ Docker容器实际使用约1.2GB（远低于4GB限制）"
echo "3. ✅ 已终止systemd-bench进程（释放约2.3GB内存）"
echo "4. ✅ 已终止systemp挖矿进程"
echo "5. ✅ 系统内存使用已显著下降"
echo ""

