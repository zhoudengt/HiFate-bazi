#!/bin/bash
# 生产环境双机部署脚本（手动执行版本）
# 用途：在服务器上直接执行，无需 SSH 连接
# 使用：在 Node1 和 Node2 上分别执行

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 生产环境配置
NODE1_PRIVATE_IP="172.18.121.222"
NODE2_PRIVATE_IP="172.18.121.223"
MYSQL_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
MYSQL_REPL_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

# Git 仓库配置
GIT_REPO="https://github.com/zhoudengt/HiFate-bazi"

# ACR 镜像仓库配置
ACR_REGISTRY="registry.cn-hangzhou.aliyuncs.com"
ACR_NAMESPACE="hifate"
# ACR 配置（从环境变量读取，避免泄露敏感信息）
ACR_USERNAME="${ACR_USERNAME:-${ACR_ACCESS_KEY_ID}}"
ACR_PASSWORD="${ACR_PASSWORD:-${ACR_ACCESS_KEY_SECRET}}"

# SECRET_KEY（已生成）
SECRET_KEY="${SECRET_KEY:?SECRET_KEY env var required}"

# 检测当前节点
CURRENT_IP=$(hostname -I | awk '{print $1}')
if [[ "$CURRENT_IP" == *"172.18.121.222"* ]] || [[ "$CURRENT_IP" == *"8.210.52.217"* ]]; then
    NODE_TYPE="node1"
    NODE_ID="node1"
elif [[ "$CURRENT_IP" == *"172.18.121.223"* ]] || [[ "$CURRENT_IP" == *"47.243.160.43"* ]]; then
    NODE_TYPE="node2"
    NODE_ID="node2"
else
    echo -e "${RED}无法识别当前节点，请手动指定 NODE_TYPE${NC}"
    read -p "请输入节点类型 (node1/node2): " NODE_TYPE
    if [ "$NODE_TYPE" = "node1" ]; then
        NODE_ID="node1"
    else
        NODE_ID="node2"
    fi
fi

echo "========================================"
echo "生产环境部署 - ${NODE_TYPE}"
echo "当前 IP: $CURRENT_IP"
echo "========================================"
echo ""

PROJECT_DIR="/opt/HiFate-bazi"

# 步骤 1: 初始化（如果未初始化）
if ! command -v docker &> /dev/null; then
    echo "========================================"
    echo "步骤 1: 初始化服务器（安装 Docker）"
    echo "========================================"
    if [ -f "deploy/scripts/init-ecs.sh" ]; then
        bash deploy/scripts/init-ecs.sh
    else
        echo "初始化脚本不存在，请先克隆代码"
        exit 1
    fi
else
    echo "Docker 已安装: $(docker --version)"
fi
echo ""

# 步骤 2: 克隆/更新代码
echo "========================================"
echo "步骤 2: 克隆/更新代码"
echo "========================================"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

if [ -d ".git" ]; then
    echo "代码已存在，更新代码..."
    git pull origin master || git pull origin main || echo "更新失败，继续使用现有代码"
else
    echo "克隆代码..."
    git clone $GIT_REPO .
fi

echo -e "${GREEN}代码准备完成${NC}"
echo ""

# 步骤 3: 配置环境变量
echo "========================================"
echo "步骤 3: 配置环境变量"
echo "========================================"
cd $PROJECT_DIR

cat > .env << EOF
# 节点配置
NODE_ID=$NODE_ID

# 内网 IP
NODE1_IP=$NODE1_PRIVATE_IP
NODE2_IP=$NODE2_PRIVATE_IP

# ACR 镜像仓库
ACR_REGISTRY=$ACR_REGISTRY
ACR_NAMESPACE=$ACR_NAMESPACE
ACR_USERNAME=$ACR_USERNAME
ACR_PASSWORD=$ACR_PASSWORD
IMAGE_TAG=latest

# MySQL 配置
MYSQL_USER=root
MYSQL_PASSWORD=$MYSQL_PASSWORD
MYSQL_DATABASE=hifate_bazi
MYSQL_REPL_PASSWORD=$MYSQL_REPL_PASSWORD

# Redis 配置
REDIS_PASSWORD=

# 应用配置
SECRET_KEY=$SECRET_KEY

# 第三方服务（可选）
COZE_ACCESS_TOKEN=
COZE_BOT_ID=
INTENT_BOT_ID=
FORTUNE_ANALYSIS_BOT_ID=
DAILY_FORTUNE_ACTION_BOT_ID=
EOF

echo -e "${GREEN}环境变量配置完成${NC}"
echo ""

# 步骤 4: 部署服务
echo "========================================"
echo "步骤 4: 部署服务"
echo "========================================"
cd $PROJECT_DIR
bash deploy/scripts/deploy.sh $NODE_TYPE

echo ""
echo "========================================"
echo -e "${GREEN}${NODE_TYPE} 部署完成！${NC}"
echo "========================================"
echo ""
echo "后续步骤："
if [ "$NODE_TYPE" = "node1" ]; then
    echo "1. 配置 MySQL 主从复制用户："
    echo "   docker exec -it hifate-mysql-master mysql -uroot -p$MYSQL_PASSWORD"
    echo "   CREATE USER 'repl'@'%' IDENTIFIED BY '$MYSQL_REPL_PASSWORD';"
    echo "   GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';"
    echo "   FLUSH PRIVILEGES;"
    echo ""
    echo "2. 等待 Node2 部署完成后，在 Node2 上配置从库"
else
    echo "1. 配置 MySQL 从库（在 Node2 上执行）："
    echo "   docker exec -it hifate-mysql-slave mysql -uroot -p$MYSQL_PASSWORD"
    echo "   CHANGE MASTER TO"
    echo "       MASTER_HOST='$NODE1_PRIVATE_IP',"
    echo "       MASTER_USER='repl',"
    echo "       MASTER_PASSWORD='$MYSQL_REPL_PASSWORD',"
    echo "       MASTER_AUTO_POSITION=1;"
    echo "   START SLAVE;"
    echo "   SHOW SLAVE STATUS\\G"
fi
echo ""

