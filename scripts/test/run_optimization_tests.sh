#!/bin/bash
# 运行优化功能测试脚本
#
# 使用方法：
#   bash scripts/test/run_optimization_tests.sh
#   或者
#   source scripts/test/enable_all_features.sh && python3 scripts/test/test_optimizations.py

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}优化功能测试运行脚本${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 步骤 1: 启用所有功能
echo -e "${YELLOW}步骤 1: 启用所有优化功能...${NC}"
if [ -f "$SCRIPT_DIR/enable_all_features.sh" ]; then
    source "$SCRIPT_DIR/enable_all_features.sh"
    echo -e "${GREEN}✓ 所有功能已启用${NC}\n"
else
    echo -e "${RED}✗ 未找到 enable_all_features.sh${NC}"
    exit 1
fi

# 步骤 2: 运行测试
echo -e "${YELLOW}步骤 2: 运行自动化测试...${NC}"
cd "$PROJECT_ROOT"

if [ -f "$SCRIPT_DIR/test_optimizations.py" ]; then
    python3 "$SCRIPT_DIR/test_optimizations.py"
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}✓ 所有测试通过！${NC}"
    else
        echo -e "\n${RED}✗ 部分测试失败，退出码: $TEST_EXIT_CODE${NC}"
        exit $TEST_EXIT_CODE
    fi
else
    echo -e "${RED}✗ 未找到 test_optimizations.py${NC}"
    exit 1
fi

# 步骤 3: 显示测试报告
echo -e "\n${YELLOW}步骤 3: 测试报告${NC}"
REPORT_FILE="$SCRIPT_DIR/optimization_test_report.json"
if [ -f "$REPORT_FILE" ]; then
    echo -e "${GREEN}✓ 测试报告已生成: $REPORT_FILE${NC}"
    echo -e "${BLUE}报告内容:${NC}"
    cat "$REPORT_FILE" | python3 -m json.tool 2>/dev/null || cat "$REPORT_FILE"
else
    echo -e "${YELLOW}⊘ 测试报告未生成${NC}"
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}测试完成${NC}"
echo -e "${BLUE}========================================${NC}\n"
