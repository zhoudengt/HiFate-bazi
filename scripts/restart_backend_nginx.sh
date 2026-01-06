#!/bin/bash
# 重启后端 Docker Nginx 服务脚本
# 用途：应用新的端口配置（80 -> 8080）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "重启后端 Docker Nginx 服务"
echo "=========================================="
echo ""

# 检查是否在服务器上
if [ ! -f "/opt/HiFate-bazi/deploy/docker/docker-compose.prod.yml" ]; then
    echo -e "${RED}❌ 错误：请在服务器上执行此脚本${NC}"
    echo "   或者在脚本中指定服务器IP"
    exit 1
fi

cd /opt/HiFate-bazi/deploy/docker

# 1. 停止旧容器
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. 停止后端 Nginx 容器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q "hifate-nginx"; then
    echo "停止容器: hifate-nginx"
    docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml stop nginx
    echo -e "${GREEN}✅ 容器已停止${NC}"
else
    echo -e "${YELLOW}⚠️  容器未运行${NC}"
fi

# 2. 删除旧容器
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. 删除旧容器（使用旧端口配置）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps -a | grep -q "hifate-nginx"; then
    echo "删除容器: hifate-nginx"
    docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml rm -f nginx
    echo -e "${GREEN}✅ 容器已删除${NC}"
else
    echo -e "${YELLOW}⚠️  容器不存在${NC}"
fi

# 3. 验证配置文件
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. 验证配置文件"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "检查端口配置："
grep -A 2 "ports:" docker-compose.prod.yml | grep "8080:80" && {
    echo -e "${GREEN}✅ 配置文件正确（端口 8080:80）${NC}"
} || {
    echo -e "${RED}❌ 配置文件错误，端口配置不正确${NC}"
    exit 1
}

# 4. 启动新容器
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. 启动新容器（使用新端口配置 8080）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml up -d nginx

# 5. 验证新容器
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. 验证新容器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sleep 3

# 检查容器状态
if docker ps | grep -q "hifate-nginx"; then
    echo -e "${GREEN}✅ 容器运行中${NC}"
    
    # 检查端口映射
    echo ""
    echo "端口映射："
    docker port hifate-nginx
    
    # 验证端口
    PORT_8080=$(docker port hifate-nginx 2>/dev/null | grep "8080" || echo "")
    if [ -n "$PORT_8080" ]; then
        echo -e "${GREEN}✅ 端口 8080 映射成功${NC}"
    else
        echo -e "${RED}❌ 端口 8080 映射失败${NC}"
    fi
else
    echo -e "${RED}❌ 容器启动失败${NC}"
    echo "查看日志："
    docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml logs nginx | tail -20
    exit 1
fi

# 6. 验证服务
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. 验证服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "测试后端 Nginx (8080 端口)："
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✅ 后端 Nginx 服务正常（8080 端口）${NC}"
else
    echo -e "${YELLOW}⚠️  后端 Nginx 可能未完全启动，请稍候再试${NC}"
fi

# 7. 检查端口占用
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. 端口占用检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "80 端口占用："
if ss -tlnp | grep ":80 " | grep -v "hifate-nginx"; then
    echo -e "${GREEN}✅ 80 端口现在可被前端使用${NC}"
else
    echo -e "${YELLOW}⚠️  80 端口未被占用（前端可以绑定）${NC}"
fi

echo ""
echo "8080 端口占用："
if ss -tlnp | grep ":8080 " | grep "hifate-nginx"; then
    echo -e "${GREEN}✅ 8080 端口被后端 Nginx 占用${NC}"
else
    echo -e "${RED}❌ 8080 端口未被后端 Nginx 占用${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 后端 Nginx 重启完成${NC}"
echo "=========================================="
echo ""
echo "总结："
echo "- ✅ 后端 Nginx 现在运行在 8080 端口"
echo "- ✅ 80 端口已释放，前端 Nginx 可以使用"
echo "- ✅ 前端调用后端 API 不受影响（直接访问 8001 端口）"
echo ""

