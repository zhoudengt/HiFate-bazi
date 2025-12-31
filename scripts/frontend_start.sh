#!/bin/bash
# 前端容器启动脚本
# 确保每次重启都能正常启动
# 使用：bash /opt/hifate-frontend/start.sh

set -e

FRONTEND_DIR="/opt/hifate-frontend"
COMPOSE_FILE="$FRONTEND_DIR/docker-compose.yml"

# 检查用户
if [ "$USER" != "frontend-user" ]; then
    echo "❌ 此脚本必须由 frontend-user 执行"
    echo "   当前用户: $USER"
    exit 1
fi

# 检查目录
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ 目录不存在: $FRONTEND_DIR"
    exit 1
fi

cd "$FRONTEND_DIR"

# 检查配置文件
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ 配置文件不存在: $COMPOSE_FILE"
    exit 1
fi

echo "=========================================="
echo "启动前端容器"
echo "=========================================="
echo ""

# 1. 停止现有容器
echo "1. 停止现有容器..."
docker-compose down 2>/dev/null || true
echo "   ✅ 已停止"

# 2. 验证配置
echo ""
echo "2. 验证配置..."
if docker-compose config > /dev/null 2>&1; then
    echo "   ✅ 配置验证通过"
else
    echo "   ❌ 配置验证失败"
    exit 1
fi

# 3. 启动容器
echo ""
echo "3. 启动容器..."
docker-compose up -d
echo "   ✅ 容器已启动"

# 4. 等待容器启动
echo ""
echo "4. 等待容器启动..."
sleep 10

# 5. 检查容器状态
echo ""
echo "5. 检查容器状态..."
FAILED_CONTAINERS=$(docker-compose ps 2>/dev/null | grep -E "Exit|Restarting" | wc -l || echo "0")

if [ "$FAILED_CONTAINERS" -gt 0 ]; then
    echo "   ⚠️  有容器启动失败，查看详情："
    docker-compose ps
    echo ""
    echo "   查看日志："
    docker-compose logs --tail=50
    exit 1
else
    echo "   ✅ 所有容器运行正常"
fi

# 6. 显示容器状态
echo ""
echo "=========================================="
echo "容器状态"
echo "=========================================="
docker-compose ps

# 7. 显示内存使用情况
echo ""
echo "=========================================="
echo "内存使用情况"
echo "=========================================="
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}" | head -10

echo ""
echo "✅ 启动完成"

