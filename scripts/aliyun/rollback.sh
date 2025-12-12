#!/bin/bash
# ============================================
# HiFate 版本回滚脚本
# ============================================
# 用途：回滚到指定版本的镜像
# 使用：bash scripts/aliyun/rollback.sh <image_tag>
# 示例：bash scripts/aliyun/rollback.sh abc1234

set -e

echo "========================================"
echo "🔄 HiFate 版本回滚"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 项目目录
PROJECT_DIR="/opt/HiFate-bazi"
cd ${PROJECT_DIR}

# 加载环境变量
source .env

# ============================================
# 1. 检查参数
# ============================================
if [ -z "$1" ]; then
    echo ""
    echo "❌ 错误：请指定要回滚的镜像标签"
    echo ""
    echo "用法: $0 <image_tag>"
    echo "示例: $0 abc1234"
    echo "      $0 v1.2.3"
    echo "      $0 latest"
    echo ""
    echo "📋 当前可用的镜像："
    docker images | grep "${ACR_REGISTRY}/${ACR_NAMESPACE}/hifate-bazi" | head -10
    echo ""
    echo "💡 提示：可以从 ACR 控制台查看更多历史镜像标签"
    exit 1
fi

ROLLBACK_TAG=$1
IMAGE="${ACR_REGISTRY}/${ACR_NAMESPACE}/hifate-bazi:${ROLLBACK_TAG}"

echo ""
echo "📋 回滚信息："
echo "  目标标签: ${ROLLBACK_TAG}"
echo "  完整镜像: ${IMAGE}"
echo ""

# ============================================
# 2. 确认回滚
# ============================================
read -p "⚠️ 确认要回滚到 ${ROLLBACK_TAG} 吗？(y/N) " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消回滚"
    exit 0
fi

# ============================================
# 3. 备份当前版本信息
# ============================================
echo ""
echo "💾 备份当前版本信息..."

CURRENT_IMAGE=$(docker inspect --format='{{.Config.Image}}' hifate-web 2>/dev/null || echo "unknown")
echo "当前运行版本: ${CURRENT_IMAGE}"
echo "${CURRENT_IMAGE}" > /tmp/hifate_rollback_backup_$(date +%Y%m%d_%H%M%S).txt

# ============================================
# 4. 拉取回滚镜像
# ============================================
echo ""
echo "📥 拉取回滚镜像..."

if ! docker pull ${IMAGE}; then
    echo "❌ 拉取镜像失败: ${IMAGE}"
    echo "请检查镜像标签是否正确"
    exit 1
fi

echo "✅ 镜像拉取成功"

# ============================================
# 5. 执行回滚
# ============================================
echo ""
echo "🔄 执行回滚..."

export IMAGE_TAG=${ROLLBACK_TAG}
export ACR_REGISTRY=${ACR_REGISTRY}
export ACR_NAMESPACE=${ACR_NAMESPACE}

# 回滚 Web 服务
docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml up -d --no-deps --force-recreate web

echo "⏳ 等待服务启动..."
sleep 20

# ============================================
# 6. 健康检查
# ============================================
echo ""
echo "🏥 健康检查..."

MAX_RETRIES=10
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
    echo "✅ Web 服务回滚成功"
    
    # 询问是否回滚其他微服务
    read -p "是否回滚其他微服务？(y/N) " rollback_all
    if [ "$rollback_all" = "y" ] || [ "$rollback_all" = "Y" ]; then
        echo ""
        echo "🔄 回滚其他微服务..."
        docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml up -d --no-deps \
            bazi-core bazi-fortune bazi-analyzer rule-service fortune-analyzer \
            payment-service fortune-rule intent-service prompt-optimizer desk-fengshui
        echo "✅ 所有微服务回滚完成"
    fi
    
    echo ""
    echo "========================================"
    echo "✅ 回滚完成！"
    echo "========================================"
    echo ""
    echo "📊 当前服务状态："
    docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml ps
else
    echo ""
    echo "========================================"
    echo "❌ 回滚失败：健康检查未通过"
    echo "========================================"
    echo ""
    echo "📋 查看日志："
    docker-compose -f docker-compose.yml -f docker-compose.aliyun.yml logs --tail=50 web
    echo ""
    echo "💡 如需恢复之前的版本："
    echo "   bash scripts/aliyun/rollback.sh ${CURRENT_IMAGE##*:}"
    exit 1
fi
