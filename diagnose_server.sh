#!/bin/bash
# 服务器诊断脚本
# 使用方法：在服务器上运行：bash diagnose_server.sh

echo "========================================"
echo "🔍 HiFate 服务器综合诊断"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

PROJECT_DIR="/opt/HiFate-bazi"

# 1. 检查容器状态
echo ""
echo "【1/10】检查容器状态..."
echo "----------------------------------------"
if command -v docker &> /dev/null; then
    docker ps -a | grep hifate || echo "❌ 未发现 HiFate 容器"
    echo ""
    echo "运行中的容器:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep hifate || echo "  ❌ 无运行中的容器"
else
    echo "❌ Docker 未安装或不可用"
fi

# 2. 检查服务端口
echo ""
echo "【2/10】检查端口占用..."
echo "----------------------------------------"
for port in 8001 80 443 3306 6379 9001 9002 9003 9004 9005 9006 9007 9008 9009 9010; do
    if netstat -tuln 2>/dev/null | grep -q ":${port} " || ss -tuln 2>/dev/null | grep -q ":${port} "; then
        echo "  ✅ 端口 ${port} 正在监听"
    else
        echo "  ❌ 端口 ${port} 未监听"
    fi
done

# 3. 检查健康检查端点
echo ""
echo "【3/10】检查健康检查端点..."
echo "----------------------------------------"
if curl -sf --connect-timeout 5 http://localhost:8001/health > /dev/null 2>&1; then
    echo "  ✅ Web 服务健康检查通过 (8001)"
    curl -s http://localhost:8001/health | head -3
else
    echo "  ❌ Web 服务健康检查失败 (8001)"
    echo "     尝试获取错误信息..."
    curl -v http://localhost:8001/health 2>&1 | head -10
fi

if curl -sf --connect-timeout 5 http://localhost/health > /dev/null 2>&1; then
    echo "  ✅ Nginx 健康检查通过 (80)"
    curl -s http://localhost/health | head -3
else
    echo "  ❌ Nginx 健康检查失败 (80)"
    echo "     尝试获取错误信息..."
    curl -v http://localhost/health 2>&1 | head -10
fi

# 4. 检查数据库连接
echo ""
echo "【4/10】检查数据库服务..."
echo "----------------------------------------"
if docker ps | grep -q hifate-mysql; then
    if docker exec hifate-mysql-master mysqladmin ping -uroot -p"${MYSQL_PASSWORD:?MYSQL_PASSWORD required}" 2>/dev/null | grep -q "mysqld is alive"; then
        echo "  ✅ MySQL 主库正常"
    else
        echo "  ❌ MySQL 主库无响应"
        docker logs --tail 5 hifate-mysql-master 2>/dev/null | tail -3
    fi
else
    echo "  ⚠️  MySQL 容器未运行"
fi

# 5. 检查 Redis 连接
echo ""
echo "【5/10】检查 Redis 服务..."
echo "----------------------------------------"
if docker ps | grep -q hifate-redis; then
    if docker exec hifate-redis-master redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo "  ✅ Redis 主库正常"
    else
        echo "  ❌ Redis 主库无响应"
        docker logs --tail 5 hifate-redis-master 2>/dev/null | tail -3
    fi
else
    echo "  ⚠️  Redis 容器未运行"
fi

# 6. 检查磁盘空间
echo ""
echo "【6/10】检查磁盘空间..."
echo "----------------------------------------"
df -h | grep -E "^/dev|Filesystem" | head -5
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "  ⚠️  磁盘使用率: ${DISK_USAGE}% (超过90%，严重)"
elif [ "$DISK_USAGE" -gt 80 ]; then
    echo "  ⚠️  磁盘使用率: ${DISK_USAGE}% (超过80%，警告)"
else
    echo "  ✅ 磁盘使用率: ${DISK_USAGE}%"
fi

# 7. 检查内存使用
echo ""
echo "【7/10】检查内存使用..."
echo "----------------------------------------"
free -h | head -2
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "  ⚠️  内存使用率: ${MEM_USAGE}% (超过90%，可能 OOM)"
elif [ "$MEM_USAGE" -gt 80 ]; then
    echo "  ⚠️  内存使用率: ${MEM_USAGE}% (超过80%，警告)"
else
    echo "  ✅ 内存使用率: ${MEM_USAGE}%"
fi

# 8. 检查 Docker 资源
echo ""
echo "【8/10】检查 Docker 资源..."
echo "----------------------------------------"
if command -v docker &> /dev/null; then
    docker system df 2>/dev/null || echo "  ⚠️  无法获取 Docker 资源信息"
fi

# 9. 检查服务日志（最近错误）
echo ""
echo "【9/10】检查服务日志（最近错误）..."
echo "----------------------------------------"
if docker ps | grep -q hifate-web; then
    echo "  Web 服务日志（最后10行，包含错误）:"
    docker logs --tail 50 hifate-web 2>&1 | grep -i "error\|exception\|failed\|refused\|timeout\|killed\|oom" | tail -5 || echo "    无错误日志"
else
    echo "  ⚠️  Web 容器未运行，无法查看日志"
fi

if docker ps | grep -q hifate-nginx; then
    echo "  Nginx 日志（最后5行）:"
    docker logs --tail 10 hifate-nginx 2>&1 | tail -5
else
    echo "  ⚠️  Nginx 容器未运行"
fi

# 10. 检查 Nginx 配置
echo ""
echo "【10/10】检查 Nginx 配置..."
echo "----------------------------------------"
if docker ps | grep -q hifate-nginx; then
    echo "  Nginx upstream 配置:"
    docker exec hifate-nginx cat /etc/nginx/conf.d/hifate.conf 2>/dev/null | grep -A 5 "upstream web_backend" || echo "    无法读取配置"
    
    # 检查是否有占位符
    if docker exec hifate-nginx cat /etc/nginx/conf.d/hifate.conf 2>/dev/null | grep -q "NODE1_IP\|NODE2_IP"; then
        echo "  ❌ 发现未替换的占位符（NODE1_IP 或 NODE2_IP）"
    else
        echo "  ✅ Nginx 配置正常（无占位符）"
    fi
else
    echo "  ⚠️  Nginx 容器未运行，无法检查配置"
fi

# 11. 检查服务进程
echo ""
echo "【11/11】检查服务进程..."
echo "----------------------------------------"
if docker ps | grep -q hifate-web; then
    echo "  Web 容器内进程:"
    docker exec hifate-web ps aux 2>/dev/null | grep -E "python|uvicorn" | head -5 || echo "    无法获取进程信息"
else
    echo "  ⚠️  Web 容器未运行"
fi

# 总结
echo ""
echo "========================================"
echo "📊 诊断完成"
echo "========================================"
echo ""
echo "💡 快速修复建议:"
echo "  1. 如果容器未运行: cd ${PROJECT_DIR}/deploy/docker && docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml up -d"
echo "  2. 如果服务崩溃: docker restart hifate-web hifate-nginx"
echo "  3. 如果 Nginx 配置有占位符: 运行部署脚本替换配置"
echo "  4. 如果磁盘空间不足: docker system prune -af"
echo "  5. 查看详细日志: docker logs --tail 100 hifate-web"
echo ""

