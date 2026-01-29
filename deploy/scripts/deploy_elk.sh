#!/bin/bash
# ELK 日志栈部署脚本 - 生产环境
# 用途：部署/更新 ELK 日志栈（Elasticsearch + Logstash + Kibana + Filebeat）
# 使用：bash deploy/scripts/deploy_elk.sh [start|stop|restart|status|logs]
#
# 资源限制（不与主应用竞争）：
#   - Elasticsearch: 1 CPU + 3G 内存
#   - Logstash: 0.5 CPU + 512M 内存
#   - Kibana: 0.5 CPU + 512M 内存
#   - Filebeat: 0.2 CPU + 128M 内存
#   - 总计：2.2 CPU + 4.2G 内存

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
PROJECT_DIR="${PROJECT_DIR:-/opt/HiFate-bazi}"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
NODE2_PRIVATE_IP="172.18.121.223"

# 默认只在 Node1 部署 ELK（集中式日志）
DEPLOY_NODE="${DEPLOY_NODE:-node1}"

# SSH 执行函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 root@$host "$cmd"
    fi
}

# 通过 Node1 连接 Node2
ssh_exec_node2_via_node1() {
    local cmd="$@"
    ssh_exec $NODE1_PUBLIC_IP "sshpass -p '$SSH_PASSWORD' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 root@$NODE2_PRIVATE_IP '$cmd'"
}

# 显示使用帮助
show_usage() {
    echo "使用方法: $0 [命令] [选项]"
    echo ""
    echo "命令："
    echo "  start     启动 ELK 日志栈"
    echo "  stop      停止 ELK 日志栈"
    echo "  restart   重启 ELK 日志栈"
    echo "  status    查看 ELK 服务状态"
    echo "  logs      查看 ELK 日志"
    echo "  health    检查 ELK 健康状态"
    echo ""
    echo "选项："
    echo "  --node=node1|node2|all  指定部署节点（默认 node1）"
    echo ""
    echo "示例："
    echo "  $0 start                # 在 Node1 启动 ELK"
    echo "  $0 status --node=all    # 查看所有节点 ELK 状态"
    echo "  $0 logs                 # 查看 Node1 ELK 日志"
}

# 启动 ELK
start_elk() {
    local node=$1
    local ip=""
    
    if [ "$node" = "node1" ]; then
        ip=$NODE1_PUBLIC_IP
    else
        ip=$NODE2_PUBLIC_IP
    fi
    
    echo -e "${BLUE}🚀 启动 $node ELK 日志栈...${NC}"
    
    # 确保网络存在
    ssh_exec $ip "docker network create hifate-network 2>/dev/null || true"
    
    # 确保 ELK 配置目录存在
    ssh_exec $ip "cd $PROJECT_DIR && mkdir -p elk/logstash/pipeline elk/filebeat logs"
    
    # 启动 ELK 服务（与主应用一起）
    ssh_exec $ip "cd $PROJECT_DIR && docker-compose -f docker-compose.yml -f docker-compose.elk.yml up -d elasticsearch logstash kibana filebeat"
    
    # 等待 Elasticsearch 启动
    echo "⏳ 等待 Elasticsearch 启动..."
    local max_wait=120
    local wait_count=0
    while [ $wait_count -lt $max_wait ]; do
        if ssh_exec $ip "curl -s http://localhost:9200/_cluster/health 2>/dev/null | grep -q 'green\|yellow'"; then
            echo -e "${GREEN}✅ Elasticsearch 已启动${NC}"
            break
        fi
        sleep 5
        wait_count=$((wait_count + 5))
        echo "⏳ 等待中... ($wait_count/$max_wait 秒)"
    done
    
    if [ $wait_count -ge $max_wait ]; then
        echo -e "${YELLOW}⚠️ Elasticsearch 启动超时，请手动检查${NC}"
    fi
    
    echo -e "${GREEN}✅ $node ELK 日志栈启动完成${NC}"
}

# 停止 ELK
stop_elk() {
    local node=$1
    local ip=""
    
    if [ "$node" = "node1" ]; then
        ip=$NODE1_PUBLIC_IP
    else
        ip=$NODE2_PUBLIC_IP
    fi
    
    echo -e "${BLUE}🛑 停止 $node ELK 日志栈...${NC}"
    
    ssh_exec $ip "cd $PROJECT_DIR && docker-compose -f docker-compose.elk.yml down 2>/dev/null || true"
    
    echo -e "${GREEN}✅ $node ELK 日志栈已停止${NC}"
}

# 查看 ELK 状态
status_elk() {
    local node=$1
    local ip=""
    
    if [ "$node" = "node1" ]; then
        ip=$NODE1_PUBLIC_IP
    else
        ip=$NODE2_PUBLIC_IP
    fi
    
    echo -e "${BLUE}📊 $node ELK 服务状态${NC}"
    echo "----------------------------------------"
    
    ssh_exec $ip "docker ps --filter 'name=hifate-elasticsearch' --filter 'name=hifate-logstash' --filter 'name=hifate-kibana' --filter 'name=hifate-filebeat' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    
    echo ""
}

