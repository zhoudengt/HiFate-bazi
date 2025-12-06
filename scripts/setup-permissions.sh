#!/bin/bash
# scripts/setup-permissions.sh - 初始化权限配置

set -e

echo "🔧 初始化用户权限配置..."
echo ""

# 1. 创建用户和组
echo "📝 [1/6] 创建用户和组..."
sudo groupadd -f backend-group
sudo groupadd -f frontend-group
sudo useradd -m -g backend-group -s /bin/bash backend-user 2>/dev/null || echo "   backend-user 已存在"
sudo useradd -m -g frontend-group -s /bin/bash frontend-user 2>/dev/null || echo "   frontend-user 已存在"
echo "   ✅ 用户和组创建完成"

# 2. 设置目录权限
echo ""
echo "📁 [2/6] 设置目录权限..."
cd /opt/HiFate-bazi

# 项目根目录：后端用户可读写
sudo chown -R backend-user:backend-group /opt/HiFate-bazi
sudo chmod 750 /opt/HiFate-bazi
echo "   ✅ 项目根目录权限设置完成"

# 前端目录：前端用户可读写
sudo chown -R frontend-user:frontend-group frontend/ 2>/dev/null || echo "   ⚠️  frontend 目录不存在，跳过"
sudo chmod 755 frontend/ 2>/dev/null || true
echo "   ✅ 前端目录权限设置完成"

# 后端目录：仅后端用户可访问
sudo chmod 750 server/ services/ src/ 2>/dev/null || echo "   ⚠️  部分后端目录不存在，跳过"
sudo setfacl -m u:frontend-user:--- server/ 2>/dev/null || true
sudo setfacl -m u:frontend-user:--- services/ 2>/dev/null || true
sudo setfacl -m u:frontend-user:--- src/ 2>/dev/null || true
echo "   ✅ 后端目录权限设置完成"

# 3. 创建前端配置目录
echo ""
echo "📁 [3/6] 创建前端配置目录..."
sudo mkdir -p /opt/HiFate-bazi/frontend-config
sudo chown -R frontend-user:frontend-group /opt/HiFate-bazi/frontend-config
sudo chmod 755 /opt/HiFate-bazi/frontend-config
echo "   ✅ 前端配置目录创建完成"

# 4. 配置文件权限
echo ""
echo "📄 [4/6] 设置配置文件权限..."
sudo chmod 640 docker-compose.yml .env 2>/dev/null || echo "   ⚠️  部分配置文件不存在，跳过"
sudo setfacl -m u:frontend-user:r-- docker-compose.yml 2>/dev/null || true
sudo setfacl -m u:frontend-user:r-- .env 2>/dev/null || true
echo "   ✅ 配置文件权限设置完成"

# 5. 设置脚本权限
echo ""
echo "📜 [5/6] 设置脚本权限..."
sudo chmod 755 scripts/deploy-backend.sh 2>/dev/null || echo "   ⚠️  deploy-backend.sh 不存在，跳过"
sudo chmod 755 scripts/deploy-frontend.sh 2>/dev/null || echo "   ⚠️  deploy-frontend.sh 不存在，跳过"
sudo chown backend-user:backend-group scripts/deploy-backend.sh 2>/dev/null || true
sudo chown frontend-user:frontend-group scripts/deploy-frontend.sh 2>/dev/null || true
echo "   ✅ 脚本权限设置完成"

# 6. 添加 Docker 组
echo ""
echo "🐳 [6/6] 添加 Docker 组权限..."
sudo usermod -aG docker backend-user
sudo usermod -aG docker frontend-user
echo "   ✅ Docker 组权限设置完成"

echo ""
echo "=========================================="
echo "✅ 权限配置完成"
echo "=========================================="
echo ""
echo "📋 用户信息："
echo "  后端用户: backend-user (完整权限)"
echo "  前端用户: frontend-user (仅前端权限)"
echo ""
echo "🔐 请为两个用户设置密码："
echo "  sudo passwd backend-user"
echo "  sudo passwd frontend-user"
echo ""

