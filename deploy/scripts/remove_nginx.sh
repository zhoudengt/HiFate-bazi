#!/bin/bash
# 移除 Nginx 容器脚本
# 用途：彻底移除后端 Nginx，让前端直接访问 8001 端口

set -e

echo "========================================="
echo "移除后端 Nginx 容器"
echo "========================================="

# 检查是否有 Nginx 容器
if docker ps -a --filter "name=nginx" --format "{{.Names}}" | grep -q nginx; then
    echo "发现 Nginx 容器，准备停止并移除..."
    
    # 停止所有 Nginx 容器
    docker ps -a --filter "name=nginx" --format "{{.Names}}" | while read container; do
        echo "停止容器: $container"
        docker stop "$container" || true
        echo "移除容器: $container"
        docker rm "$container" || true
    done
    
    echo "✅ Nginx 容器已移除"
else
    echo "⚠️  未发现 Nginx 容器"
fi

# 检查 80 端口是否还被占用
if netstat -tuln | grep -q ":80 "; then
    echo ""
    echo "⚠️  警告：80 端口仍被占用"
    echo "占用进程："
    netstat -tulnp | grep ":80 "
    echo ""
    echo "如果是 Nginx 进程，请手动停止："
    echo "  sudo systemctl stop nginx"
    echo "  或"
    echo "  sudo nginx -s stop"
else
    echo "✅ 80 端口已释放"
fi

echo ""
echo "========================================="
echo "移除完成"
echo "========================================="
echo ""
echo "后续操作："
echo "1. 前端团队需要将域名指向 8001 端口"
echo "   或者配置他们的 Nginx 代理到 8001"
echo ""
echo "2. 测试后端 API："
echo "   curl http://8.210.52.217:8001/health"
echo "   curl -X POST http://8.210.52.217:8001/api/v1/bazi/pan/display \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"solar_date\":\"1990-01-01\",\"solar_time\":\"12:00\",\"gender\":\"male\"}'"