# 查看 ELK 日志
logs_elk() {
    local node=$1
    local ip=""
    local service="${2:-elasticsearch}"
    
    if [ "$node" = "node1" ]; then
        ip=$NODE1_PUBLIC_IP
    else
        ip=$NODE2_PUBLIC_IP
    fi
    
    echo -e "${BLUE}📋 $node ELK 日志 ($service)${NC}"
    echo "----------------------------------------"
    
    ssh_exec $ip "docker logs --tail 50 hifate-$service 2>&1"
}

# 健康检查
health_elk() {
    local node=$1
    local ip=""
    
    if [ "$node" = "node1" ]; then
        ip=$NODE1_PUBLIC_IP
    else
        ip=$NODE2_PUBLIC_IP
    fi
    
    echo -e "${BLUE}🏥 $node ELK 健康检查${NC}"
    echo "----------------------------------------"
    
    # Elasticsearch 健康检查
    echo -n "Elasticsearch: "
    ES_HEALTH=$(ssh_exec $ip "curl -s http://localhost:9200/_cluster/health 2>/dev/null" || echo "{}")
    if echo "$ES_HEALTH" | grep -q '"status":"green"'; then
        echo -e "${GREEN}健康 (green)${NC}"
    elif echo "$ES_HEALTH" | grep -q '"status":"yellow"'; then
        echo -e "${YELLOW}警告 (yellow)${NC}"
    else
        echo -e "${RED}异常${NC}"
    fi
    
    # Kibana 健康检查
    echo -n "Kibana: "
    if ssh_exec $ip "curl -s http://localhost:5601/api/status 2>/dev/null | grep -q 'available'"; then
        echo -e "${GREEN}健康${NC}"
    else
        echo -e "${RED}异常${NC}"
    fi
    
    # Logstash 健康检查（检查是否在监听）
    echo -n "Logstash: "
    if ssh_exec $ip "docker exec hifate-logstash curl -s http://localhost:9600/_node/stats 2>/dev/null | grep -q 'events'"; then
        echo -e "${GREEN}健康${NC}"
    else
        echo -e "${YELLOW}无法检查（正常运行中）${NC}"
    fi
    
    # Filebeat 健康检查
    echo -n "Filebeat: "
    if ssh_exec $ip "docker ps --filter 'name=hifate-filebeat' --filter 'status=running' -q" | grep -q .; then
        echo -e "${GREEN}运行中${NC}"
    else
        echo -e "${RED}未运行${NC}"
    fi
    
    echo ""
    
    # 显示索引信息
    echo "Elasticsearch 索引："
    ssh_exec $ip "curl -s 'http://localhost:9200/_cat/indices/stream-flow-*?v&h=index,docs.count,store.size' 2>/dev/null" || echo "  无索引数据"
    
    echo ""
}

# 解析命令行参数
COMMAND=""
DEPLOY_NODE="node1"

while [[ $# -gt 0 ]]; do
    case $1 in
        start|stop|restart|status|logs|health)
            COMMAND=$1
            shift
            ;;
        --node=*)
            DEPLOY_NODE="${1#*=}"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# 默认命令
if [ -z "$COMMAND" ]; then
    show_usage
    exit 0
fi

# 执行命令
echo "========================================"
echo -e "${BLUE}ELK 日志栈管理${NC}"
echo "========================================"
echo "命令: $COMMAND"
echo "节点: $DEPLOY_NODE"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

case $COMMAND in
    start)
        if [ "$DEPLOY_NODE" = "all" ]; then
            start_elk "node1"
            start_elk "node2"
        else
            start_elk "$DEPLOY_NODE"
        fi
        ;;
    stop)
        if [ "$DEPLOY_NODE" = "all" ]; then
            stop_elk "node1"
            stop_elk "node2"
        else
            stop_elk "$DEPLOY_NODE"
        fi
        ;;
    restart)
        if [ "$DEPLOY_NODE" = "all" ]; then
            stop_elk "node1"
            stop_elk "node2"
            start_elk "node1"
            start_elk "node2"
        else
            stop_elk "$DEPLOY_NODE"
            start_elk "$DEPLOY_NODE"
        fi
        ;;
    status)
        if [ "$DEPLOY_NODE" = "all" ]; then
            status_elk "node1"
            status_elk "node2"
        else
            status_elk "$DEPLOY_NODE"
        fi
        ;;
    logs)
        logs_elk "$DEPLOY_NODE" "$2"
        ;;
    health)
        if [ "$DEPLOY_NODE" = "all" ]; then
            health_elk "node1"
            health_elk "node2"
        else
            health_elk "$DEPLOY_NODE"
        fi
        ;;
esac

echo ""
echo -e "${GREEN}✅ 完成${NC}"
