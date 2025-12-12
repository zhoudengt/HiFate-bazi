#!/bin/bash
# 健康检查脚本
# 用途：检查双节点服务状态
# 使用：bash health-check.sh
# 定时任务：*/5 * * * * /opt/HiFate-bazi/deploy/scripts/health-check.sh >> /var/log/hifate-health.log 2>&1

PROJECT_DIR="/opt/HiFate-bazi"
cd ${PROJECT_DIR}

# 加载环境变量
if [ -f .env ]; then
    source .env
fi

NODE1_IP="${NODE1_IP:-127.0.0.1}"
NODE2_IP="${NODE2_IP:-127.0.0.1}"
TIMEOUT=5

echo "========================================"
echo "HiFate 健康检查"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 检查服务
check_service() {
    local host=$1
    local port=$2
    local name=$3
    
    if curl -sf --connect-timeout ${TIMEOUT} "http://${host}:${port}/health" > /dev/null 2>&1; then
        echo "  [OK] ${name} (${host}:${port})"
        return 0
    else
        echo "  [FAIL] ${name} (${host}:${port})"
        return 1
    fi
}

# 检查 Node1
echo ""
echo "Node1 (${NODE1_IP}):"
node1_ok=true
check_service ${NODE1_IP} 8001 "Web服务" || node1_ok=false
check_service ${NODE1_IP} 80 "Nginx" || node1_ok=false

# 检查 Node2
echo ""
echo "Node2 (${NODE2_IP}):"
node2_ok=true
check_service ${NODE2_IP} 8001 "Web服务" || node2_ok=false
check_service ${NODE2_IP} 80 "Nginx" || node2_ok=false

# 本地容器状态
echo ""
echo "本地容器:"
docker ps --format "  {{.Names}}: {{.Status}}" | grep hifate || echo "  无 HiFate 容器运行"

# 结果汇总
echo ""
echo "========================================"
if [ "$node1_ok" = false ] && [ "$node2_ok" = false ]; then
    echo "严重: 双节点全部异常！"
    # 发送告警（如果配置了 webhook）
    if [ -n "$DINGTALK_WEBHOOK" ]; then
        curl -s -X POST "$DINGTALK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d '{"msgtype":"text","text":{"content":"HiFate 严重告警: 双节点全部异常！"}}' > /dev/null
    fi
    exit 2
elif [ "$node1_ok" = false ]; then
    echo "警告: Node1 异常"
    exit 1
elif [ "$node2_ok" = false ]; then
    echo "警告: Node2 异常"
    exit 1
else
    echo "正常: 双节点运行正常"
    exit 0
fi
