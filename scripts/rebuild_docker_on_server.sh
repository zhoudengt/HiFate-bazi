#!/bin/bash
# 在服务器上重新构建 Docker 镜像的脚本
# 用途：当 requirements.txt 变更时，在服务器上重新构建镜像
# 使用：在服务器上执行此脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/opt/HiFate-bazi"

echo -e "${YELLOW}=== 重新构建 Docker 镜像 ===${NC}"
echo ""

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# 拉取最新代码
echo -e "${YELLOW}[1/4] 拉取最新代码...${NC}"
git fetch gitee 2>/dev/null || git fetch origin 2>/dev/null || true
git pull gitee master 2>/dev/null || git pull origin master 2>/dev/null || {
    echo -e "${YELLOW}⚠️  代码拉取失败，继续使用当前代码${NC}"
}
echo -e "${GREEN}✅ 代码已更新${NC}"
echo ""

# 停止旧容器
echo -e "${YELLOW}[2/4] 停止旧容器...${NC}"
docker-compose -f deploy/docker/docker-compose.prod.yml -f deploy/docker/docker-compose.node1.yml down 2>/dev/null || true
echo -e "${GREEN}✅ 旧容器已停止${NC}"
echo ""

# 重新构建镜像
echo -e "${YELLOW}[3/4] 重新构建 Docker 镜像（这可能需要几分钟）...${NC}"
docker build --platform linux/amd64 -t hifate-bazi:latest . || {
    echo -e "${RED}❌ 镜像构建失败${NC}"
    exit 1
}
echo -e "${GREEN}✅ 镜像构建完成${NC}"
echo ""

# 验证 stripe 库是否已安装
echo -e "${YELLOW}[4/4] 验证依赖安装...${NC}"
docker run --rm hifate-bazi:latest python -c "import stripe; print('✅ stripe:', stripe.__version__)" || {
    echo -e "${RED}❌ stripe 库未安装${NC}"
    exit 1
}
echo -e "${GREEN}✅ 依赖验证通过${NC}"
echo ""

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
docker-compose -f deploy/docker/docker-compose.prod.yml -f deploy/docker/docker-compose.node1.yml up -d
echo -e "${GREEN}✅ 服务已启动${NC}"
echo ""

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 20

# 健康检查
echo -e "${YELLOW}执行健康检查...${NC}"
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 健康检查通过${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 3
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo -e "${YELLOW}等待服务启动... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ 健康检查超时${NC}"
    echo "请检查服务日志: docker logs hifate-web"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
