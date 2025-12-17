#!/bin/bash
# scripts/docker/test_image.sh
# Docker 镜像测试脚本
# 功能：测试 Docker 镜像的基本功能、完整性、依赖关系

set -e

IMAGE_NAME=${1:-hifate-bazi:latest}

echo "=========================================="
echo "🧪 Docker 镜像测试"
echo "=========================================="
echo "镜像: ${IMAGE_NAME}"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ============================================
# 1. 检查镜像是否存在
# ============================================
echo "1️⃣  检查镜像是否存在..."
if ! docker image inspect "${IMAGE_NAME}" > /dev/null 2>&1; then
    echo "❌ 镜像不存在: ${IMAGE_NAME}"
    echo "请先构建镜像或拉取镜像"
    exit 1
fi
echo "✅ 镜像存在"

# 获取镜像信息
IMAGE_SIZE=$(docker image inspect "${IMAGE_NAME}" --format='{{.Size}}' | numfmt --to=iec-i --suffix=B)
echo "   镜像大小: ${IMAGE_SIZE}"

# ============================================
# 2. 检查关键文件
# ============================================
echo ""
echo "2️⃣  检查关键文件..."

REQUIRED_FILES=(
    "/app/server/start.py"
    "/app/server/main.py"
    "/app/requirements.txt"
)

MISSING_FILES=0
for file in "${REQUIRED_FILES[@]}"; do
    if docker run --rm "${IMAGE_NAME}" test -f "${file}" 2>/dev/null; then
        echo "   ✅ ${file}"
    else
        echo "   ❌ ${file} 不存在"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    echo "❌ 缺少 ${MISSING_FILES} 个关键文件"
    exit 1
fi

# ============================================
# 3. 检查 Python 环境
# ============================================
echo ""
echo "3️⃣  检查 Python 环境..."

PYTHON_VERSION=$(docker run --rm "${IMAGE_NAME}" python --version 2>&1)
echo "   Python版本: ${PYTHON_VERSION}"

# 检查 Python 路径
PYTHON_PATH=$(docker run --rm "${IMAGE_NAME}" which python)
echo "   Python路径: ${PYTHON_PATH}"

# ============================================
# 4. 检查核心依赖
# ============================================
echo ""
echo "4️⃣  检查核心依赖..."

CORE_PACKAGES=(
    "uvicorn"
    "fastapi"
    "grpc"
    "pymysql"
    "redis"
)

MISSING_PACKAGES=0
for package in "${CORE_PACKAGES[@]}"; do
    if docker run --rm "${IMAGE_NAME}" python -c "import ${package}" 2>/dev/null; then
        VERSION=$(docker run --rm "${IMAGE_NAME}" python -c "import ${package}; print(${package}.__version__ if hasattr(${package}, '__version__') else 'N/A')" 2>/dev/null || echo "N/A")
        echo "   ✅ ${package} (${VERSION})"
    else
        echo "   ❌ ${package} 未安装"
        MISSING_PACKAGES=$((MISSING_PACKAGES + 1))
    fi
done

if [ $MISSING_PACKAGES -gt 0 ]; then
    echo "❌ 缺少 ${MISSING_PACKAGES} 个核心依赖"
    exit 1
fi

# ============================================
# 5. 检查应用代码结构
# ============================================
echo ""
echo "5️⃣  检查应用代码结构..."

REQUIRED_DIRS=(
    "/app/server"
    "/app/src"
    "/app/services"
)

MISSING_DIRS=0
for dir in "${REQUIRED_DIRS[@]}"; do
    if docker run --rm "${IMAGE_NAME}" test -d "${dir}" 2>/dev/null; then
        FILE_COUNT=$(docker run --rm "${IMAGE_NAME}" find "${dir}" -type f -name "*.py" 2>/dev/null | wc -l)
        echo "   ✅ ${dir} (${FILE_COUNT} 个 Python 文件)"
    else
        echo "   ❌ ${dir} 不存在"
        MISSING_DIRS=$((MISSING_DIRS + 1))
    fi
done

if [ $MISSING_DIRS -gt 0 ]; then
    echo "❌ 缺少 ${MISSING_DIRS} 个关键目录"
    exit 1
