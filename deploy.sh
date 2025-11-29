#!/bin/bash
# ============================================
# HiFate-bazi 一键部署脚本
# 基于 Gitee（码云）+ 阿里云 ECS + Docker
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# 配置区域
# ============================================
SERVER="root@123.57.216.15"                     # 阿里云 ECS 地址
SERVER_PORT="22"                                 # SSH 端口
REMOTE_PATH="/opt/HiFate-bazi"                  # 服务器项目路径
GITEE_REPO="https://gitee.com/zhoudengtang/hifate-prod.git"  # Gitee 仓库地址
BRANCH="master"                                  # 分支名
HEALTH_URL="http://localhost:8001/api/v1/health"
HEALTH_TIMEOUT=120                               # 健康检查超时（秒）

# SSH 命令简化
SSH_CMD="ssh -p $SERVER_PORT $SERVER"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   HiFate-bazi 部署工具${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "服务器: ${BLUE}$SERVER${NC}"
echo -e "仓库:   ${BLUE}$GITEE_REPO${NC}"
echo ""

# 选择操作
echo "请选择操作："
echo ""
echo -e "  ${GREEN}1) 完整部署（推荐）${NC}"
echo "     本地提交 → 推送 Gitee → 服务器 pull → Docker 重启"
echo ""
echo "  2) 仅推送到 Gitee（不部署）"
echo "  3) 仅更新服务器（服务器 pull + 重启）"
echo "  4) 重启服务器 Docker 服务"
echo "  5) 查看服务器日志"
echo "  6) 查看服务器状态"
echo ""
echo -e "  ${YELLOW}7) 首次部署：初始化服务器${NC}"
echo ""
read -p "选择 [1-7]: " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}=== 完整部署流程 ===${NC}"
        
        # 检查是否有未提交的更改
        if [ -n "$(git status --porcelain)" ]; then
            echo ""
            echo -e "${YELLOW}检测到未提交的更改：${NC}"
            git status --short
            echo ""
            read -p "是否提交这些更改？[y/N]: " commit_confirm
            if [[ $commit_confirm == "y" || $commit_confirm == "Y" ]]; then
                read -p "请输入提交信息: " commit_msg
                git add .
                git commit -m "$commit_msg"
            else
                echo -e "${YELLOW}跳过提交，使用已提交的代码${NC}"
            fi
        fi
        
        # 1. 推送到 Gitee
        echo ""
        echo "📤 [1/4] 推送代码到 Gitee..."
        git push gitee $BRANCH 2>&1 || {
            echo -e "${RED}推送失败！请检查 Gitee 配置${NC}"
            exit 1
        }
        echo -e "${GREEN}✅ 推送成功${NC}"
        
        # 2. 服务器部署
        echo ""
        echo "🚀 [2/4] 服务器拉取代码..."
        $SSH_CMD << 'ENDSSH'
cd /opt/HiFate-bazi

# 保存本地配置
git stash --include-untracked 2>/dev/null || true

# 拉取最新代码
echo "   拉取最新代码..."
git pull origin master

# 恢复本地配置
git stash pop 2>/dev/null || true

echo "✅ 代码更新完成"
ENDSSH
        
        echo ""
        echo "🐳 [3/4] Docker 零停机重启..."
        $SSH_CMD << 'ENDSSH'
cd /opt/HiFate-bazi

# 检查并构建基础镜像（如果不存在）
echo "   检查基础镜像..."
if ! docker images hifate-base:latest --format "{{.Repository}}" | grep -q hifate-base; then
    echo "   ⚠️  基础镜像不存在，开始构建（约5-10分钟）..."
    echo "   正在构建基础镜像，请耐心等待..."
    docker build \
        --platform linux/amd64 \
        -f Dockerfile.base \
        -t hifate-base:latest \
        -t hifate-base:$(date +%Y%m%d) \
        . || {
        echo "   ❌ 基础镜像构建失败，请检查错误信息"
        exit 1
    }
    echo "   ✅ 基础镜像构建完成"
