#!/bin/bash
# 重新构建 Docker 镜像并部署脚本
# 用途：当 requirements.txt 变更时，重新构建镜像并部署
# 使用：bash scripts/rebuild_and_deploy.sh

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
PROJECT_DIR="/opt/HiFate-bazi"

# SSH 密码（从环境变量读取）
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# SSH 执行函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    fi
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}重新构建 Docker 镜像并部署${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 确认
read -p "确认重新构建镜像并部署到生产环境？(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "已取消部署"
    exit 1
fi

# 检查 SSH 连接
echo -e "${YELLOW}[1/6] 检查 SSH 连接...${NC}"
ssh_exec $NODE1_PUBLIC_IP "echo 'Node1 连接成功'" || {
    echo -e "${RED}无法连接到 Node1 ($NODE1_PUBLIC_IP)${NC}"
    exit 1
}

ssh_exec $NODE2_PUBLIC_IP "echo 'Node2 连接成功'" || {
    echo -e "${RED}无法连接到 Node2 ($NODE2_PUBLIC_IP)${NC}"
    exit 1
}

echo -e "${GREEN}✅ SSH 连接检查通过${NC}"
echo ""

# 拉取最新代码
echo -e "${YELLOW}[2/6] 拉取最新代码...${NC}"
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git fetch gitee && git pull gitee master || git pull origin master"
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git fetch gitee && git pull gitee master || git pull origin master"
echo -e "${GREEN}✅ 代码已更新${NC}"
echo ""

# 停止旧容器
echo -e "${YELLOW}[3/6] 停止旧容器...${NC}"
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && docker-compose -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true"
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && docker-compose -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true"
echo -e "${GREEN}✅ 旧容器已停止${NC}"
echo ""

# 重新构建镜像
echo -e "${YELLOW}[4/6] 重新构建 Docker 镜像（这可能需要几分钟）...${NC}"
echo -e "${YELLOW}Node1 构建中...${NC}"
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && docker build --platform linux/amd64 -t hifate-bazi:latest ." || {
    echo -e "${RED}❌ Node1 镜像构建失败${NC}"
    exit 1
}

echo -e "${YELLOW}Node2 构建中...${NC}"
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && docker build --platform linux/amd64 -t hifate-bazi:latest ." || {
    echo -e "${RED}❌ Node2 镜像构建失败${NC}"
    exit 1
}

echo -e "${GREEN}✅ 镜像构建完成${NC}"
echo ""

# 验证 stripe 库是否已安装
echo -e "${YELLOW}[5/6] 验证依赖安装...${NC}"
ssh_exec $NODE1_PUBLIC_IP "docker run --rm hifate-bazi:latest python -c 'import stripe; print(\"✅ stripe:\", stripe.__version__)'" || {
    echo -e "${RED}❌ Node1 镜像中 stripe 库未安装${NC}"
    exit 1
}

ssh_exec $NODE2_PUBLIC_IP "docker run --rm hifate-bazi:latest python -c 'import stripe; print(\"✅ stripe:\", stripe.__version__)'" || {
    echo -e "${RED}❌ Node2 镜像中 stripe 库未安装${NC}"
    exit 1
}

echo -e "${GREEN}✅ 依赖验证通过${NC}"
echo ""

# 启动服务
echo -e "${YELLOW}[6/6] 启动服务...${NC}"
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
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
    if curl -sf http://$NODE1_PUBLIC_IP:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Node1 健康检查通过${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 3
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo -e "${YELLOW}等待 Node1 启动... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Node1 健康检查超时${NC}"
fi

RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://$NODE2_PUBLIC_IP:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Node2 健康检查通过${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 3
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo -e "${YELLOW}等待 Node2 启动... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Node2 健康检查超时${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "测试 Stripe 支付接口："
echo "curl -X POST http://$NODE1_PUBLIC_IP:8001/api/v1/payment/unified/create \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"provider\": \"stripe\", \"amount\": \"19.90\", \"currency\": \"USD\", \"product_name\": \"测试\", \"customer_email\": \"test@example.com\"}'"
