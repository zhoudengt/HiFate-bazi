#!/bin/bash
# scripts/test_buildx_fix.sh - 测试 buildx 修复脚本（本地验证）

set -e

echo "=========================================="
echo "  测试 buildx 修复脚本"
echo "=========================================="
echo ""

# 测试脚本是否存在
if [ ! -f "scripts/fix_buildx_version.sh" ]; then
    echo "❌ 修复脚本不存在：scripts/fix_buildx_version.sh"
    exit 1
fi
echo "✅ 修复脚本存在"

# 测试脚本可执行
if [ ! -x "scripts/fix_buildx_version.sh" ]; then
    echo "⚠️  脚本不可执行，正在添加执行权限..."
    chmod +x scripts/fix_buildx_version.sh
fi
echo "✅ 脚本可执行"

# 测试语法
echo ""
echo "检查脚本语法..."
if bash -n scripts/fix_buildx_version.sh 2>&1; then
    echo "✅ 脚本语法正确"
else
    echo "❌ 脚本语法错误"
    exit 1
fi

# 检查文档是否存在
echo ""
echo "检查文档..."
if [ -f "docs/fix_buildx_version_guide.md" ]; then
    echo "✅ 详细指南存在：docs/fix_buildx_version_guide.md"
else
    echo "⚠️  详细指南不存在"
fi

if [ -f "docs/fix_buildx_quick_reference.md" ]; then
    echo "✅ 快速参考存在：docs/fix_buildx_quick_reference.md"
else
    echo "⚠️  快速参考不存在"
fi

# 检查关键功能
echo ""
echo "检查脚本关键功能..."
if grep -q "docker buildx version" scripts/fix_buildx_version.sh; then
    echo "✅ 包含版本检查功能"
else
    echo "❌ 缺少版本检查功能"
fi

if grep -q "NEED_UPGRADE" scripts/fix_buildx_version.sh; then
    echo "✅ 包含升级逻辑"
else
    echo "❌ 缺少升级逻辑"
fi

if grep -q "frontend-gateway" scripts/fix_buildx_version.sh; then
    echo "✅ 包含 frontend-gateway 检查"
else
    echo "❌ 缺少 frontend-gateway 检查"
fi

echo ""
echo "=========================================="
echo "✅ 本地测试完成"
echo "=========================================="
echo ""
echo "📋 下一步：在服务器上执行以下命令进行实际测试"
echo ""
echo "1. SSH 连接到服务器："
echo "   ssh frontend-user@服务器IP"
echo ""
echo "2. 进入项目目录："
echo "   cd /opt/HiFate-bazi"
echo ""
echo "3. 执行修复脚本："
echo "   bash scripts/fix_buildx_version.sh"
echo ""
echo "4. 验证修复："
echo "   docker buildx version"
echo "   docker-compose up -d frontend-gateway"
echo ""

