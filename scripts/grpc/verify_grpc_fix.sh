#!/bin/bash
# 验证 gRPC 代码修复
# 检查所有环境代码是否一致

echo "========================================"
echo "🔍 验证 gRPC 代码修复状态"
echo "========================================"

PROJECT_DIR="${1:-/opt/HiFate-bazi}"

# 检查本地文件
echo ""
echo "【1/3】检查本地代码..."
if [ -d "${PROJECT_DIR}/proto/generated" ]; then
    count=$(grep -r "add_registered_method_handlers" ${PROJECT_DIR}/proto/generated/*_pb2_grpc.py 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -eq 0 ]; then
        echo "  ✅ 本地代码已修复（0 个问题文件）"
    else
        echo "  ❌ 本地代码仍有 $count 个文件包含问题代码"
    fi
else
    echo "  ⚠️  本地 proto/generated 目录不存在"
fi

# 检查容器内代码
echo ""
echo "【2/3】检查容器内代码..."
if docker ps | grep -q hifate-bazi-core; then
    count=$(docker exec hifate-bazi-core grep -r "add_registered_method_handlers" /app/proto/generated/*_pb2_grpc.py 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -eq 0 ]; then
        echo "  ✅ 容器内代码已修复（0 个问题文件）"
    else
        echo "  ❌ 容器内代码仍有 $count 个文件包含问题代码"
    fi
else
    echo "  ⚠️  容器未运行，无法检查"
fi

# 检查微服务状态
echo ""
echo "【3/3】检查微服务状态..."
running=$(docker ps --format "{{.Names}}" | grep -E "hifate-bazi|hifate-rule|hifate-intent|hifate-payment" | grep -v "Restarting" | wc -l | tr -d ' ')
restarting=$(docker ps --format "{{.Names}}\t{{.Status}}" | grep -E "hifate-bazi|hifate-rule|hifate-intent|hifate-payment" | grep "Restarting" | wc -l | tr -d ' ')

echo "  运行中: $running 个微服务"
echo "  重启中: $restarting 个微服务"

if [ "$restarting" -eq 0 ]; then
    echo "  ✅ 所有微服务正常运行"
else
    echo "  ⚠️  有 $restarting 个微服务仍在重启，请检查日志"
fi

echo ""
echo "========================================"

