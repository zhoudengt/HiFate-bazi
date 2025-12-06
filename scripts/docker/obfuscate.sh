#!/bin/bash
# scripts/docker/obfuscate.sh
# PyArmor 混淆脚本（用于本地测试）

set -e

echo "🔒 开始使用 PyArmor 混淆代码..."
echo ""

# 检查 PyArmor 是否安装
if ! command -v pyarmor &> /dev/null; then
    echo "❌ PyArmor 未安装，正在安装..."
    pip install pyarmor
fi

# 显示 PyArmor 版本
echo "📦 PyArmor 版本:"
pyarmor --version
echo ""

# 创建输出目录
OUTPUT_DIR="./obfuscated"
rm -rf ${OUTPUT_DIR}
mkdir -p ${OUTPUT_DIR}

echo "📁 输出目录: ${OUTPUT_DIR}"
echo ""

# 混淆代码（使用最高保护级别）
echo "🔐 开始混淆代码（最高保护级别）..."
echo "   保护选项:"
echo "   - obf-code=2 (最高级别代码混淆)"
echo "   - obf-mod=1 (模块级别混淆)"
echo "   - wrap-mode=1 (包装模式)"
echo "   - restrict-mode=4 (最高限制模式)"
echo "   - enable-rft=1 (运行时保护)"
echo "   - advanced-mode=2 (高级模式)"
echo ""

pyarmor gen --platform linux.x86_64 \
    --obf-code=2 \
    --obf-mod=1 \
    --wrap-mode=1 \
    --restrict-mode=4 \
    --enable-rft=1 \
    --advanced-mode=2 \
    --output ${OUTPUT_DIR} \
    --recursive \
    --exclude "frontend" \
    --exclude "docs" \
    --exclude "tests" \
    --exclude "scripts" \
    --exclude "*.pyc" \
    --exclude "__pycache__" \
    --exclude ".git" \
    --exclude "node_modules" \
    --exclude "logs" \
    --exclude "*.log" \
    server/ services/ src/ proto/ mianxiang_hand_fengshui/

if [ $? -ne 0 ]; then
    echo "❌ 混淆失败！"
    exit 1
fi

echo ""
echo "📋 复制非 Python 文件..."

# 复制非 Python 文件
find . -type f ! -name "*.py" ! -name "*.pyc" ! -path "*/__pycache__/*" ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/logs/*" ! -name "*.log" ! -path "*/${OUTPUT_DIR}/*" \
    -exec cp --parents {} ${OUTPUT_DIR}/ \; 2>/dev/null || true

# 复制前端文件
if [ -d "frontend" ]; then
    echo "   复制前端文件..."
    cp -r frontend ${OUTPUT_DIR}/ 2>/dev/null || true
fi

# 复制配置文件
if [ -d "config" ]; then
    echo "   复制配置文件..."
    cp -r config ${OUTPUT_DIR}/ 2>/dev/null || true
fi

# 复制 proto 文件（gRPC 需要）
if [ -d "proto" ]; then
    echo "   复制 proto 文件..."
    mkdir -p ${OUTPUT_DIR}/proto
    cp proto/*.proto ${OUTPUT_DIR}/proto/ 2>/dev/null || true
fi

# 复制其他必要文件
if [ -f "requirements.txt" ]; then
    cp requirements.txt ${OUTPUT_DIR}/ 2>/dev/null || true
fi

if [ -f "README.md" ]; then
    cp README.md ${OUTPUT_DIR}/ 2>/dev/null || true
fi

echo ""
echo "✅ 混淆完成！"
echo ""
echo "📊 统计信息:"
echo "   输出目录: ${OUTPUT_DIR}"
echo "   混淆后的 Python 文件数: $(find ${OUTPUT_DIR} -name "*.py" | wc -l)"
echo "   pyarmor_runtime 目录: $(find ${OUTPUT_DIR} -type d -name "pyarmor_runtime" | wc -l)"
echo ""
echo "⚠️  重要提示:"
echo "   1. 混淆后的代码无法反编译"
echo "   2. 请妥善保管原始代码（Git 备份）"
echo "   3. 混淆后的代码只能在 linux.x86_64 平台运行"
echo "   4. 测试混淆后的代码: cd ${OUTPUT_DIR} && python server/start.py"
echo ""

