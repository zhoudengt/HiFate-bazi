#!/bin/bash
# 生产环境双机部署脚本
# 用途：自动化部署生产环境 Node1 和 Node2
# 使用：bash deploy_production.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE1_PRIVATE_IP="172.18.121.222"
NODE2_PUBLIC_IP="47.243.160.43"
NODE2_PRIVATE_IP="172.18.121.223"
MYSQL_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
MYSQL_REPL_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

# Git 仓库配置
GIT_REPO="https://github.com/zhoudengt/HiFate-bazi"

# ACR 镜像仓库配置（从环境变量读取，避免泄露敏感信息）
ACR_USERNAME="${ACR_USERNAME:-${ACR_ACCESS_KEY_ID}}"
ACR_PASSWORD="${ACR_PASSWORD:-${ACR_ACCESS_KEY_SECRET}}"

# 生成 SECRET_KEY
SECRET_KEY="${SECRET_KEY:?SECRET_KEY env var required}"

# SSH 密码
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

# 测试环境（不要操作）
TEST_ENV_IP="123.57.216.15"

# SSH 执行函数（使用 sshpass）
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
}

# SCP 上传函数（使用 sshpass）
scp_upload() {
    local host=$1
    local src=$2
    local dst=$3
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 $src root@$host:$dst
}

# 删除前端相关目录和文件函数（前端团队已独立部署，禁止同步）
remove_frontend_files() {
    local host=$1
    local node_name=$2
    
    echo "🚫 删除 $node_name 前端相关目录和文件（前端团队已独立部署，禁止同步）..."
    ssh_exec $host "cd /opt/HiFate-bazi && \
        rm -rf local_frontend frontend frontend-config nginx deploy/nginx 2>/dev/null || true && \
        rm -f docker-compose.frontend.yml docker-compose.nginx.yml 2>/dev/null || true && \
        rm -f scripts/deploy-frontend.sh scripts/deploy_nacos_proxy.sh scripts/deploy_frontend_proxy_dual_nodes.sh 2>/dev/null || true && \
        rm -f scripts/rollback_frontend_proxy_dual_nodes.sh scripts/protect_frontend_directory.sh scripts/restore_frontend_directory.sh scripts/check_frontend_directory.sh 2>/dev/null || true && \
        echo '✅ 前端相关目录和文件已删除（前端团队独立部署）'"
    
    # 验证删除结果
    if ssh_exec $host "cd /opt/HiFate-bazi && [ -d local_frontend ] || [ -d frontend ] || [ -d frontend-config ] || [ -d nginx ] || [ -d deploy/nginx ]" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  警告：部分前端目录可能未完全删除，请手动检查${NC}"
    else
        echo -e "${GREEN}✅ $node_name 前端目录删除验证通过${NC}"
    fi
}

echo "========================================"
echo "生产环境双机部署"
echo "========================================"
echo "Node1: $NODE1_PUBLIC_IP ($NODE1_PRIVATE_IP)"
echo "Node2: $NODE2_PUBLIC_IP ($NODE2_PRIVATE_IP)"
echo "测试环境: $TEST_ENV_IP (不会操作)"
echo "========================================"
echo ""

# 确认（支持非交互模式）
if [ -z "$AUTO_DEPLOY" ]; then
    read -p "确认部署到生产环境？(yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "已取消部署"
        exit 1
    fi
else
    echo "自动部署模式，跳过确认"
fi

# 检查 SSH 连接
echo "检查 SSH 连接..."
ssh_exec $NODE1_PUBLIC_IP "echo 'Node1 连接成功'" || {
    echo -e "${RED}无法连接到 Node1 ($NODE1_PUBLIC_IP)${NC}"
    exit 1
}

ssh_exec $NODE2_PUBLIC_IP "echo 'Node2 连接成功'" || {
    echo -e "${RED}无法连接到 Node2 ($NODE2_PUBLIC_IP)${NC}"
    exit 1
}

echo -e "${GREEN}SSH 连接检查通过${NC}"
echo ""

# 步骤 1: 初始化 Node1
echo "========================================"
echo "步骤 1: 初始化 Node1"
echo "========================================"
echo "上传初始化脚本到 Node1..."
scp_upload $NODE1_PUBLIC_IP "deploy/scripts/init-ecs.sh" "/tmp/init-ecs.sh"

