#!/bin/bash
# ============================================
# HiFate-bazi 服务器初始化脚本
# 首次部署时在服务器上执行
# 使用：curl -sSL https://gitee.com/.../server_init.sh | bash
# 或者：bash server_init.sh
# ============================================

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   HiFate-bazi 服务器初始化${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 配置
PROJECT_DIR="/opt/HiFate-bazi"
GITEE_REPO="https://gitee.com/zhoudengtang/hifate-prod.git"

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 root 用户执行此脚本${NC}"
    exit 1
fi

# 1. 更新系统
echo -e "${YELLOW}[1/7] 更新系统...${NC}"
apt update -qq
apt upgrade -y -qq

# 2. 安装 Docker
echo -e "${YELLOW}[2/7] 安装 Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}Docker 安装完成${NC}"
else
    echo -e "${GREEN}Docker 已安装${NC}"
fi

# 3. 安装 Docker Compose
echo -e "${YELLOW}[3/7] 安装 Docker Compose...${NC}"
if ! docker compose version &> /dev/null; then
    apt install -y docker-compose-plugin
    echo -e "${GREEN}Docker Compose 安装完成${NC}"
else
    echo -e "${GREEN}Docker Compose 已安装${NC}"
fi

# 4. 配置 Docker 镜像加速
echo -e "${YELLOW}[4/7] 配置 Docker 镜像加速...${NC}"
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
    "registry-mirrors": [
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com",
        "https://mirror.baidubce.com"
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
echo -e "${GREEN}Docker 镜像加速配置完成${NC}"

# 5. 安装 Git
echo -e "${YELLOW}[5/7] 安装 Git...${NC}"
apt install -y git curl
git config --global credential.helper store

# 6. 克隆代码
echo -e "${YELLOW}[6/7] 克隆代码...${NC}"
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}项目目录已存在，跳过克隆${NC}"
else
    mkdir -p /opt
    cd /opt
    git clone "$GITEE_REPO" HiFate-bazi
    echo -e "${GREEN}代码克隆完成${NC}"
fi

# 7. 创建环境配置
echo -e "${YELLOW}[7/7] 创建环境配置...${NC}"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cat > "$PROJECT_DIR/.env" << 'EOF'
# === HiFate-bazi 生产环境配置 ===
# 创建时间: $(date '+%Y-%m-%d %H:%M:%S')

APP_ENV=production
DEBUG=False

# MySQL 配置（请修改密码！）
MYSQL_ROOT_PASSWORD=HiFate_Prod_2024!
MYSQL_USER=root
MYSQL_DATABASE=bazi_system

# Redis 配置
REDIS_PASSWORD=HiFate_Redis_2024!

# Web 端口
WEB_PORT=8001

# 密钥（请修改！）
SECRET_KEY=change-me-to-a-random-string

# 日志级别
LOG_LEVEL=WARNING
EOF
    chmod 600 "$PROJECT_DIR/.env"
    echo -e "${GREEN}环境配置创建完成${NC}"
    echo -e "${YELLOW}⚠️  请编辑 $PROJECT_DIR/.env 修改密码！${NC}"
else
    echo -e "${GREEN}环境配置已存在${NC}"
fi

# 完成
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   初始化完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}下一步：${NC}"
echo ""
echo "1. 编辑配置文件（修改密码）："
echo -e "   ${YELLOW}vim $PROJECT_DIR/.env${NC}"
echo ""
echo "2. 启动服务："
echo -e "   ${YELLOW}cd $PROJECT_DIR${NC}"
echo -e "   ${YELLOW}docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build${NC}"
echo ""
echo "3. 查看状态："
echo -e "   ${YELLOW}docker compose ps${NC}"
echo ""
echo "4. 访问服务："
echo -e "   ${YELLOW}http://$(curl -s ifconfig.me):8001${NC}"
echo ""

