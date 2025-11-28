#!/bin/bash
# 构建 HiFate 基础镜像
# 仅在 requirements.txt 变更时需要执行

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "   HiFate 基础镜像构建工具"
echo "=========================================="
echo ""

# 检查 requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误：找不到 requirements.txt"
    exit 1
fi

echo "📋 当前 requirements.txt 内容："
echo "   $(wc -l < requirements.txt) 行依赖"
echo ""

# 询问是否继续
read -p "是否开始构建基础镜像？(y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "🔨 开始构建基础镜像..."
echo "   ⏱️  预计耗时：5-10 分钟"
echo "   📦 镜像大小：约 1-2 GB"
echo ""

# 构建基础镜像（跨平台兼容）
docker build \
    --platform linux/amd64 \
    -f Dockerfile.base \
    -t hifate-base:latest \
    -t hifate-base:$(date +%Y%m%d) \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 基础镜像构建成功！"
    echo ""
    echo "📦 镜像信息："
    docker images hifate-base:latest --format "   {{.Repository}}:{{.Tag}} - {{.Size}}"
    echo ""
    echo "💡 提示："
    echo "   - 本地使用：直接运行 docker compose up -d --build"
    echo "   - 如需推送到服务器：使用 ./scripts/docker/push_base.sh"
    echo ""
else
    echo ""
    echo "❌ 构建失败，请检查错误信息"
    exit 1
fi
