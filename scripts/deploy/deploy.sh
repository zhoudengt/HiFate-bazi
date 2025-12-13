#!/bin/bash
# HiFate-bazi Docker 快速部署脚本
# 使用方法：./scripts/deploy.sh [production|development]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 环境类型（默认生产环境）
ENV_TYPE=${1:-production}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}HiFate-bazi Docker 部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "环境类型: ${YELLOW}${ENV_TYPE}${NC}"
echo -e "项目目录: ${PROJECT_DIR}"
echo ""

# 检查 Docker 和 Docker Compose
echo -e "${YELLOW}[1/7] 检查环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装，请先安装 Docker Compose${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker 和 Docker Compose 已安装${NC}"

# 检查 .env 文件
echo -e "${YELLOW}[2/7] 检查环境变量配置...${NC}"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠️  .env 文件不存在，从 env.template 创建...${NC}"
    if [ -f "$PROJECT_DIR/env.template" ]; then
        cp "$PROJECT_DIR/env.template" "$PROJECT_DIR/.env"
        chmod 600 "$PROJECT_DIR/.env"
        echo -e "${YELLOW}⚠️  请编辑 .env 文件，设置正确的配置值${NC}"
        echo -e "${YELLOW}⚠️  按 Enter 继续，或 Ctrl+C 取消...${NC}"
        read
    else
        echo -e "${RED}❌ env.template 文件不存在${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ 环境变量配置已检查${NC}"

# 停止旧容器
echo -e "${YELLOW}[3/7] 停止旧容器...${NC}"
cd "$PROJECT_DIR"
if [ "$ENV_TYPE" == "production" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true
else
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml down 2>/dev/null || true
fi
echo -e "${GREEN}✅ 旧容器已停止${NC}"

# 拉取最新代码（如果在 Git 仓库中）
echo -e "${YELLOW}[4/7] 更新代码...${NC}"
if [ -d "$PROJECT_DIR/.git" ]; then
    git fetch origin
    if [ "$ENV_TYPE" == "production" ]; then
        git checkout master 2>/dev/null || true
        git pull origin master 2>/dev/null || true
    else
        git checkout develop 2>/dev/null || true
        git pull origin develop 2>/dev/null || true
    fi
    echo -e "${GREEN}✅ 代码已更新${NC}"
else
    echo -e "${YELLOW}⚠️  不是 Git 仓库，跳过代码更新${NC}"
fi

# 构建镜像
echo -e "${YELLOW}[5/7] 构建 Docker 镜像...${NC}"
if [ "$ENV_TYPE" == "production" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
else
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
fi
echo -e "${GREEN}✅ 镜像构建完成${NC}"

# 启动服务
echo -e "${YELLOW}[6/7] 启动服务...${NC}"
if [ "$ENV_TYPE" == "production" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
else
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
fi
echo -e "${GREEN}✅ 服务已启动${NC}"

# 等待服务启动
echo -e "${YELLOW}[7/7] 等待服务启动...${NC}"
sleep 15

# 健康检查
echo -e "${YELLOW}执行健康检查...${NC}"
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 健康检查通过！服务运行正常${NC}"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}⏳ 等待服务启动... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
            sleep 5
        else
            echo -e "${RED}❌ 健康检查失败，请查看日志：${NC}"
            if [ "$ENV_TYPE" == "production" ]; then
                docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=50
            else
                docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs --tail=50
            fi
            exit 1
        fi
    fi
done

# 显示服务状态
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "服务状态："
if [ "$ENV_TYPE" == "production" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
else
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
fi
echo ""
echo -e "访问地址："
echo -e "  - 主服务: ${GREEN}http://localhost:8001${NC}"
echo -e "  - 算法公式: ${GREEN}http://localhost:8001/local_frontend/formula-analysis.html${NC}"
echo -e "  - 运势分析: ${GREEN}http://localhost:8001/local_frontend/fortune.html${NC}"
echo ""
echo -e "查看日志："
echo -e "  ${YELLOW}docker-compose logs -f${NC}"
echo ""