echo "在 Node1 上执行初始化..."
ssh_exec $NODE1_PUBLIC_IP "bash /tmp/init-ecs.sh"

echo -e "${GREEN}Node1 初始化完成${NC}"
echo ""

# 步骤 2: 初始化 Node2
echo "========================================"
echo "步骤 2: 初始化 Node2"
echo "========================================"
echo "上传初始化脚本到 Node2..."
scp_upload $NODE2_PUBLIC_IP "deploy/scripts/init-ecs.sh" "/tmp/init-ecs.sh"

echo "在 Node2 上执行初始化..."
ssh_exec $NODE2_PUBLIC_IP "bash /tmp/init-ecs.sh"

echo -e "${GREEN}Node2 初始化完成${NC}"
echo ""

# Git 仓库地址
GIT_REPO="https://github.com/zhoudengt/HiFate-bazi"

# ACR 配置（从环境变量读取，避免泄露敏感信息）
ACR_USERNAME="${ACR_USERNAME:-${ACR_ACCESS_KEY_ID}}"
ACR_PASSWORD="${ACR_PASSWORD:-${ACR_ACCESS_KEY_SECRET}}"

# 生成 SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)

echo "生成的 SECRET_KEY: $SECRET_KEY"
echo ""

# 步骤 3: 克隆代码到 Node1
echo "========================================"
echo "步骤 3: 克隆代码到 Node1"
echo "========================================"
echo "在 Node1 上克隆代码..."
ssh_exec $NODE1_PUBLIC_IP "cd /opt/HiFate-bazi && if [ -d '.git' ]; then echo '代码已存在，更新代码...' && git pull origin master || git pull origin main; else echo '克隆代码...' && mkdir -p /opt/HiFate-bazi && git clone $GIT_REPO /opt/HiFate-bazi; fi"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Node1 代码克隆/更新完成${NC}"
    # 🚫 删除前端相关目录和文件（前端团队已独立部署，禁止同步）
    remove_frontend_files $NODE1_PUBLIC_IP "Node1"
else
    echo -e "${RED}Node1 代码克隆失败${NC}"
    exit 1
fi
echo ""

# 步骤 4: 克隆代码到 Node2
echo "========================================"
echo "步骤 4: 克隆代码到 Node2"
echo "========================================"
echo "在 Node2 上克隆代码..."
ssh_exec $NODE2_PUBLIC_IP "cd /opt/HiFate-bazi && if [ -d '.git' ]; then echo '代码已存在，更新代码...' && git pull origin master || git pull origin main; else echo '克隆代码...' && mkdir -p /opt/HiFate-bazi && git clone $GIT_REPO /opt/HiFate-bazi; fi"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Node2 代码克隆/更新完成${NC}"
    # 🚫 删除前端相关目录和文件（前端团队已独立部署，禁止同步）
    remove_frontend_files $NODE2_PUBLIC_IP "Node2"
else
    echo -e "${RED}Node2 代码克隆失败${NC}"
    exit 1
fi
echo ""

# 步骤 5: 配置 Node1 环境变量
echo "========================================"
echo "步骤 5: 配置 Node1 环境变量"
echo "========================================"

# 生成 Node1 的 .env 文件
cat > /tmp/node1.env << EOF
# 节点配置
NODE_ID=node1

# 内网 IP
NODE1_IP=$NODE1_PRIVATE_IP
NODE2_IP=$NODE2_PRIVATE_IP

# ACR 镜像仓库
ACR_REGISTRY=registry.cn-hangzhou.aliyuncs.com
ACR_NAMESPACE=hifate
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

echo "上传 .env 文件到 Node1..."
scp_upload $NODE1_PUBLIC_IP "/tmp/node1.env" "/opt/HiFate-bazi/.env"
rm /tmp/node1.env

echo -e "${GREEN}Node1 环境变量配置完成${NC}"
echo ""

# 步骤 6: 配置 Node2 环境变量
echo "========================================"
echo "步骤 6: 配置 Node2 环境变量"
echo "========================================"

# 生成 Node2 的 .env 文件
cat > /tmp/node2.env << EOF
# 节点配置
NODE_ID=node2

# 内网 IP
NODE1_IP=$NODE1_PRIVATE_IP
NODE2_IP=$NODE2_PRIVATE_IP

