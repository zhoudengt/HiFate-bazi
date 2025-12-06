#!/bin/bash
# scripts/verify-permissions.sh - 权限验证脚本

echo "🔍 权限验证脚本"
echo ""

CURRENT_USER=$(whoami)
echo "当前用户: $CURRENT_USER"
echo ""

# 检查目录权限
echo "📁 目录权限检查："
if [ -d "/opt/HiFate-bazi/frontend" ]; then
    echo "  frontend/: $(ls -ld /opt/HiFate-bazi/frontend | awk '{print $1, $3, $4}')"
else
    echo "  frontend/: 目录不存在"
fi

if [ -d "/opt/HiFate-bazi/server" ]; then
    echo "  server/: $(ls -ld /opt/HiFate-bazi/server | awk '{print $1, $3, $4}')"
else
    echo "  server/: 目录不存在"
fi
echo ""

# 检查文件权限
echo "📄 文件权限检查："
if [ -f "/opt/HiFate-bazi/docker-compose.yml" ]; then
    echo "  docker-compose.yml: $(ls -l /opt/HiFate-bazi/docker-compose.yml | awk '{print $1}')"
else
    echo "  docker-compose.yml: 文件不存在"
fi

if [ -f "/opt/HiFate-bazi/.env" ]; then
    echo "  .env: $(ls -l /opt/HiFate-bazi/.env | awk '{print $1}')"
else
    echo "  .env: 文件不存在"
fi
echo ""

# 检查 ACL
echo "🔐 ACL 检查："
if [ -d "/opt/HiFate-bazi/server" ]; then
    if getfacl /opt/HiFate-bazi/server/ 2>/dev/null | grep -q frontend-user; then
        echo "  ⚠️  frontend-user 有 server 目录权限（应该被拒绝）"
        getfacl /opt/HiFate-bazi/server/ | grep frontend-user
    else
        echo "  ✅ frontend-user 无 server 目录权限（正确）"
    fi
fi

if [ -d "/opt/HiFate-bazi/frontend" ]; then
    if getfacl /opt/HiFate-bazi/frontend/ 2>/dev/null | grep -q frontend-user; then
        echo "  ✅ frontend-user 有 frontend 目录权限（正确）"
    else
        echo "  ⚠️  frontend-user 无 frontend 目录权限（应该被允许）"
    fi
fi
echo ""

# 检查 Docker 组
echo "🐳 Docker 组检查："
if groups | grep -q docker; then
    echo "  ✅ 当前用户在 docker 组"
else
    echo "  ❌ 当前用户不在 docker 组"
fi
echo ""

# 检查脚本权限
echo "📜 脚本权限检查："
if [ -f "/opt/HiFate-bazi/scripts/deploy-backend.sh" ]; then
    ls -l /opt/HiFate-bazi/scripts/deploy-backend.sh
fi
if [ -f "/opt/HiFate-bazi/scripts/deploy-frontend.sh" ]; then
    ls -l /opt/HiFate-bazi/scripts/deploy-frontend.sh
fi
echo ""

echo "✅ 权限验证完成"

