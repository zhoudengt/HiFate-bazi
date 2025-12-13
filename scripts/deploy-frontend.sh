#!/bin/bash
# scripts/deploy-frontend.sh - 前端用户部署脚本（仅前端权限）

set -e

echo "🚀 前端部署脚本（仅限前端用户使用）"
echo ""

# 检查用户
if [ "$USER" != "frontend-user" ]; then
    echo "❌ 此脚本仅限 frontend-user 用户使用"
    echo "   当前用户: $USER"
    exit 1
fi

# 检查目录权限
if [ ! -w "/opt/HiFate-bazi/local_frontend" ]; then
    echo "❌ 没有 local_frontend 目录的写权限"
    exit 1
fi

# 进入项目目录
cd /opt/HiFate-bazi

# 1. 拉取最新代码（仅本地前端目录）
echo "📥 [1/3] 更新本地前端代码..."
cd local_frontend/
git pull origin master -- local_frontend/ 2>/dev/null || {
    echo "   ⚠️  使用 git pull 更新整个仓库（前端用户权限受限）"
    cd ..
    git pull origin master
}
echo "   ✅ 前端代码更新完成"

# 2. 构建前端（如果有构建步骤）
echo ""
echo "🔨 [2/3] 构建前端..."
# 如果有 npm 构建步骤，在这里执行
# cd /opt/HiFate-bazi/frontend
# npm install
# npm run build
echo "   ✅ 前端构建完成（跳过，如需构建请取消注释）"

# 3. 重启前端服务
echo ""
echo "🔄 [3/3] 重启前端服务..."
cd /opt/HiFate-bazi
docker compose -f docker-compose.frontend.yml up -d --build nginx-frontend || {
    echo "❌ 前端服务启动失败"
    exit 1
}
echo "   ✅ 前端服务启动完成"

# 4. 健康检查
echo ""
echo "🏥 健康检查..."
sleep 5
if curl -f -s http://localhost/health > /dev/null 2>&1; then
    echo "   ✅ 前端服务健康"
else
    echo "   ⚠️  前端服务健康检查失败（可能 Nginx 未配置 /health 端点）"
fi

echo ""
echo "=========================================="
echo "✅ 前端部署完成"
echo "=========================================="
echo ""
echo "📊 前端服务状态："
docker compose -f docker-compose.frontend.yml ps
echo ""

