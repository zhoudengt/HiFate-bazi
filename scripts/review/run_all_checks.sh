#!/bin/bash
# 运行所有代码审查检查脚本
# 用途：在提交 PR 前运行所有检查

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================"
echo "🔍 代码审查检查"
echo "========================================"
echo ""

# 检查变更的文件
CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null || echo "")

if [ -z "$CHANGED_FILES" ]; then
    echo -e "${YELLOW}⚠️  未找到变更的文件${NC}"
    echo "提示：请先提交代码变更"
    exit 0
fi

echo -e "${BLUE}变更的文件：${NC}"
echo "$CHANGED_FILES" | while read -r file; do
    echo "  - $file"
done
echo ""

# 运行所有检查
ERRORS=0

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}1. 开发规范符合性检查${NC}"
echo -e "${BLUE}========================================${NC}"
python3 scripts/review/check_cursorrules.py || ERRORS=$((ERRORS + 1))
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}2. 安全漏洞检查${NC}"
echo -e "${BLUE}========================================${NC}"
python3 scripts/review/check_security.py || ERRORS=$((ERRORS + 1))
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}3. 热更新支持检查${NC}"
echo -e "${BLUE}========================================${NC}"
python3 scripts/review/check_hot_reload.py || echo -e "${YELLOW}⚠️  热更新检查有警告${NC}"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}4. 编码方式检查${NC}"
echo -e "${BLUE}========================================${NC}"
python3 scripts/review/check_encoding.py || ERRORS=$((ERRORS + 1))
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}5. gRPC 端点注册检查${NC}"
echo -e "${BLUE}========================================${NC}"
python3 scripts/review/check_grpc.py || ERRORS=$((ERRORS + 1))
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}6. 测试覆盖检查${NC}"
echo -e "${BLUE}========================================${NC}"
python3 scripts/review/check_tests.py || echo -e "${YELLOW}⚠️  测试覆盖检查有警告${NC}"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}综合代码审查检查${NC}"
echo -e "${BLUE}========================================${NC}"
python3 scripts/review/code_review_check.py || ERRORS=$((ERRORS + 1))
echo ""

# 输出总结
echo "========================================"
echo "📊 检查结果总结"
echo "========================================"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有核心检查通过！${NC}"
    echo ""
    echo "可以提交 PR 了！"
    exit 0
else
    echo -e "${RED}❌ 发现 $ERRORS 个错误，请修复后重试${NC}"
    echo ""
    echo "请根据上述错误信息修复问题，然后重新运行检查："
    echo "  bash scripts/review/run_all_checks.sh"
    exit 1
fi