else
    echo "   ✅ 基础镜像已存在"
fi

# 使用 docker compose（新版命令）
if command -v docker &> /dev/null; then
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
else
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
fi

echo "✅ 服务重启完成"
ENDSSH
        
        echo ""
        echo "🏥 [4/4] 健康检查（最多 ${HEALTH_TIMEOUT} 秒）..."
        $SSH_CMD << ENDSSH
for i in \$(seq 1 $HEALTH_TIMEOUT); do
    if curl -sf http://localhost:8001/api/v1/health > /dev/null 2>&1; then
        echo "✅ 服务健康！耗时 \${i} 秒"
        exit 0
    fi
    sleep 1
    if [ \$((i % 15)) -eq 0 ]; then
        echo "   等待中... \${i}/${HEALTH_TIMEOUT}"
    fi
done
echo "⚠️ 健康检查超时"
exit 1
ENDSSH
        
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}✅ 部署成功！${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "访问地址: ${BLUE}http://123.57.216.15:8001${NC}"
        ;;
    
    2)
        echo ""
        echo -e "${YELLOW}=== 推送到 Gitee ===${NC}"
        
        # 检查未提交更改
        if [ -n "$(git status --porcelain)" ]; then
            echo "检测到未提交的更改："
            git status --short
            echo ""
            read -p "是否提交？[y/N]: " confirm
            if [[ $confirm == "y" || $confirm == "Y" ]]; then
                read -p "提交信息: " msg
                git add .
                git commit -m "$msg"
            fi
        fi
        
        git push gitee $BRANCH
        echo -e "\n${GREEN}✅ 已推送到 Gitee${NC}"
        ;;
    
    3)
        echo ""
        echo -e "${YELLOW}=== 服务器更新 ===${NC}"
        $SSH_CMD << 'ENDSSH'
cd /opt/HiFate-bazi

echo "📂 拉取代码..."
git stash --include-untracked 2>/dev/null || true
git pull origin master
git stash pop 2>/dev/null || true

# 检查并构建基础镜像（如果不存在）
echo "🐳 检查基础镜像..."
if ! docker images hifate-base:latest --format "{{.Repository}}" | grep -q hifate-base; then
    echo "   ⚠️  基础镜像不存在，开始构建（约5-10分钟）..."
    echo "   正在构建基础镜像，请耐心等待..."
    docker build \
        --platform linux/amd64 \
        -f Dockerfile.base \
        -t hifate-base:latest \
        -t hifate-base:$(date +%Y%m%d) \
        . || {
        echo "   ❌ 基础镜像构建失败，请检查错误信息"
        exit 1
    }
    echo "   ✅ 基础镜像构建完成"
else
    echo "   ✅ 基础镜像已存在"
fi

echo "🐳 重启服务..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "✅ 更新完成"
ENDSSH
        ;;
    
    4)
        echo ""
        echo -e "${YELLOW}=== 重启服务 ===${NC}"
        $SSH_CMD << 'ENDSSH'
cd /opt/HiFate-bazi
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart
echo "✅ 服务已重启"
ENDSSH
        ;;
    
    5)
        echo ""
        echo -e "${YELLOW}=== 服务器日志（Ctrl+C 退出）===${NC}"
        $SSH_CMD "cd /opt/HiFate-bazi && docker compose logs -f --tail=100"
        ;;
    
    6)
        echo ""
        echo -e "${YELLOW}=== 服务器状态 ===${NC}"
        $SSH_CMD << 'ENDSSH'
cd /opt/HiFate-bazi

echo "📦 容器状态："
docker compose ps
echo ""

echo "📊 资源使用："
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo ""

echo "💾 磁盘使用："
df -h / | tail -1
echo ""

echo "🏥 健康检查："
if curl -sf http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo "✅ 服务健康"
else
    echo "❌ 服务异常"
