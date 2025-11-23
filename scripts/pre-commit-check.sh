#!/bin/bash

# HiFate-bazi 提交前检查脚本
# 使用方式：./scripts/pre-commit-check.sh

set -e

echo "=========================================="
echo "🔍 HiFate-bazi 提交前检查"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查计数
ERRORS=0
WARNINGS=0

# 1. 检查当前分支
echo ""
echo "📍 1. 检查当前分支..."
CURRENT_BRANCH=$(git branch --show-current)
echo "   当前分支：$CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" = "master" ]; then
    echo -e "   ${RED}❌ 警告：不建议直接在 master 分支开发${NC}"
    ((WARNINGS++))
elif [ "$CURRENT_BRANCH" = "develop" ]; then
    echo -e "   ${YELLOW}⚠️  注意：在 develop 分支开发，建议使用 feature 分支${NC}"
else
    echo -e "   ${GREEN}✅ 当前在功能分支${NC}"
fi

# 2. 检查未暂存的修改
echo ""
echo "📝 2. 检查未暂存的修改..."
UNSTAGED=$(git diff --name-only)
if [ -n "$UNSTAGED" ]; then
    echo -e "   ${YELLOW}⚠️  有未暂存的修改：${NC}"
    git diff --name-only | sed 's/^/     - /'
    ((WARNINGS++))
else
    echo -e "   ${GREEN}✅ 所有修改已暂存${NC}"
fi

# 3. 检查敏感文件
echo ""
echo "🔒 3. 检查敏感文件..."
STAGED_FILES=$(git diff --cached --name-only)
SENSITIVE_PATTERNS=(
    "*.env"
    "*.key"
    "*.pem"
    "*password*"
    "*secret*"
    "*.pid"
    "*.log"
)

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if echo "$STAGED_FILES" | grep -qi "$pattern"; then
        echo -e "   ${RED}❌ 发现敏感文件：$pattern${NC}"
        echo "$STAGED_FILES" | grep -i "$pattern" | sed 's/^/     - /'
        ((ERRORS++))
    fi
done

if [ $ERRORS -eq 0 ]; then
    echo -e "   ${GREEN}✅ 无敏感文件${NC}"
fi

# 4. 检查日志文件
echo ""
echo "📋 4. 检查日志文件..."
if echo "$STAGED_FILES" | grep -q "logs/"; then
    echo -e "   ${RED}❌ 不要提交日志文件${NC}"
    echo "$STAGED_FILES" | grep "logs/" | sed 's/^/     - /'
    ((ERRORS++))
else
    echo -e "   ${GREEN}✅ 无日志文件${NC}"
fi

# 5. 检查缓存文件
echo ""
echo "🗂️  5. 检查缓存文件..."
if echo "$STAGED_FILES" | grep -E "__pycache__|\.pyc$|\.pyo$"; then
    echo -e "   ${RED}❌ 不要提交 Python 缓存文件${NC}"
    echo "$STAGED_FILES" | grep -E "__pycache__|\.pyc$|\.pyo$" | sed 's/^/     - /'
    ((ERRORS++))
else
    echo -e "   ${GREEN}✅ 无缓存文件${NC}"
fi

# 6. 检查大文件
echo ""
echo "📦 6. 检查大文件（>1MB）..."
LARGE_FILES=$(git diff --cached --name-only | while read file; do
    if [ -f "$file" ]; then
        SIZE=$(du -k "$file" | cut -f1)
        if [ $SIZE -gt 1024 ]; then
            echo "$file ($SIZE KB)"
        fi
    fi
done)

if [ -n "$LARGE_FILES" ]; then
    echo -e "   ${YELLOW}⚠️  发现大文件：${NC}"
    echo "$LARGE_FILES" | sed 's/^/     - /'
    ((WARNINGS++))
else
    echo -e "   ${GREEN}✅ 无大文件${NC}"
fi

# 7. 检查 TODO/FIXME 标记
echo ""
echo "📌 7. 检查 TODO/FIXME 标记..."
TODO_COUNT=$(git diff --cached | grep -E "^\+.*TODO|^\+.*FIXME" | wc -l | tr -d ' ')
if [ "$TODO_COUNT" -gt 0 ]; then
    echo -e "   ${YELLOW}⚠️  发现 $TODO_COUNT 个 TODO/FIXME 标记${NC}"
    git diff --cached | grep -E "^\+.*TODO|^\+.*FIXME" | sed 's/^/     /'
    ((WARNINGS++))
else
    echo -e "   ${GREEN}✅ 无未完成的 TODO/FIXME${NC}"
fi

# 8. 检查调试代码
echo ""
echo "🐛 8. 检查调试代码..."
DEBUG_PATTERNS=(
    "console\.log"
    "print\("
    "debugger"
    "pdb\.set_trace"
    "import pdb"
)

DEBUG_FOUND=0
for pattern in "${DEBUG_PATTERNS[@]}"; do
    if git diff --cached | grep -E "^\+.*$pattern" > /dev/null; then
        if [ $DEBUG_FOUND -eq 0 ]; then
            echo -e "   ${YELLOW}⚠️  发现调试代码：${NC}"
            DEBUG_FOUND=1
            ((WARNINGS++))
        fi
        echo "     - $pattern"
    fi
done

if [ $DEBUG_FOUND -eq 0 ]; then
    echo -e "   ${GREEN}✅ 无调试代码${NC}"
fi

# 9. 检查提交信息
echo ""
echo "💬 9. 提交信息预检..."
echo "   当前暂存的文件："
git diff --cached --name-only | sed 's/^/     - /'

echo ""
echo "   建议的提交信息格式："
echo "     [类型] 简短描述"
echo ""
echo "     - 修改文件：[列出主要文件]"
echo "     - 功能说明：[详细说明]"
echo "     - 测试情况：[测试结果]"
echo ""
echo "   类型可选：[新增] [修复] [优化] [重构] [文档] [测试] [配置]"

# 10. 本地测试提醒
echo ""
echo "🧪 10. 本地测试提醒..."
if [ -f "start_all_services.sh" ]; then
    echo -e "   ${YELLOW}⚠️  提交前请确保本地测试通过：${NC}"
    echo "     ./start_all_services.sh"
    echo "     访问 http://localhost:8001 测试功能"
else
    echo -e "   ${GREEN}✅ 已确认本地测试${NC}"
fi

# 总结
echo ""
echo "=========================================="
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ 发现 $ERRORS 个错误，$WARNINGS 个警告${NC}"
    echo "   请修复错误后再提交"
    echo "=========================================="
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现 $WARNINGS 个警告${NC}"
    echo "   建议检查后再提交"
    echo "=========================================="
    read -p "是否继续提交？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ 所有检查通过！${NC}"
    echo "=========================================="
fi

echo ""
echo "可以使用以下命令提交："
echo "  git commit -m \"[类型] 描述\""
echo "  git push origin $CURRENT_BRANCH"
echo ""

