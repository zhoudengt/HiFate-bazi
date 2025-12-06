#!/bin/bash
# scripts/deploy-backend.sh - 后端用户部署脚本（完整权限）

set -e

echo "🚀 后端部署脚本（完整权限）"
echo ""

# 检查用户
if [ "$USER" != "backend-user" ]; then
    echo "❌ 此脚本仅限 backend-user 用户使用"
    echo "   当前用户: $USER"
    exit 1
fi

# 进入项目目录
cd /opt/HiFate-bazi

# 0. 检查环境变量配置
echo "🔍 [0/6] 检查环境变量配置..."
if [ ! -f .env ]; then
    echo "   ⚠️  .env 文件不存在，从模板创建..."
    if [ -f env.template ]; then
        cp env.template .env
        echo "   ✅ 已创建 .env 文件"
        echo "   ⚠️  请编辑 .env 文件，设置以下关键变量："
        echo "      - MYSQL_ROOT_PASSWORD"
        echo "      - REDIS_PASSWORD"
        echo "      - SECRET_KEY"
        echo ""
        read -p "   是否现在编辑 .env 文件？[y/N]: " edit_env
        if [[ $edit_env == "y" || $edit_env == "Y" ]]; then
            ${EDITOR:-vim} .env
        else
            echo "   ⚠️  请稍后手动编辑 .env 文件，否则部署可能失败"
        fi
    else
        echo "   ❌ env.template 文件不存在，无法创建 .env"
        exit 1
    fi
fi

# 加载环境变量
set -a
source .env 2>/dev/null || true
set +a

# 检查关键环境变量
MISSING_VARS=()
if [ -z "$MYSQL_ROOT_PASSWORD" ] || [ "$MYSQL_ROOT_PASSWORD" == "your_strong_password_here" ]; then
    MISSING_VARS+=("MYSQL_ROOT_PASSWORD")
fi
if [ -z "$REDIS_PASSWORD" ] || [ "$REDIS_PASSWORD" == "your_redis_password_here" ]; then
    MISSING_VARS+=("REDIS_PASSWORD")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "   ❌ 以下环境变量未设置或使用默认值："
    for var in "${MISSING_VARS[@]}"; do
        echo "      - $var"
    done
    echo "   请编辑 .env 文件并设置这些变量"
    exit 1
fi
echo "   ✅ 环境变量配置检查通过"

# 1. 拉取最新代码
echo ""
echo "📥 [1/6] 更新代码..."
git pull origin master || {
    echo "❌ 代码更新失败"
    exit 1
}
echo "   ✅ 代码更新完成"

# 2. 检查并构建基础镜像（如果不存在）
echo ""
echo "🐳 [2/6] 检查基础镜像..."
if ! docker images hifate-base:latest --format "{{.Repository}}" | grep -q hifate-base; then
    echo "   ⚠️  基础镜像不存在，开始构建（约5-10分钟）..."
    docker build \
        --platform linux/amd64 \
        -f Dockerfile.base \
        -t hifate-base:latest \
        -t hifate-base:$(date +%Y%m%d) \
        . || {
        echo "   ❌ 基础镜像构建失败"
        exit 1
    }
    echo "   ✅ 基础镜像构建完成"
else
    echo "   ✅ 基础镜像已存在"
fi

# 3. 停止现有服务（如果存在）
echo ""
echo "🛑 [3/6] 停止现有服务..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true
echo "   ✅ 现有服务已停止"

# 4. 启动所有服务（包括 MySQL 和 Redis）
echo ""
echo "🔄 [4/6] 启动所有服务..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build || {
    echo "❌ 服务启动失败"
    echo "📋 查看错误日志："
    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=50
    exit 1
}
echo "   ✅ 服务启动命令执行完成"

# 5. 等待 MySQL 和 Redis 启动
echo ""
echo "⏳ [5/6] 等待 MySQL 和 Redis 启动..."
MAX_WAIT=60
WAIT_TIME=0
MYSQL_READY=false
REDIS_READY=false

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    # 检查 MySQL
    if ! $MYSQL_READY; then
        if docker exec hifate-mysql mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD}" --silent 2>/dev/null; then
            MYSQL_READY=true
            echo "   ✅ MySQL 已就绪"
        fi
    fi
    
    # 检查 Redis
    if ! $REDIS_READY; then
        if docker exec hifate-redis redis-cli -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; then
            REDIS_READY=true
            echo "   ✅ Redis 已就绪"
        fi
    fi
    
    if $MYSQL_READY && $REDIS_READY; then
        break
    fi
    
    sleep 2
    WAIT_TIME=$((WAIT_TIME + 2))
    if [ $((WAIT_TIME % 10)) -eq 0 ]; then
        echo "   ⏳ 等待中... (${WAIT_TIME}/${MAX_WAIT}秒)"
    fi
done

if ! $MYSQL_READY; then
    echo "   ❌ MySQL 启动超时"
    echo "   📋 MySQL 日志："
    docker logs hifate-mysql --tail=30
    exit 1
fi

if ! $REDIS_READY; then
    echo "   ⚠️  Redis 启动超时（继续部署，但可能影响功能）"
fi

# 6. 健康检查
echo ""
echo "🏥 [6/6] Web 服务健康检查..."
sleep 5
MAX_RETRIES=10
RETRY_COUNT=0
HEALTH_CHECK_PASSED=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost:8001/api/v1/health > /dev/null 2>&1; then
        HEALTH_CHECK_PASSED=true
        echo "   ✅ Web 服务健康检查通过"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "   ⏳ 健康检查失败，重试 $RETRY_COUNT/$MAX_RETRIES..."
        sleep 5
    fi
done

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    echo "   ❌ Web 服务健康检查失败"
    echo "   📋 查看服务日志："
    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs web --tail=50
    echo ""
    echo "   📋 查看所有服务状态："
    docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 后端部署完成"
echo "=========================================="
echo ""
echo "📊 服务状态："
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
echo ""
echo "🔗 访问地址："
echo "   Web API: http://localhost:8001"
echo "   健康检查: http://localhost:8001/api/v1/health"
echo ""

