#!/bin/bash
# 监控双机内存使用情况并分析
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
echo "📊 双机内存使用情况详细报告"
echo "========================================"
echo ""

# Node1报告
echo "【Node1 - $NODE1_IP】"
echo "========================================"
echo "系统内存："
ssh_exec $NODE1_IP "free -h"
echo ""
echo "容器内存使用（按使用量排序）："
ssh_exec $NODE1_IP "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | \
    grep hifate | sort -k3 -rn | \
    awk 'BEGIN {print \"容器名称\t内存使用\t内存占比\"} {print \$1 \"\t\" \$2 \"\t\" \$3}'"
echo ""

# Node2报告
echo "【Node2 - $NODE2_IP】"
echo "========================================"
echo "系统内存："
ssh_exec $NODE2_IP "free -h"
echo ""
echo "容器内存使用（按使用量排序）："
ssh_exec $NODE2_IP "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | \
    grep hifate | sort -k3 -rn | \
    awk 'BEGIN {print \"容器名称\t内存使用\t内存占比\"} {print \$1 \"\t\" \$2 \"\t\" \$3}'"
echo ""

# 内存使用汇总
echo "========================================"
echo "📈 内存使用汇总分析"
echo "========================================"
echo ""

echo "【Node1 内存占用TOP5】"
ssh_exec $NODE1_IP "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' | \
    grep hifate | sort -k2 -hr | head -5 | \
    awk '{mem=\$2; gsub(/MiB|GiB/, \"\", mem); if(mem ~ /[0-9]+\.[0-9]+/) print \$1 \" - \" \$2}'"
echo ""

echo "【Node2 内存占用TOP5】"
ssh_exec $NODE2_IP "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' | \
    grep hifate | sort -k2 -hr | head -5 | \
    awk '{mem=\$2; gsub(/MiB|GiB/, \"\", mem); if(mem ~ /[0-9]+\.[0-9]+/) print \$1 \" - \" \$2}'"
echo ""

# 检查内存限制配置
echo "========================================"
echo "🔍 内存限制配置检查"
echo "========================================"
echo ""

echo "【Node1 容器内存限制】"
ssh_exec $NODE1_IP "for container in \$(docker ps --format '{{.Names}}' | grep hifate); do
    limit=\$(docker inspect \$container 2>/dev/null | grep -A 5 '\"Memory\"' | grep '\"Limit\"' | awk '{print \$2}' | tr -d ',')
    if [ ! -z \"\$limit\" ] && [ \"\$limit\" != \"0\" ]; then
        limit_gb=\$(echo \"scale=2; \$limit/1024/1024/1024\" | bc)
        echo \"\$container: \$limit_gb GB\"
    fi
done | sort -k2 -rn"
echo ""

echo "【Node2 容器内存限制】"
ssh_exec $NODE2_IP "for container in \$(docker ps --format '{{.Names}}' | grep hifate); do
    limit=\$(docker inspect \$container 2>/dev/null | grep -A 5 '\"Memory\"' | grep '\"Limit\"' | awk '{print \$2}' | tr -d ',')
    if [ ! -z \"\$limit\" ] && [ \"\$limit\" != \"0\" ]; then
        limit_gb=\$(echo \"scale=2; \$limit/1024/1024/1024\" | bc)
        echo \"\$container: \$limit_gb GB\"
    fi
done | sort -k2 -rn"
echo ""

echo "========================================"
echo "✅ 内存监控完成"
echo "========================================"

