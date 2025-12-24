#!/bin/bash
# 快速修复流式接口 Nginx 配置
# 在 Node1 和 Node2 上重启 Nginx 容器以应用新配置

echo "=========================================="
echo "🔧 修复流式接口 Nginx 配置"
echo "=========================================="

NODE1="8.210.52.217"
NODE2="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# 检查是否有 sshpass
if ! command -v sshpass &> /dev/null; then
    echo "❌ 需要安装 sshpass: brew install sshpass"
    exit 1
fi

# Node1
echo ""
echo "📦 在 Node1 上重启 Nginx..."
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE1 << 'EOF'
cd /opt/HiFate-bazi/deploy/docker
docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml --env-file /opt/HiFate-bazi/.env restart nginx
echo "✅ Node1 Nginx 已重启"
EOF

# Node2
echo ""
echo "📦 在 Node2 上重启 Nginx..."
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE2 << 'EOF'
cd /opt/HiFate-bazi/deploy/docker
docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml --env-file /opt/HiFate-bazi/.env restart nginx
echo "✅ Node2 Nginx 已重启"
EOF

echo ""
echo "=========================================="
echo "✅ Nginx 配置已更新"
echo "=========================================="
echo ""
echo "📋 验证步骤："
echo "1. 测试五行占比流式分析是否实时输出"
echo "2. 测试喜神忌神流式分析是否实时输出"
echo "3. 验证结果不再重复输出"
echo ""

