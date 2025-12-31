#!/bin/bash
# 停止双机所有容器脚本
# 用途：特殊情况停止双机所有容器（包括数据库、Redis、Nginx等）
# 使用：bash deploy/scripts/stop_all_containers_dual_nodes.sh
#
# ⚠️ 警告：此操作会中断所有服务！

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"

# 项目目录
PROJECT_DIR="/opt/HiFate-bazi"
DOCKER_COMPOSE_DIR="$PROJECT_DIR/deploy/docker"

# SSH 密码（从环境变量或默认值读取）
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# SSH 执行函数（支持密码登录）
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    # 检查是否有 sshpass
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        # 如果没有 sshpass，尝试使用 expect（如果可用）
        if command -v expect &> /dev/null; then
            expect << EOF
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
expect {
    "password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    eof
}
EOF
        else
            # 如果都没有，尝试直接 SSH（可能需要手动输入密码或已配置密钥）
            ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
        fi
    fi
}

# 停止单个节点的所有容器
stop_node_containers() {
    local host=$1
    local node_name=$2
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}停止 $node_name ($host) 的所有容器${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # 检查 Docker 是否运行
    if ! ssh_exec $host "docker ps > /dev/null 2>&1"; then
        echo -e "${YELLOW}⚠️  $node_name: Docker 未运行或无法访问${NC}"
        return 1
    fi
    
    # 查看当前运行的容器
    echo -e "${BLUE}📋 $node_name: 当前运行的容器：${NC}"
    ssh_exec $host "cd $DOCKER_COMPOSE_DIR && docker-compose -f docker-compose.prod.yml ps 2>/dev/null || docker ps --filter 'name=hifate-' --format 'table {{.Names}}\t{{.Status}}'"
    
    # 停止所有容器（使用 docker-compose down）
    echo -e "${YELLOW}🛑 $node_name: 正在停止所有容器...${NC}"
    
    # 尝试使用 docker-compose down（推荐方式）
    if ssh_exec $host "cd $DOCKER_COMPOSE_DIR && [ -f docker-compose.prod.yml ]"; then
        # 根据节点选择对应的配置文件
        if [ "$node_name" == "Node1" ]; then
            ssh_exec $host "cd $DOCKER_COMPOSE_DIR && \
                source $PROJECT_DIR/.env 2>/dev/null || true && \
                docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml --env-file $PROJECT_DIR/.env down 2>&1 || \
                docker-compose -f docker-compose.prod.yml --env-file $PROJECT_DIR/.env down 2>&1 || \
                docker-compose -f docker-compose.prod.yml down 2>&1"
        else
            ssh_exec $host "cd $DOCKER_COMPOSE_DIR && \
                source $PROJECT_DIR/.env 2>/dev/null || true && \
                docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml --env-file $PROJECT_DIR/.env down 2>&1 || \
                docker-compose -f docker-compose.prod.yml --env-file $PROJECT_DIR/.env down 2>&1 || \
                docker-compose -f docker-compose.prod.yml down 2>&1"
        fi
    else
        # 如果 docker-compose 文件不存在，直接停止所有 hifate 容器
        echo -e "${YELLOW}⚠️  docker-compose 文件不存在，直接停止所有 hifate 容器...${NC}"
        ssh_exec $host "docker ps --filter 'name=hifate-' --format '{{.Names}}' | xargs -r docker stop 2>/dev/null || true"
        ssh_exec $host "docker ps -a --filter 'name=hifate-' --format '{{.Names}}' | xargs -r docker rm -f 2>/dev/null || true"
    fi
    
    # 验证容器是否已停止
    echo -e "${BLUE}🔍 $node_name: 验证容器状态...${NC}"
    local running_containers=$(ssh_exec $host "docker ps --filter 'name=hifate-' --format '{{.Names}}' 2>/dev/null | wc -l" || echo "0")
    
    if [ "$running_containers" -eq 0 ] || [ -z "$running_containers" ]; then
        echo -e "${GREEN}✅ $node_name: 所有容器已停止${NC}"
    else
        echo -e "${YELLOW}⚠️  $node_name: 仍有 $running_containers 个容器在运行${NC}"
        echo -e "${YELLOW}   正在强制停止...${NC}"
        ssh_exec $host "docker ps --filter 'name=hifate-' --format '{{.Names}}' | xargs -r docker stop -t 5 2>/dev/null || true"
        ssh_exec $host "docker ps -a --filter 'name=hifate-' --format '{{.Names}}' | xargs -r docker rm -f 2>/dev/null || true"
    fi
    
    # 最终验证
    local final_count=$(ssh_exec $host "docker ps --filter 'name=hifate-' --format '{{.Names}}' 2>/dev/null | wc -l" || echo "0")
    if [ "$final_count" -eq 0 ] || [ -z "$final_count" ]; then
        echo -e "${GREEN}✅ $node_name: 所有容器已完全停止${NC}"
        return 0
    else
        echo -e "${RED}❌ $node_name: 仍有 $final_count 个容器在运行，请手动检查${NC}"
        return 1
    fi
}

# 主函数
main() {
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}⚠️  停止双机所有容器${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}此操作将停止以下所有容器：${NC}"
    echo -e "  - Nginx (hifate-nginx)"
    echo -e "  - Web 服务 (hifate-web)"
    echo -e "  - MySQL (hifate-mysql)"
    echo -e "  - Redis (hifate-redis)"
    echo -e "  - 所有微服务容器 (hifate-bazi-*, hifate-rule-service, etc.)"
    echo ""
    echo -e "${YELLOW}影响范围：${NC}"
    echo -e "  - Node1: $NODE1_PUBLIC_IP"
    echo -e "  - Node2: $NODE2_PUBLIC_IP"
    echo ""
    
    # 倒计时确认
    echo -e "${YELLOW}5秒后开始停止... (按 Ctrl+C 取消)${NC}"
    sleep 5
    
    # 停止 Node1
    echo ""
    stop_node_containers $NODE1_PUBLIC_IP "Node1"
    local node1_result=$?
    
    # 停止 Node2
    echo ""
    stop_node_containers $NODE2_PUBLIC_IP "Node2"
    local node2_result=$?
    
    # 总结
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}停止操作完成${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if [ $node1_result -eq 0 ] && [ $node2_result -eq 0 ]; then
        echo -e "${GREEN}✅ 双机所有容器已成功停止${NC}"
        echo ""
        echo -e "${YELLOW}📝 后续操作：${NC}"
        echo -e "  1. 如需重新启动，运行："
        echo -e "     bash deploy/scripts/start_all_containers_dual_nodes.sh"
        echo -e "  2. 或使用增量部署脚本："
        echo -e "     bash deploy/scripts/incremental_deploy_production.sh"
        exit 0
    else
        echo -e "${RED}❌ 部分节点停止失败，请检查日志${NC}"
        exit 1
    fi
}

# 执行主函数
main

