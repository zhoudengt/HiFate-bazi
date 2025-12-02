#!/bin/bash
# ============================================
# 灰度发布回滚脚本
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

GRAY_INFO_FILE="$PROJECT_ROOT/.gray_release_info"

if [ ! -f "$GRAY_INFO_FILE" ]; then
    echo -e "${RED}❌ 未找到灰度发布信息文件${NC}"
    echo "请确认是否正在进行灰度发布"
    exit 1
fi

source "$GRAY_INFO_FILE"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   灰度发布回滚${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

echo -e "${BLUE}当前灰度发布信息：${NC}"
echo "  标签: ${GRAY_TAG}"
echo "  端口: ${GRAY_PORT}"
echo "  流量: ${GRAY_PERCENTAGE}%"
echo ""

read -p "确认回滚灰度发布？[y/N]: " confirm
if [[ $confirm != "y" && $confirm != "Y" ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

# 1. 停止灰度容器
echo ""
echo -e "${BLUE}[1/2] 停止灰度容器...${NC}"
docker stop hifate-bazi-web-gray 2>/dev/null || true
docker rm hifate-bazi-web-gray 2>/dev/null || true
echo -e "${GREEN}✅ 灰度容器已停止${NC}"

# 2. 删除灰度发布信息
echo ""
echo -e "${BLUE}[2/2] 清理灰度发布信息...${NC}"
rm -f "$GRAY_INFO_FILE"
echo -e "${GREEN}✅ 清理完成${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 灰度发布回滚成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "所有流量已切回正式版本"
echo ""

