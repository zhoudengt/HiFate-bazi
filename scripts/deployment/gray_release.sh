#!/bin/bash
# ============================================
# 灰度发布脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   灰度发布${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 灰度发布配置
GRAY_PERCENTAGE="${GRAY_PERCENTAGE:-10}"  # 默认 10% 流量
GRAY_DURATION="${GRAY_DURATION:-3600}"    # 默认 1 小时

echo -e "${BLUE}灰度发布配置：${NC}"
echo "  流量百分比: ${GRAY_PERCENTAGE}%"
echo "  持续时间: ${GRAY_DURATION} 秒"
echo ""

read -p "是否继续？[y/N]: " confirm
if [[ $confirm != "y" && $confirm != "Y" ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

# 1. 创建新版本容器（不启动）
echo ""
echo -e "${BLUE}[1/4] 构建新版本容器...${NC}"
docker compose build web 2>&1 | tail -5
echo -e "${GREEN}✅ 构建完成${NC}"

# 2. 创建灰度发布标签
GRAY_TAG="gray-$(date +%Y%m%d-%H%M%S)"
echo ""
echo -e "${BLUE}[2/4] 创建灰度发布标签: ${GRAY_TAG}${NC}"
docker tag hifate-bazi-web:latest hifate-bazi-web:${GRAY_TAG} 2>/dev/null || true
echo -e "${GREEN}✅ 标签创建完成${NC}"

# 3. 启动灰度容器（使用不同的端口）
GRAY_PORT="${GRAY_PORT:-8002}"
echo ""
echo -e "${BLUE}[3/4] 启动灰度容器（端口 ${GRAY_PORT}）...${NC}"

# 使用 docker run 启动灰度容器
docker run -d \
    --name hifate-bazi-web-gray \
    --network hifate-bazi_default \
    -p ${GRAY_PORT}:8001 \
    -e GRAY_RELEASE=true \
    -e GRAY_PERCENTAGE=${GRAY_PERCENTAGE} \
    hifate-bazi-web:${GRAY_TAG} 2>&1 | tail -3

echo -e "${GREEN}✅ 灰度容器启动完成${NC}"

# 4. 配置负载均衡/流量分配
echo ""
echo -e "${BLUE}[4/4] 配置流量分配...${NC}"
echo -e "${YELLOW}⚠️  请手动配置负载均衡器：${NC}"
echo "  - ${GRAY_PERCENTAGE}% 流量 -> 灰度版本 (端口 ${GRAY_PORT})"
echo "  - $((100 - GRAY_PERCENTAGE))% 流量 -> 正式版本 (端口 8001)"
echo ""

# 保存灰度发布信息
GRAY_INFO_FILE="$PROJECT_ROOT/.gray_release_info"
cat > "$GRAY_INFO_FILE" << EOF
GRAY_TAG=${GRAY_TAG}
GRAY_PORT=${GRAY_PORT}
GRAY_PERCENTAGE=${GRAY_PERCENTAGE}
GRAY_START_TIME=$(date +%s)
GRAY_DURATION=${GRAY_DURATION}
EOF

echo -e "${GREEN}✅ 灰度发布信息已保存: ${GRAY_INFO_FILE}${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 灰度发布启动成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "下一步："
echo "  1. 监控灰度版本运行情况"
echo "  2. 如果正常，逐步增加流量"
echo "  3. 如果异常，执行回滚: ./scripts/deployment/rollback_gray.sh"
echo ""

