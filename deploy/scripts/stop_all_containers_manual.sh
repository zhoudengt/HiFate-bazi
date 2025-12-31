#!/bin/bash
# 手动停止所有容器脚本（在服务器上直接执行）
# 用途：在服务器上直接执行，停止所有容器
# 使用：在服务器上执行 bash stop_all_containers_manual.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="/opt/HiFate-bazi"
DOCKER_COMPOSE_DIR="$PROJECT_DIR/deploy/docker"

# 检测当前节点
detect_node() {
    local hostname=$(hostname)
    local ip=$(hostname -I | awk '{print $1}')
    
    if [[ "$ip" == "172.18.121.222" ]] || [[ "$hostname" == *"node1"* ]]; then
        echo "node1"
    elif [[ "$ip" == "172.18.121.223" ]] || [[ "$hostname" == *"node2"* ]]; then
        echo "node2"
    else
        echo "unknown"
    fi
}

# 停止所有容器
stop_all_containers() {
    local node=$(detect_node)
    
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}⚠️  停止所有容器${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}当前节点：$node${NC}"
    echo ""
    
    # 检查 Docker 是否运行
    if ! docker ps > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker 未运行或无法访问${NC}"
        exit 1
    fi
    
    # 查看当前运行的容器
    echo -e "${BLUE}📋 当前运行的容器：${NC}"
    docker ps --filter 'name=hifate-' --format 'table {{.Names}}\t{{.Status}}' || true
    echo ""
    
    # 停止所有容器
    echo -e "${YELLOW}🛑 正在停止所有容器...${NC}"
    
    # 方法1：使用 docker-compose down（推荐）
    if [ -f "$DOCKER_COMPOSE_DIR/docker-compose.prod.yml" ]; then
        cd $DOCKER_COMPOSE_DIR
        
        # 加载环境变量
        if [ -f "$PROJECT_DIR/.env" ]; then
            source $PROJECT_DIR/.env
        fi
        
        # 根据节点选择配置文件
        if [ "$node" == "node1" ] && [ -f "docker-compose.node1.yml" ]; then
            echo -e "${BLUE}使用 Node1 配置停止容器...${NC}"
            docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml --env-file $PROJECT_DIR/.env down 2>&1 || \
            docker-compose -f docker-compose.prod.yml --env-file $PROJECT_DIR/.env down 2>&1 || \
            docker-compose -f docker-compose.prod.yml down 2>&1
        elif [ "$node" == "node2" ] && [ -f "docker-compose.node2.yml" ]; then
            echo -e "${BLUE}使用 Node2 配置停止容器...${NC}"
            docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml --env-file $PROJECT_DIR/.env down 2>&1 || \
            docker-compose -f docker-compose.prod.yml --env-file $PROJECT_DIR/.env down 2>&1 || \
            docker-compose -f docker-compose.prod.yml down 2>&1
        else
            echo -e "${BLUE}使用默认配置停止容器...${NC}"
            docker-compose -f docker-compose.prod.yml --env-file $PROJECT_DIR/.env down 2>&1 || \
            docker-compose -f docker-compose.prod.yml down 2>&1
        fi
    else
        # 方法2：直接停止所有 hifate 容器
        echo -e "${YELLOW}⚠️  docker-compose 文件不存在，直接停止所有 hifate 容器...${NC}"
        docker ps --filter 'name=hifate-' --format '{{.Names}}' | xargs -r docker stop 2>/dev/null || true
        docker ps -a --filter 'name=hifate-' --format '{{.Names}}' | xargs -r docker rm -f 2>/dev/null || true
    fi
    
    # 验证容器是否已停止
    echo ""
    echo -e "${BLUE}🔍 验证容器状态...${NC}"
    local running_containers=$(docker ps --filter 'name=hifate-' --format '{{.Names}}' 2>/dev/null | wc -l || echo "0")
    
    if [ "$running_containers" -eq 0 ] || [ -z "$running_containers" ]; then
        echo -e "${GREEN}✅ 所有容器已停止${NC}"
    else
        echo -e "${YELLOW}⚠️  仍有 $running_containers 个容器在运行，正在强制停止...${NC}"
        docker ps --filter 'name=hifate-' --format '{{.Names}}' | xargs -r docker stop -t 5 2>/dev/null || true
        docker ps -a --filter 'name=hifate-' --format '{{.Names}}' | xargs -r docker rm -f 2>/dev/null || true
    fi
    
    # 最终验证
    local final_count=$(docker ps --filter 'name=hifate-' --format '{{.Names}}' 2>/dev/null | wc -l || echo "0")
    if [ "$final_count" -eq 0 ] || [ -z "$final_count" ]; then
        echo -e "${GREEN}✅ 所有容器已完全停止${NC}"
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${GREEN}停止操作完成${NC}"
        echo -e "${BLUE}========================================${NC}"
        return 0
    else
        echo -e "${RED}❌ 仍有 $final_count 个容器在运行：${NC}"
        docker ps --filter 'name=hifate-' --format 'table {{.Names}}\t{{.Status}}'
        return 1
    fi
}

# 执行停止
stop_all_containers

