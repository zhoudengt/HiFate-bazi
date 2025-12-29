#!/bin/bash
# 应用4GB总内存限制到所有后端容器
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
echo "🔧 应用4GB总内存限制（后端容器）"
echo "========================================"
echo ""
echo "内存分配方案："
echo "  - MySQL: 1GB"
echo "  - Redis: 300MB"
echo "  - Nginx: 80MB"
echo "  - 11个微服务: 每个240MB = 2.64GB"
echo "  - 总计: 4.02GB"
echo ""

# Node1: 应用内存限制
echo "🔧 Node1: 应用内存限制..."
ssh_exec $NODE1_IP "
    docker update --memory=1g --memory-swap=1g --memory-reservation=600m hifate-mysql-master
    docker update --memory=300m --memory-swap=300m --memory-reservation=180m hifate-redis-master
    docker update --memory=80m --memory-swap=80m --memory-reservation=50m hifate-nginx
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-bazi-core
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-bazi-fortune
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-bazi-analyzer
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-rule-service
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-fortune-analyzer
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-payment-service
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-fortune-rule
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-intent-service
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-prompt-optimizer
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-desk-fengshui
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-auth-service
    echo '✅ Node1 内存限制已应用'
"

# Node2: 应用内存限制
echo "🔧 Node2: 应用内存限制..."
ssh_exec $NODE2_IP "
    docker update --memory=1g --memory-swap=1g --memory-reservation=600m hifate-mysql-slave
    docker update --memory=300m --memory-swap=300m --memory-reservation=180m hifate-redis-slave
    docker update --memory=80m --memory-swap=80m --memory-reservation=50m hifate-nginx
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-bazi-core
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-bazi-fortune
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-bazi-analyzer
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-rule-service
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-fortune-analyzer
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-payment-service
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-fortune-rule
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-intent-service
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-prompt-optimizer
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-desk-fengshui
    docker update --memory=240m --memory-swap=240m --memory-reservation=150m hifate-auth-service
    echo '✅ Node2 内存限制已应用'
"

echo ""
echo "⏳ 等待5秒让配置生效..."
sleep 5

echo ""
echo "========================================"
echo "📊 验证内存限制"
echo "========================================"
echo ""

echo "【Node1 容器内存限制】"
ssh_exec $NODE1_IP "for container in mysql redis nginx bazi-core bazi-fortune bazi-analyzer rule-service fortune-analyzer payment-service fortune-rule intent-service prompt-optimizer desk-fengshui auth-service; do
    full_name=\"hifate-\$container\"
    if [ \"\$container\" = \"mysql\" ]; then
        full_name=\"hifate-mysql-master\"
    elif [ \"\$container\" = \"redis\" ]; then
        full_name=\"hifate-redis-master\"
    fi
    limit=\$(docker inspect \$full_name 2>/dev/null | grep -A 5 '\"Memory\"' | grep '\"Limit\"' | awk '{print \$2}' | tr -d ',')
    if [ ! -z \"\$limit\" ] && [ \"\$limit\" != \"0\" ]; then
        limit_mb=\$(echo \"scale=0; \$limit/1024/1024\" | bc)
        echo \"  \$full_name: \$limit_mb MB\"
    fi
done"
echo ""

echo "【Node2 容器内存限制】"
ssh_exec $NODE2_IP "for container in mysql redis nginx bazi-core bazi-fortune bazi-analyzer rule-service fortune-analyzer payment-service fortune-rule intent-service prompt-optimizer desk-fengshui auth-service; do
    full_name=\"hifate-\$container\"
    if [ \"\$container\" = \"mysql\" ]; then
        full_name=\"hifate-mysql-slave\"
    elif [ \"\$container\" = \"redis\" ]; then
        full_name=\"hifate-redis-slave\"
    fi
    limit=\$(docker inspect \$full_name 2>/dev/null | grep -A 5 '\"Memory\"' | grep '\"Limit\"' | awk '{print \$2}' | tr -d ',')
    if [ ! -z \"\$limit\" ] && [ \"\$limit\" != \"0\" ]; then
        limit_mb=\$(echo \"scale=0; \$limit/1024/1024\" | bc)
        echo \"  \$full_name: \$limit_mb MB\"
    fi
done"
echo ""

echo "【总内存限制计算】"
echo "  MySQL: 1024 MB"
echo "  Redis: 300 MB"
echo "  Nginx: 80 MB"
echo "  11个微服务: 240 MB × 11 = 2640 MB"
echo "  ---------------------------------"
echo "  总计: 4044 MB ≈ 4 GB"
echo ""

echo "========================================"
echo "✅ 4GB内存限制配置应用完成"
echo "========================================"

