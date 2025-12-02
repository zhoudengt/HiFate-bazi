#!/bin/bash
# ============================================
# 运行所有测试和代码检查
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
echo -e "${GREEN}   测试和代码检查${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否安装了依赖
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}⚠️  测试工具未安装，正在安装...${NC}"
    pip install -r requirements.txt
fi

# 1. 代码格式检查（Black）
echo -e "${BLUE}[1/5] 代码格式检查（Black）...${NC}"
if black --check server/ src/ services/ 2>/dev/null; then
    echo -e "${GREEN}✅ 代码格式正确${NC}"
else
    echo -e "${YELLOW}⚠️  代码格式不符合规范${NC}"
    echo -e "${YELLOW}   运行 'black server/ src/ services/' 自动格式化${NC}"
    read -p "是否自动格式化？[y/N]: " format_confirm
    if [[ $format_confirm == "y" || $format_confirm == "Y" ]]; then
        black server/ src/ services/
        echo -e "${GREEN}✅ 代码已格式化${NC}"
    fi
fi
echo ""

# 2. 导入排序检查（isort）
echo -e "${BLUE}[2/5] 导入排序检查（isort）...${NC}"
if isort --check server/ src/ services/ 2>/dev/null; then
    echo -e "${GREEN}✅ 导入排序正确${NC}"
else
    echo -e "${YELLOW}⚠️  导入排序不符合规范${NC}"
    read -p "是否自动修复？[y/N]: " isort_confirm
    if [[ $isort_confirm == "y" || $isort_confirm == "Y" ]]; then
        isort server/ src/ services/
        echo -e "${GREEN}✅ 导入已排序${NC}"
    fi
fi
echo ""

# 3. 代码质量检查（pylint）
echo -e "${BLUE}[3/5] 代码质量检查（pylint）...${NC}"
if pylint server/ --errors-only --disable=all --enable=E,F 2>/dev/null | grep -q "rated"; then
    echo -e "${GREEN}✅ 代码质量检查通过${NC}"
else
    pylint_output=$(pylint server/ --errors-only 2>/dev/null || true)
    if echo "$pylint_output" | grep -q "E[0-9]"; then
        echo -e "${RED}❌ 发现代码错误：${NC}"
        echo "$pylint_output" | grep "E[0-9]"
        exit 1
    else
        echo -e "${YELLOW}⚠️  代码质量检查有警告（非阻塞）${NC}"
    fi
fi
echo ""

# 4. 类型检查（mypy，可选）
echo -e "${BLUE}[4/5] 类型检查（mypy）...${NC}"
if command -v mypy &> /dev/null; then
    if mypy server/ --ignore-missing-imports 2>/dev/null | grep -q "Success"; then
        echo -e "${GREEN}✅ 类型检查通过${NC}"
    else
        echo -e "${YELLOW}⚠️  类型检查有警告（非阻塞）${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  mypy 未安装，跳过类型检查${NC}"
fi
echo ""

# 5. 运行测试
echo -e "${BLUE}[5/5] 运行测试（pytest）...${NC}"
if pytest tests/unit/ -v --tb=short; then
    echo -e "${GREEN}✅ 单元测试通过${NC}"
else
    echo -e "${RED}❌ 单元测试失败${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 所有检查完成！${NC}"
echo -e "${GREEN}========================================${NC}"