fi
ENDSSH
        ;;
    
    7)
        echo ""
        echo -e "${YELLOW}=== 首次部署：服务器初始化 ===${NC}"
        echo ""
        echo "将执行以下操作："
        echo "  1. 安装 Docker 和 Docker Compose"
        echo "  2. 配置 Docker 国内镜像加速"
        echo "  3. 克隆代码到 $REMOTE_PATH"
        echo "  4. 创建环境配置文件"
        echo "  5. 启动服务"
        echo ""
        read -p "确认初始化服务器？[y/N]: " confirm
        
        if [[ $confirm == "y" || $confirm == "Y" ]]; then
            echo ""
            echo "🔧 开始初始化服务器..."
            $SSH_CMD << 'ENDSSH'
set -e

echo ""
echo "=========================================="
echo "   HiFate-bazi 服务器初始化"
echo "=========================================="
echo ""

# 1. 安装 Docker
echo "[1/5] 检查 Docker..."
if ! command -v docker &> /dev/null; then
    echo "   安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "   ✅ Docker 安装完成"
else
    echo "   ✅ Docker 已安装"
fi

# 2. 安装 Docker Compose 插件
echo "[2/5] 检查 Docker Compose..."
if ! docker compose version &> /dev/null 2>&1; then
    echo "   安装 Docker Compose 插件..."
    apt-get update -qq
    apt-get install -y docker-compose-plugin
    echo "   ✅ Docker Compose 安装完成"
else
    echo "   ✅ Docker Compose 已安装"
fi

# 3. 配置 Docker 镜像加速
echo "[3/5] 配置镜像加速..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
    "registry-mirrors": [
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    }
}
EOF
systemctl daemon-reload
systemctl restart docker
echo "   ✅ 镜像加速配置完成"

# 4. 克隆代码
echo "[4/5] 克隆代码..."
mkdir -p /opt
if [ -d "/opt/HiFate-bazi/.git" ]; then
    echo "   项目已存在，更新代码..."
    cd /opt/HiFate-bazi
    git pull origin master
else
    cd /opt
    git clone https://gitee.com/zhoudengtang/hifate-prod.git HiFate-bazi
fi
echo "   ✅ 代码准备完成"

# 5. 创建环境配置
echo "[5/5] 创建环境配置..."
if [ ! -f "/opt/HiFate-bazi/.env" ]; then
    cat > /opt/HiFate-bazi/.env << 'ENVEOF'
# === HiFate-bazi 生产环境配置 ===
APP_ENV=production
DEBUG=False

# MySQL 配置
MYSQL_ROOT_PASSWORD=HiFate_Prod_2024!
MYSQL_USER=root
MYSQL_DATABASE=bazi_system

# Redis 配置
REDIS_PASSWORD=HiFate_Redis_2024!

# Web 端口
WEB_PORT=8001

# 密钥
SECRET_KEY=hifate-production-secret-key-2024

# 日志级别
LOG_LEVEL=WARNING
ENVEOF
    chmod 600 /opt/HiFate-bazi/.env
    echo "   ✅ 环境配置创建完成"
    echo "   ⚠️  请稍后修改密码: vim /opt/HiFate-bazi/.env"
else
    echo "   ✅ 环境配置已存在"
fi

echo ""
echo "=========================================="
echo "🚀 启动服务..."
echo "=========================================="
cd /opt/HiFate-bazi

# 检查并构建基础镜像（如果不存在）
echo "检查基础镜像..."
if ! docker images hifate-base:latest --format "{{.Repository}}" | grep -q hifate-base; then
    echo "   基础镜像不存在，开始构建（约5-10分钟）..."
    echo "   正在构建基础镜像，请耐心等待..."
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

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "=========================================="
echo "✅ 服务器初始化完成！"
echo "=========================================="
echo ""
echo "访问地址: http://$(curl -s ifconfig.me 2>/dev/null || echo '123.57.216.15'):8001"
echo ""
echo "后续部署只需在本地执行: ./deploy.sh"
echo ""
ENDSSH
        fi
        ;;
    
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac

echo ""
