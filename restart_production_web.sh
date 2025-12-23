#!/bin/bash
# 重启生产环境Web服务（Node1和Node2）
# 使用方法：bash restart_production_web.sh

set -e

PASSWORD="Yuanqizhan@163"

echo "========================================  "
echo "⚠️  重启生产环境Web服务"
echo "========================================"
echo ""

# 重启 Node1
echo "🔄 重启 Node1 Web服务..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no root@8.210.52.217 << 'EOF'
cd /opt/HiFate-bazi/deploy/docker
source /opt/HiFate-bazi/.env
docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml --env-file /opt/HiFate-bazi/.env up -d --force-recreate web
EOF

echo "⏳ 等待 Node1 服务启动（15秒）..."
sleep 15

echo "🔍 检查 Node1 服务状态..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no root@8.210.52.217 "docker ps | grep hifate-web"

echo "✅ Node1 服务已重启"
echo ""

# 测试 Node1
echo "🧪 测试 Node1 登录功能..."
curl -f http://8.210.52.217:8001/health && echo "✅ Node1 健康检查通过" || echo "❌ Node1 健康检查失败"

echo ""
echo "========================================
echo "✅ 重启完成"
echo "请在浏览器中测试登录：http://8.210.52.217/login.html"
echo "========================================"

