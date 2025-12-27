#!/bin/bash
# 部署脚本
# 用途：部署 HiFate 到 Node1 或 Node2
# 使用：bash deploy.sh node1  或  bash deploy.sh node2

set -e

# 参数检查
NODE_TYPE=${1:-}
if [ "$NODE_TYPE" != "node1" ] && [ "$NODE_TYPE" != "node2" ]; then
    echo "用法: $0 <node1|node2>"
    echo "示例: $0 node1"
    exit 1
fi

PROJECT_DIR="/opt/HiFate-bazi"
DEPLOY_DIR="${PROJECT_DIR}/deploy"

echo "========================================"
echo "HiFate 部署 - ${NODE_TYPE}"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

cd ${PROJECT_DIR}

# 检查环境变量
if [ ! -f .env ]; then
    echo "错误: .env 文件不存在"
    echo "请先复制并编辑配置文件:"
    echo "  cp deploy/env/env.template .env"
    echo "  vim .env"
    exit 1
fi

source .env

# 检查必要变量
REQUIRED_VARS="MYSQL_PASSWORD SECRET_KEY NODE1_IP NODE2_IP"
for var in $REQUIRED_VARS; do
    if [ -z "${!var}" ]; then
        echo "错误: 环境变量 ${var} 未设置"
        exit 1
    fi
done

# 🚫 注意：Nginx 配置由前端团队管理，后端部署脚本不再修改 Nginx 配置
# 如果 deploy/nginx 目录存在，说明是旧版本，应该已被删除
if [ -d "${DEPLOY_DIR}/nginx" ]; then
    echo -e "\033[1;33m⚠️  警告：发现 deploy/nginx 目录（应该已被删除）\033[0m"
    echo -e "\033[1;33m⚠️  Nginx 配置由前端团队管理，后端不再修改\033[0m"
fi

# 替换 Redis 从库配置中的主库 IP（仅 node2）
if [ "$NODE_TYPE" = "node2" ]; then
    echo "配置 Redis 从库..."
    sed -i "s/NODE1_IP/${NODE1_IP}/g" ${DEPLOY_DIR}/redis/slave.conf
fi

# 登录 ACR
echo ""
echo "[2/5] 登录镜像仓库..."
if [ -n "$ACR_USERNAME" ] && [ -n "$ACR_PASSWORD" ]; then
    echo "$ACR_PASSWORD" | docker login ${ACR_REGISTRY:-registry.cn-hangzhou.aliyuncs.com} -u $ACR_USERNAME --password-stdin 2>&1 || {
        echo "⚠️  ACR 登录失败，尝试使用本地构建镜像..."
        # 如果 ACR 登录失败，尝试本地构建
        if [ -f "Dockerfile" ]; then
            echo "构建本地镜像..."
            docker build -t ${ACR_REGISTRY:-registry.cn-hangzhou.aliyuncs.com}/${ACR_NAMESPACE:-hifate}/hifate-bazi:${IMAGE_TAG:-latest} . || echo "⚠️  本地构建失败，将尝试使用已有镜像"
        fi
    }
fi

# 拉取镜像
echo ""
echo "[3/5] 拉取镜像..."
IMAGE="${ACR_REGISTRY:-registry.cn-hangzhou.aliyuncs.com}/${ACR_NAMESPACE:-hifate}/hifate-bazi:${IMAGE_TAG:-latest}"
docker pull ${IMAGE} 2>&1 || {
    echo "⚠️  镜像拉取失败，尝试使用本地镜像或构建..."
    # 检查是否有本地镜像
    if docker images | grep -q "hifate-bazi"; then
        echo "使用本地已有镜像"
    elif [ -f "Dockerfile" ]; then
        echo "构建本地镜像..."
        cd ${PROJECT_DIR}
        docker build -t ${IMAGE} . || echo "⚠️  构建失败，请检查 Dockerfile"
    else
        echo "⚠️  无法获取镜像，部署可能失败"
    fi
}

# 启动服务
echo ""
echo "[4/5] 启动服务..."
cd ${DEPLOY_DIR}/docker

if [ "$NODE_TYPE" = "node1" ]; then
    docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml --env-file ${PROJECT_DIR}/.env up -d
else
    docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml --env-file ${PROJECT_DIR}/.env up -d
fi

# 等待启动
echo ""
echo "[5/5] 健康检查..."
sleep 15

MAX_RETRIES=20
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
        echo ""
        echo "========================================"
        echo "部署成功！"
        echo "========================================"
        echo ""
        echo "服务状态:"
        docker-compose -f docker-compose.prod.yml -f docker-compose.${NODE_TYPE}.yml ps
        echo ""
        echo "访问地址:"
        echo "  - 健康检查: http://localhost/health"
        echo "  - API 文档: http://localhost/docs"
        exit 0
    fi
    RETRY=$((RETRY + 1))
    echo "等待服务启动... ($RETRY/$MAX_RETRIES)"
    sleep 5
done

echo ""
echo "========================================"
echo "部署可能存在问题，请检查日志:"
echo "  docker-compose logs -f web"
echo "========================================"
exit 1
