#!/bin/bash
# ECS 初始化脚本
# 用途：在阿里云 ECS（Alibaba Cloud Linux 3）上安装 Docker 环境
# 使用：bash init-ecs.sh

set -e

echo "========================================"
echo "HiFate ECS 初始化"
echo "系统: Alibaba Cloud Linux 3"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "请以 root 用户执行此脚本"
    exit 1
fi

# 1. 更新系统
echo ""
echo "[1/6] 更新系统..."
yum update -y

# 2. 安装基础工具
echo ""
echo "[2/6] 安装基础工具..."
yum install -y git curl wget vim htop net-tools jq

# 3. 安装 Docker
echo ""
echo "[3/6] 安装 Docker..."
if command -v docker &> /dev/null; then
    echo "Docker 已安装: $(docker --version)"
else
    # Alibaba Cloud Linux 3 使用 dnf/yum
    yum install -y yum-utils
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# 4. 启动 Docker
echo ""
echo "[4/6] 启动 Docker..."
systemctl start docker
systemctl enable docker

# 5. 配置 Docker
echo ""
echo "[5/6] 配置 Docker..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true
}
EOF

systemctl daemon-reload
systemctl restart docker

# 6. 安装 Docker Compose
echo ""
echo "[6/6] 安装 Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo "Docker Compose 已安装: $(docker-compose --version)"
else
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r '.tag_name')
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
fi

# 创建项目目录
echo ""
echo "创建项目目录..."
mkdir -p /opt/HiFate-bazi
mkdir -p /opt/HiFate-bazi/logs

# 系统优化
echo ""
echo "系统优化..."
cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65535
* hard nofile 65535
EOF

cat >> /etc/sysctl.conf << 'EOF'
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
vm.swappiness = 10
EOF
sysctl -p 2>/dev/null || true

echo ""
echo "========================================"
echo "初始化完成！"
echo "========================================"
echo ""
echo "后续步骤："
echo "  1. 克隆代码: cd /opt/HiFate-bazi && git clone ... ."
echo "  2. 配置环境: cp deploy/env/env.template .env && vim .env"
echo "  3. 部署服务: bash deploy/scripts/deploy.sh node1  # 或 node2"
echo ""
echo "Docker: $(docker --version)"
echo "Compose: $(docker-compose --version)"
echo "========================================"
