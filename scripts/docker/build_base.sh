#!/bin/bash
# 构建 HiFate 基础镜像
# 用途：预装所有 Python 依赖，加速后续部署
# 执行时机：首次部署 或 requirements.txt 变更后

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_DIR"

echo "=========================================="
echo "   HiFate 基础镜像构建"
echo "=========================================="
echo ""
echo "项目目录: $PROJECT_DIR"
echo ""

# 检查是否已存在基础镜像
if docker images | grep -q "hifate-base.*latest"; then
    echo "⚠️  发现已有基础镜像："
    docker images | grep "hifate-base"
    echo ""
    read -p "是否重新构建？(y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "取消构建"
        exit 0
    fi
fi

echo ""
echo "🔨 开始构建基础镜像..."
echo "   这可能需要 5-10 分钟，请耐心等待..."
echo ""

# 构建基础镜像
docker build \
    -f Dockerfile.base \
    -t hifate-base:latest \
    --progress=plain \
    .

echo ""
echo "✅ 基础镜像构建完成！"
echo ""

# 显示镜像信息
echo "镜像信息："
docker images | grep "hifate-base"

echo ""
echo "📋 后续操作："
echo "   1. 部署应用: docker compose up -d --build web"
echo "   2. 依赖变更后需重新构建: ./scripts/docker/build_base.sh"

