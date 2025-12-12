#!/bin/bash
# 回滚脚本
# 用途：回滚到指定版本的镜像
# 使用：bash rollback.sh <image_tag> <node1|node2>

set -e

IMAGE_TAG=${1:-}
NODE_TYPE=${2:-}

if [ -z "$IMAGE_TAG" ] || [ -z "$NODE_TYPE" ]; then
    echo "用法: $0 <image_tag> <node1|node2>"
    echo "示例: $0 abc1234 node1"
    echo ""
    echo "当前可用镜像:"
    docker images | grep hifate-bazi | head -10
    exit 1
fi

if [ "$NODE_TYPE" != "node1" ] && [ "$NODE_TYPE" != "node2" ]; then
    echo "错误: node 类型必须是 node1 或 node2"
    exit 1
fi

PROJECT_DIR="/opt/HiFate-bazi"
DEPLOY_DIR="${PROJECT_DIR}/deploy"

cd ${PROJECT_DIR}
source .env

echo "========================================"
echo "HiFate 回滚"
echo "目标版本: ${IMAGE_TAG}"
echo "节点: ${NODE_TYPE}"
echo "========================================"

read -p "确认回滚? (y/N) " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# 备份当前版本信息
CURRENT_IMAGE=$(docker inspect --format='{{.Config.Image}}' hifate-web 2>/dev/null || echo "unknown")
echo "当前版本: ${CURRENT_IMAGE}"
echo "${CURRENT_IMAGE}" > /tmp/hifate_rollback_$(date +%Y%m%d_%H%M%S).txt

# 拉取回滚镜像
echo ""
echo "拉取镜像..."
ROLLBACK_IMAGE="${ACR_REGISTRY:-registry.cn-hangzhou.aliyuncs.com}/${ACR_NAMESPACE:-hifate}/hifate-bazi:${IMAGE_TAG}"
docker pull ${ROLLBACK_IMAGE}

# 执行回滚
echo ""
echo "执行回滚..."
cd ${DEPLOY_DIR}/docker
export IMAGE_TAG=${IMAGE_TAG}

docker-compose -f docker-compose.prod.yml -f docker-compose.${NODE_TYPE}.yml --env-file ${PROJECT_DIR}/.env up -d --no-deps web

# 健康检查
echo ""
echo "健康检查..."
sleep 15

if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
    echo ""
    echo "========================================"
    echo "回滚成功！"
    echo "========================================"
else
    echo ""
    echo "========================================"
    echo "回滚后健康检查失败，请检查日志"
    echo "========================================"
    exit 1
fi
