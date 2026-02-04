#!/bin/bash
#
# 部署后自动测试脚本
# 用于每次部署后验证接口是否正常
#
# 使用方法:
#   ./deploy/scripts/post_deploy_test.sh [环境]
#
# 参数:
#   环境: production (默认) | staging | local
#
# 示例:
#   ./deploy/scripts/post_deploy_test.sh production
#   ./deploy/scripts/post_deploy_test.sh local

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 环境配置
ENV="${1:-production}"

case "$ENV" in
    production)
        BASE_URL="http://8.210.52.217:8001"
        ;;
    staging|node2)
        BASE_URL="http://47.243.160.43:8001"
        ;;
    local)
        BASE_URL="http://localhost:8001"
        ;;
    *)
        echo -e "${RED}未知环境: $ENV${NC}"
        echo "支持的环境: production, staging, local"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "  部署后接口测试"
echo "=============================================="
echo "环境: $ENV"
echo "URL: $BASE_URL"
echo "时间: $(date)"
echo "=============================================="
echo ""

# 检查服务健康状态
echo -e "${YELLOW}>>> 检查服务健康状态...${NC}"
HEALTH=$(curl -s --max-time 10 "$BASE_URL/health" 2>/dev/null || echo '{"status":"error"}')
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo -e "${GREEN}✓ 服务健康${NC}"
else
    echo -e "${RED}✗ 服务不健康或无法连接${NC}"
    echo "响应: $HEALTH"
    exit 1
fi

# 运行 API 回归测试
echo ""
echo -e "${YELLOW}>>> 运行 API 回归测试...${NC}"

cd "$PROJECT_ROOT"

# 基础接口测试（必须通过）
echo ""
echo "--- 基础接口测试 ---"
if python3 scripts/evaluation/api_regression_test.py --url "$BASE_URL" --category basic -q; then
    echo -e "${GREEN}✓ 基础接口测试通过${NC}"
else
    echo -e "${RED}✗ 基础接口测试失败${NC}"
    exit 1
fi

# 流式接口测试（并行，必须通过）
echo ""
echo "--- 流式接口测试（并行）---"
if python3 scripts/evaluation/api_regression_test.py --url "$BASE_URL" --category stream --parallel -q; then
    echo -e "${GREEN}✓ 流式接口测试通过${NC}"
else
    echo -e "${RED}✗ 流式接口测试失败${NC}"
    exit 1
fi

# 管理接口测试（必须通过）
echo ""
echo "--- 管理接口测试 ---"
if python3 scripts/evaluation/api_regression_test.py --url "$BASE_URL" --category admin -q; then
    echo -e "${GREEN}✓ 管理接口测试通过${NC}"
else
    echo -e "${RED}✗ 管理接口测试失败${NC}"
    exit 1
fi

# 支付接口测试（可选，允许失败）
echo ""
echo "--- 支付接口测试（可选）---"
if python3 scripts/evaluation/api_regression_test.py --url "$BASE_URL" --category payment -q 2>/dev/null; then
    echo -e "${GREEN}✓ 支付接口测试通过${NC}"
else
    echo -e "${YELLOW}⚠ 支付接口测试未完全通过（可能是配置问题）${NC}"
fi

echo ""
echo "=============================================="
echo -e "${GREEN}  部署后测试完成 - 所有核心接口正常${NC}"
echo "=============================================="
echo ""
