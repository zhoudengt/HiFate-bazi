#!/bin/bash
# 检查基础镜像是否需要更新

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "   基础镜像状态检查"
echo "=========================================="
echo ""

# 检查基础镜像是否存在
if ! docker images hifate-base:latest --format "{{.Repository}}" | grep -q hifate-base; then
    echo "⚠️  基础镜像不存在"
    echo ""
    echo "请先构建基础镜像："
    echo "   ./scripts/docker/build_base.sh"
    echo ""
    exit 1
fi

echo "✅ 基础镜像存在"
docker images hifate-base:latest --format "   镜像: {{.Repository}}:{{.Tag}}"
docker images hifate-base:latest --format "   大小: {{.Size}}"
docker images hifate-base:latest --format "   创建: {{.CreatedAt}}"
echo ""

# 检查 requirements.txt 是否有变更（包括微服务依赖）
REQ_HASH=$(md5 -q requirements.txt 2>/dev/null || md5sum requirements.txt | cut -d' ' -f1)
DESK_FENGSHUI_REQ_HASH=""
if [ -f "services/desk_fengshui/requirements.txt" ]; then
    DESK_FENGSHUI_REQ_HASH=$(md5 -q services/desk_fengshui/requirements.txt 2>/dev/null || md5sum services/desk_fengshui/requirements.txt | cut -d' ' -f1)
fi
COMBINED_HASH="${REQ_HASH}_${DESK_FENGSHUI_REQ_HASH}"

BASE_REQ_HASH=$(docker run --rm hifate-base:latest cat /app/.requirements_hash 2>/dev/null | tr -d '\n\r' || echo "")

if [ -z "$BASE_REQ_HASH" ]; then
    echo "⚠️  无法读取基础镜像的 requirements 哈希值"
    echo "   建议重建基础镜像"
    echo ""
    exit 1
fi

if [ "$REQ_HASH" != "$BASE_REQ_HASH" ]; then
    echo "⚠️  requirements.txt 已变更，建议更新基础镜像"
    echo "   当前: $REQ_HASH"
    echo "   镜像: $BASE_REQ_HASH"
    if [ -n "$DESK_FENGSHUI_REQ_HASH" ]; then
        echo "   微服务依赖: $DESK_FENGSHUI_REQ_HASH"
    fi
    echo ""
    echo "执行更新："
    echo "   ./scripts/docker/build_base.sh"
    echo ""
    exit 1
else
    echo "✅ requirements.txt 未变更，基础镜像可用"
    if [ -n "$DESK_FENGSHUI_REQ_HASH" ]; then
        echo "✅ 微服务依赖（风水模块）已包含"
    fi
    echo ""
fi

