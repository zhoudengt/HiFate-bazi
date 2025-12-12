#!/bin/bash
# ============================================
# HiFate 健康检查脚本
# ============================================
# 用途：监控双节点服务状态
# 使用：
#   手动执行：bash scripts/aliyun/health_check.sh
#   定时任务：*/5 * * * * /opt/HiFate-bazi/scripts/aliyun/health_check.sh >> /var/log/hifate-health.log 2>&1

set -e

# ============================================
# 配置
# ============================================
# 节点 IP（根据实际情况修改）
NODE1_IP="${NODE1_IP:-172.16.0.10}"
NODE2_IP="${NODE2_IP:-172.16.0.11}"

# 告警 Webhook（可选）
DINGTALK_WEBHOOK="${DINGTALK_WEBHOOK:-}"
WECOM_WEBHOOK="${WECOM_WEBHOOK:-}"

# 检查端口
WEB_PORT=8001
NGINX_PORT=80

# 超时时间（秒）
TIMEOUT=5

# ============================================
# 函数定义
# ============================================

# 检查单个服务
check_service() {
    local host=$1
    local port=$2
    local path=$3
    local timeout=$4
    
    if curl -sf --connect-timeout ${timeout} "http://${host}:${port}${path}" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 检查节点
check_node() {
    local node_name=$1
    local node_ip=$2
    local errors=""
    
    echo "检查 ${node_name} (${node_ip})..."
    
    # 检查 Web 服务
    if check_service ${node_ip} ${WEB_PORT} "/health" ${TIMEOUT}; then
        echo "  ✅ Web 服务正常"
    else
        errors="${errors}Web服务异常;"
        echo "  ❌ Web 服务异常"
    fi
    
    # 检查 Nginx（如果在同一节点）
    if check_service ${node_ip} ${NGINX_PORT} "/health" ${TIMEOUT}; then
        echo "  ✅ Nginx 正常"
    else
        # Nginx 可能在其他节点，不作为严重错误
        echo "  ⚠️ Nginx 不可访问（可能不在此节点）"
    fi
    
    if [ -n "$errors" ]; then
        echo "  📋 问题: ${errors}"
        return 1
    fi
    
    return 0
}

# 发送告警
send_alert() {
    local level=$1  # critical / warning / info
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[${timestamp}] [${level}] ${message}"
    
    # 钉钉告警
    if [ -n "$DINGTALK_WEBHOOK" ]; then
        curl -s -X POST "$DINGTALK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{
                \"msgtype\": \"markdown\",
                \"markdown\": {
                    \"title\": \"HiFate 监控告警\",
                    \"text\": \"### HiFate 监控告警\\n- **级别**: ${level}\\n- **时间**: ${timestamp}\\n- **内容**: ${message}\"
                }
            }" > /dev/null 2>&1 || true
    fi
    
    # 企业微信告警
    if [ -n "$WECOM_WEBHOOK" ]; then
        curl -s -X POST "$WECOM_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{
                \"msgtype\": \"markdown\",
                \"markdown\": {
                    \"content\": \"### HiFate 监控告警\\n> **级别**: ${level}\\n> **时间**: ${timestamp}\\n> **内容**: ${message}\"
                }
            }" > /dev/null 2>&1 || true
    fi
}

# ============================================
# 主流程
# ============================================

echo "========================================"
echo "🔍 HiFate 健康检查"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

node1_ok=true
node2_ok=true

# 检查 Node 1
if ! check_node "Node1" "${NODE1_IP}"; then
    node1_ok=false
fi

echo ""

# 检查 Node 2
if ! check_node "Node2" "${NODE2_IP}"; then
    node2_ok=false
fi

echo ""
echo "========================================"
echo "📊 检查结果"
echo "========================================"

# 判断整体状态并发送告警
if [ "$node1_ok" = false ] && [ "$node2_ok" = false ]; then
    echo "❌ 严重：双节点全部异常！"
    send_alert "critical" "严重警告：HiFate 双节点全部异常！Node1(${NODE1_IP}) 和 Node2(${NODE2_IP}) 均不可用，请立即检查！"
    exit 2
elif [ "$node1_ok" = false ]; then
    echo "⚠️ 警告：Node1 异常"
    send_alert "warning" "Node1(${NODE1_IP}) 服务异常，请检查。Node2 正常运行中。"
    exit 1
elif [ "$node2_ok" = false ]; then
    echo "⚠️ 警告：Node2 异常"
    send_alert "warning" "Node2(${NODE2_IP}) 服务异常，请检查。Node1 正常运行中。"
    exit 1
else
    echo "✅ 所有节点正常"
    exit 0
fi
