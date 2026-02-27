#!/bin/bash
# 关闭 Nginx，Web 接管 80 端口
# 在 Node1 上执行：cd /opt/HiFate-bazi && bash deploy/scripts/disable_nginx.sh

set -e

PROJECT_DIR="${1:-/opt/HiFate-bazi}"
cd "$PROJECT_DIR"

echo "1. 关闭 Nginx..."

# 系统 Nginx
if systemctl is-active --quiet nginx 2>/dev/null; then
    systemctl stop nginx
    echo "   ✓ 已停止 systemd nginx"
fi

# Docker Nginx 容器
if docker ps -q -f name=hifate-nginx 2>/dev/null | grep -q .; then
    docker stop hifate-nginx 2>/dev/null || true
    echo "   ✓ 已停止 hifate-nginx"
fi

echo ""
echo "2. 重启 Web 容器（占用 80 端口）..."
cd "$PROJECT_DIR"
[ -f .env ] && set -a && . .env && set +a
docker compose -f deploy/docker/docker-compose.prod.yml -f deploy/docker/docker-compose.node1.yml up -d --no-deps web

echo ""
echo "3. 等待就绪..."
sleep 5
curl -sf http://localhost:80/health > /dev/null && echo "   ✓ 80 端口正常" || echo "   ⚠ 请检查: curl http://localhost:80/health"

echo ""
echo "访问：http://<节点IP>/ 或 http://<节点IP>:8001/"
