#!/bin/bash
# scripts/docker/verify_protection.sh
# 验证 Docker 镜像中的代码保护效果

set -e

IMAGE_NAME=${1:-hifate-bazi:latest}

echo "🔍 验证镜像 ${IMAGE_NAME} 的代码保护效果..."
echo ""

# 1. 检查原始 .py 文件是否存在
echo "1️⃣  检查原始源码文件..."
PY_FILES=$(docker run --rm ${IMAGE_NAME} find /app -name "*.py" ! -path "*/pyarmor_runtime/*" 2>/dev/null | wc -l)
if [ "${PY_FILES}" -eq 0 ]; then
    echo "✅ 原始 .py 文件已完全删除"
else
    echo "⚠️  发现 ${PY_FILES} 个原始 .py 文件（可能未完全保护）"
    docker run --rm ${IMAGE_NAME} find /app -name "*.py" ! -path "*/pyarmor_runtime/*" 2>/dev/null | head -5
fi

# 2. 检查混淆后的文件
echo ""
echo "2️⃣  检查混淆后的文件..."
OBF_FILES=$(docker run --rm ${IMAGE_NAME} find /app -name "*.py" -path "*/pyarmor_runtime/*" 2>/dev/null | wc -l)
if [ "${OBF_FILES}" -gt 0 ]; then
    echo "✅ 发现 ${OBF_FILES} 个混淆后的文件（pyarmor_runtime）"
else
    echo "⚠️  未发现混淆后的文件"
fi

# 3. 尝试查看混淆后的代码（应该无法读取）
echo ""
echo "3️⃣  尝试读取混淆后的代码..."
SAMPLE_FILE=$(docker run --rm ${IMAGE_NAME} find /app/server -name "*.py" 2>/dev/null | head -1)
if [ -n "${SAMPLE_FILE}" ]; then
    echo "检查文件: ${SAMPLE_FILE}"
    CONTENT=$(docker run --rm ${IMAGE_NAME} cat "${SAMPLE_FILE}" 2>/dev/null | head -10)
    if echo "${CONTENT}" | grep -q "pyarmor\|__pyarmor__\|PyArmor"; then
        echo "✅ 代码已混淆（包含 pyarmor 保护标记）"
        echo "   前10行内容（已混淆）:"
        echo "${CONTENT}" | head -5 | sed 's/^/   /'
    else
        echo "⚠️  代码可能未正确混淆"
        echo "   前10行内容:"
        echo "${CONTENT}" | head -5 | sed 's/^/   /'
    fi
else
    echo "⚠️  未找到可测试的文件"
fi

# 4. 测试模块导入
echo ""
echo "4️⃣  测试混淆后的模块是否可以正常导入..."
docker run --rm ${IMAGE_NAME} python -c "
import sys
sys.path.insert(0, '/app')
try:
    import pyarmor_runtime
    print('✅ pyarmor_runtime 已导入')
    from server.services.rule_service import RuleService
    print('✅ 混淆后的模块可以正常导入')
    print('✅ 代码保护已生效')
except ImportError as e:
    print(f'❌ 模块导入失败: {e}')
    sys.exit(1)
except Exception as e:
    print(f'⚠️  验证过程出错: {e}')
    sys.exit(1)
" 2>&1

# 5. 检查是否有原始源码残留
echo ""
echo "5️⃣  检查是否有原始源码残留..."
SOURCE_FILES=$(docker run --rm ${IMAGE_NAME} find /app -type f -name "*.py" ! -path "*/pyarmor_runtime/*" ! -path "*/site-packages/*" 2>/dev/null | wc -l)
if [ "${SOURCE_FILES}" -eq 0 ]; then
    echo "✅ 没有原始源码残留"
else
    echo "⚠️  发现 ${SOURCE_FILES} 个可能的源码文件"
    docker run --rm ${IMAGE_NAME} find /app -type f -name "*.py" ! -path "*/pyarmor_runtime/*" ! -path "*/site-packages/*" 2>/dev/null | head -10
fi

# 6. 检查文件大小（混淆后的文件应该更小）
echo ""
echo "6️⃣  检查混淆后的文件大小..."
OBF_SIZE=$(docker run --rm ${IMAGE_NAME} du -sh /app/server 2>/dev/null | awk '{print $1}')
echo "   混淆后的 server 目录大小: ${OBF_SIZE}"

echo ""
echo "=========================================="
echo "✅ 验证完成！"
echo "=========================================="
echo ""
echo "保护效果总结:"
echo "  - 原始源码: ${PY_FILES} 个文件"
echo "  - 混淆文件: ${OBF_FILES} 个文件"
echo "  - 源码残留: ${SOURCE_FILES} 个文件"
echo ""
if [ "${PY_FILES}" -eq 0 ] && [ "${OBF_FILES}" -gt 0 ]; then
    echo "✅ 代码保护已成功应用！"
else
    echo "⚠️  代码保护可能未完全生效，请检查构建过程"
fi