# ACR 镜像仓库
ACR_REGISTRY=registry.cn-hangzhou.aliyuncs.com
ACR_NAMESPACE=hifate
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

echo "上传 .env 文件到 Node2..."
scp_upload $NODE2_PUBLIC_IP "/tmp/node2.env" "/opt/HiFate-bazi/.env"
rm /tmp/node2.env

echo -e "${GREEN}Node2 环境变量配置完成${NC}"
echo ""

# 步骤 7: 部署 Node1
echo "========================================"
echo "步骤 7: 部署 Node1（主节点）"
echo "========================================"
echo "在 Node1 上执行部署..."
ssh_exec $NODE1_PUBLIC_IP "cd /opt/HiFate-bazi && bash deploy/scripts/deploy.sh node1"

echo -e "${GREEN}Node1 部署完成${NC}"
echo ""

# 步骤 8: 配置 MySQL 主从复制用户
echo "========================================"
echo "步骤 8: 配置 MySQL 主从复制用户"
echo "========================================"
echo "在 Node1 上创建复制用户..."
ssh_exec $NODE1_PUBLIC_IP "docker exec -i hifate-mysql-master mysql -uroot -p$MYSQL_PASSWORD -e \"CREATE USER IF NOT EXISTS 'repl'@'%' IDENTIFIED BY '$MYSQL_REPL_PASSWORD'; GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%'; FLUSH PRIVILEGES; SHOW MASTER STATUS;\""

echo -e "${GREEN}MySQL 主从复制用户创建完成${NC}"
echo ""

# 步骤 9: 部署 Node2
echo "========================================"
echo "步骤 9: 部署 Node2（从节点）"
echo "========================================"
echo "在 Node2 上执行部署..."
ssh_exec $NODE2_PUBLIC_IP "cd /opt/HiFate-bazi && bash deploy/scripts/deploy.sh node2"

echo -e "${GREEN}Node2 部署完成${NC}"
echo ""

# 步骤 10: 配置 Node2 MySQL 从库
echo "========================================"
echo "步骤 10: 配置 Node2 MySQL 从库"
echo "========================================"
echo "在 Node2 上配置从库..."
ssh_exec $NODE2_PUBLIC_IP "docker exec -i hifate-mysql-slave mysql -uroot -p$MYSQL_PASSWORD -e \"CHANGE MASTER TO MASTER_HOST='$NODE1_PRIVATE_IP', MASTER_USER='repl', MASTER_PASSWORD='$MYSQL_REPL_PASSWORD', MASTER_AUTO_POSITION=1; START SLAVE; SHOW SLAVE STATUS\\G\""

echo -e "${GREEN}Node2 MySQL 从库配置完成${NC}"
echo ""

# 步骤 11: 验证部署
echo "========================================"
echo "步骤 11: 验证部署"
echo "========================================"
echo "检查 Node1 服务状态..."
ssh_exec $NODE1_PUBLIC_IP "docker ps | grep hifate"

echo ""
echo "检查 Node2 服务状态..."
ssh_exec $NODE2_PUBLIC_IP "docker ps | grep hifate"

echo ""
echo "检查 Node1 健康状态..."
ssh_exec $NODE1_PUBLIC_IP "curl -s http://localhost/health || echo '健康检查失败'"

echo ""
echo "检查 Node2 健康状态..."
ssh_exec $NODE2_PUBLIC_IP "curl -s http://localhost/health || echo '健康检查失败'"

echo ""
echo "检查 MySQL 主从复制状态..."
ssh_exec $NODE2_PUBLIC_IP "docker exec -i hifate-mysql-slave mysql -uroot -p$MYSQL_PASSWORD -e \"SHOW SLAVE STATUS\\G\" | grep -E 'Slave_IO_Running|Slave_SQL_Running'"

echo ""
echo "========================================"
echo -e "${GREEN}部署完成！${NC}"
echo "========================================"
echo ""
echo "访问地址："
echo "  Node1: http://$NODE1_PUBLIC_IP"
echo "  Node2: http://$NODE2_PUBLIC_IP"
echo ""
echo "健康检查："
echo "  Node1: http://$NODE1_PUBLIC_IP/health"
echo "  Node2: http://$NODE2_PUBLIC_IP/health"
echo ""

