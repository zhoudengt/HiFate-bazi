#!/bin/bash
# ============================================
# HiFate 首次部署脚本
# ============================================
# 用途：在初始化后的 ECS 上首次部署应用
# 使用：bash scripts/aliyun/first_deploy.sh

set -e

echo "========================================"
echo "🚀 HiFate 首次部署"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 项目目录
PROJECT_DIR="/opt/HiFate-bazi"
cd ${PROJECT_DIR}

# ============================================
# 1. 检查环境
# ============================================
echo ""
echo "🔍 [1/7] 检查环境..."

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "❌ 错误：.env 文件不存在"
    echo "请先复制并编辑配置文件："
    echo "  cp .env.aliyun.template .env"
    echo "  vim .env"
    exit 1
fi

# 加载环境变量
source .env

# 检查必要的环境变量
REQUIRED_VARS="ACR_REGISTRY ACR_NAMESPACE RDS_MYSQL_HOST MYSQL_USER MYSQL_PASSWORD ALIYUN_REDIS_HOST REDIS_PASSWORD SECRET_KEY"
for var in $REQUIRED_VARS; do
    if [ -z "${!var}" ]; then
        echo "❌ 错误：环境变量 ${var} 未设置"
        exit 1
    fi
done

echo "✅ 环境检查通过"

# ============================================
# 2. 登录 ACR
# ============================================
echo ""
echo "🔐 [2/7] 登录阿里云 ACR..."

if [ -z "${ACR_USERNAME}" ] || [ -z "${ACR_PASSWORD}" ]; then
    echo "请输入 ACR 登录信息："
    read -p "ACR 用户名: " ACR_USERNAME
    read -sp "ACR 密码: " ACR_PASSWORD
    echo ""
fi

docker login ${ACR_REGISTRY} -u ${ACR_USERNAME} -p ${ACR_PASSWORD}
echo "✅ ACR 登录成功"

# ============================================
# 3. 拉取镜像
# ============================================
echo ""
echo "📥 [3/7] 拉取 Docker 镜像..."

IMAGE="${ACR_REGISTRY}/${ACR_NAMESPACE}/hifate-bazi:${IMAGE_TAG:-latest}"
echo "镜像地址: ${IMAGE}"

docker pull ${IMAGE}
echo "✅ 镜像拉取成功"

# ============================================
# 4. 创建 Docker 网络
# ============================================
echo ""
echo "🌐 [4/7] 创建 Docker 网络..."

docker network create hifate-network 2>/dev/null || echo "网络已存在"
echo "✅ Docker 网络已就绪"

# ============================================
# 5. 测试数据库连接
# ============================================
echo ""
echo "🔗 [5/7] 测试数据库连接..."

# 测试 MySQL 连接
echo "测试 MySQL 连接..."
if docker run --rm --network host mysql:8.0 \
    mysqladmin ping -h ${RDS_MYSQL_HOST} -u ${MYSQL_USER} -p${MYSQL_PASSWORD} --silent 2>/dev/null; then
    echo "✅ MySQL 连接成功"
else
    echo "⚠️ MySQL 连接测试失败，请检查配置（部署将继续）"
fi

# 测试 Redis 连接
echo "测试 Redis 连接..."
if docker run --rm --network host redis:7-alpine \
    redis-cli -h ${ALIYUN_REDIS_HOST} -a ${REDIS_PASSWORD} ping 2>/dev/null | grep -q PONG; then
    echo "✅ Redis 连接成功"
else
    echo "⚠️ Redis 连接测试失败，请检查配置（部署将继续）"
fi

# ============================================
# 6. 启动服务
# ============================================
echo ""
echo "🚀 [6/7] 启动服务..."

# 设置环境变量
export IMAGE_TAG=${IMAGE_TAG:-latest}
export ACR_REGISTRY=${ACR_REGISTRY}
export ACR_NAMESPACE=${ACR_NAMESPACE}

# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml up -d

echo "⏳ 等待服务启动..."
sleep 30

# ============================================
# 7. 健康检查
# ============================================
echo ""
echo "🏥 [7/7] 健康检查..."

MAX_RETRIES=15
RETRY=0
HEALTH_OK=false

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
        HEALTH_OK=true
        break
    fi
    RETRY=$((RETRY + 1))
    echo "⏳ 等待服务启动... ($RETRY/$MAX_RETRIES)"
    sleep 5
done

if [ "$HEALTH_OK" = "true" ]; then
    echo ""
    echo "========================================"
    echo "✅ HiFate 首次部署成功！"
    echo "========================================"
    echo ""
    echo "📊 服务状态："
    docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml ps
    echo ""
    echo "🌐 访问地址："
    echo "  - 健康检查: http://localhost:8001/health"
    echo "  - API 文档: http://localhost:8001/docs"
    echo ""
    echo "📋 常用命令："
    echo "  查看日志:   docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml logs -f"
    echo "  重启服务:   docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml restart"
    echo "  停止服务:   docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml down"
    echo ""
else
    echo ""
    echo "========================================"
    echo "❌ 部署失败：健康检查未通过"
    echo "========================================"
    echo ""
    echo "📋 查看日志排查问题："
    docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml logs --tail=50 web
    exit 1
fi