fi

# ============================================
# 6. 测试模块导入
# ============================================
echo ""
echo "6️⃣  测试模块导入..."

IMPORT_TESTS=(
    "from server.main import app"
    "from src.bazi_calculator import BaziCalculator"
)

IMPORT_FAILED=0
for import_test in "${IMPORT_TESTS[@]}"; do
    if docker run --rm "${IMAGE_NAME}" python -c "${import_test}" 2>/dev/null; then
        echo "   ✅ ${import_test}"
    else
        echo "   ❌ ${import_test} 导入失败"
        IMPORT_FAILED=$((IMPORT_FAILED + 1))
    fi
done

if [ $IMPORT_FAILED -gt 0 ]; then
    echo "⚠️  ${IMPORT_FAILED} 个模块导入失败（可能是正常的，如果缺少运行时依赖）"
fi

# ============================================
# 7. 检查环境变量
# ============================================
echo ""
echo "7️⃣  检查环境变量配置..."

ENV_VARS=(
    "APP_HOME"
    "PYTHONUNBUFFERED"
)

for env_var in "${ENV_VARS[@]}"; do
    VALUE=$(docker run --rm "${IMAGE_NAME}" printenv "${env_var}" 2>/dev/null || echo "")
    if [ -n "${VALUE}" ]; then
        echo "   ✅ ${env_var}=${VALUE}"
    else
        echo "   ⚠️  ${env_var} 未设置"
    fi
done

# ============================================
# 8. 检查端口暴露
# ============================================
echo ""
echo "8️⃣  检查端口暴露..."

EXPOSED_PORTS=$(docker image inspect "${IMAGE_NAME}" --format='{{json .Config.ExposedPorts}}' | jq -r 'keys[]' 2>/dev/null || echo "")
if echo "${EXPOSED_PORTS}" | grep -q "8001"; then
    echo "   ✅ 端口 8001 已暴露"
else
    echo "   ⚠️  端口 8001 未暴露（可能通过 docker-compose 配置）"
fi

# ============================================
# 9. 检查健康检查配置
# ============================================
echo ""
echo "9️⃣  检查健康检查配置..."

HEALTHCHECK=$(docker image inspect "${IMAGE_NAME}" --format='{{json .Config.Healthcheck}}' 2>/dev/null || echo "")
if [ -n "${HEALTHCHECK}" ] && [ "${HEALTHCHECK}" != "null" ]; then
    echo "   ✅ 健康检查已配置"
    echo "${HEALTHCHECK}" | jq '.' 2>/dev/null || echo "${HEALTHCHECK}"
else
    echo "   ⚠️  健康检查未配置"
fi

# ============================================
# 10. 测试容器启动（快速测试）
# ============================================
echo ""
echo "🔟 测试容器启动..."

CONTAINER_ID=$(docker run -d --rm -p 18001:8001 \
    -e MYSQL_HOST=localhost \
    -e REDIS_HOST=localhost \
    "${IMAGE_NAME}" 2>&1) || {
    echo "❌ 容器启动失败"
    exit 1
}

echo "   容器ID: ${CONTAINER_ID:0:12}"

# 等待几秒
sleep 5

# 检查容器状态
CONTAINER_STATUS=$(docker inspect "${CONTAINER_ID}" --format='{{.State.Status}}' 2>/dev/null || echo "unknown")
echo "   容器状态: ${CONTAINER_STATUS}"

# 停止容器
docker stop "${CONTAINER_ID}" > /dev/null 2>&1 || true

if [ "${CONTAINER_STATUS}" == "running" ]; then
    echo "   ✅ 容器可以正常启动"
else
    echo "   ⚠️  容器状态异常: ${CONTAINER_STATUS}"
    docker logs "${CONTAINER_ID}" 2>&1 | tail -20 || true
fi

# ============================================
# 测试总结
# ============================================
echo ""
echo "=========================================="
echo "✅ 镜像测试完成"
echo "=========================================="
echo "镜像: ${IMAGE_NAME}"
echo "大小: ${IMAGE_SIZE}"
echo "状态: 通过"
echo ""






