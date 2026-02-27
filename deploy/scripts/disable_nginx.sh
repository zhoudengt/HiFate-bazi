#!/bin/bash
# 关闭 Nginx，改用单节点直连 8001
# 在 Node1 上执行：bash deploy/scripts/disable_nginx.sh

set -e

echo "关闭 Nginx..."

# 1. 系统 Nginx
if systemctl is-active --quiet nginx 2>/dev/null; then
    sudo systemctl stop nginx
    echo "✓ 已停止 systemd nginx"
fi

# 2. Docker Nginx 容器
if docker ps -q -f name=hifate-nginx 2>/dev/null | grep -q .; then
    docker stop hifate-nginx 2>/dev/null || true
    echo "✓ 已停止 hifate-nginx 容器"
fi

echo ""
echo "访问方式：http://<节点IP>:8001/"
echo "API 直连：http://<节点IP>:8001/api/v1/..."
