#!/bin/bash
# ============================================
# HiFate ECS 初始化脚本
# ============================================
# 用途：初始化阿里云 ECS 实例，安装 Docker 环境
# 使用：在新创建的 ECS 上以 root 用户执行
#
# curl -fsSL https://raw.githubusercontent.com/your-org/HiFate-bazi/master/scripts/aliyun/init_ecs.sh | bash
# 或
# bash scripts/aliyun/init_ecs.sh

set -e

echo "========================================"
echo "🚀 HiFate ECS 初始化"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请以 root 用户执行此脚本"
    exit 1
fi

# 检测操作系统
if [ -f /etc/centos-release ]; then
    OS="centos"
elif [ -f /etc/debian_version ]; then
    OS="debian"
else
    echo "⚠️ 未识别的操作系统，尝试使用 CentOS 方式安装"
    OS="centos"
fi

echo "📋 检测到操作系统: ${OS}"

# ============================================
# 1. 更新系统
# ============================================
echo ""
echo "📦 [1/8] 更新系统包..."
if [ "$OS" = "centos" ]; then
    yum update -y
else
    apt-get update && apt-get upgrade -y
fi

# ============================================
# 2. 安装基础工具
# ============================================
echo ""
echo "🔧 [2/8] 安装基础工具..."
if [ "$OS" = "centos" ]; then
    yum install -y git curl wget vim htop net-tools jq
else
    apt-get install -y git curl wget vim htop net-tools jq
fi

# ============================================
# 3. 安装 Docker
# ============================================
echo ""
echo "🐳 [3/8] 安装 Docker..."

if command -v docker &> /dev/null; then
    echo "✅ Docker 已安装: $(docker --version)"
else
    if [ "$OS" = "centos" ]; then
        # CentOS/RHEL
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    else
        # Debian/Ubuntu
        apt-get install -y ca-certificates curl gnupg
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
fi

# ============================================
# 4. 启动 Docker
# ============================================
echo ""
echo "▶️ [4/8] 启动 Docker 服务..."
systemctl start docker
systemctl enable docker
echo "✅ Docker 服务已启动"

# ============================================
# 5. 配置 Docker 镜像加速
# ============================================
echo ""
echo "⚡ [5/8] 配置 Docker 镜像加速..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
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
echo "✅ Docker 镜像加速已配置"

# ============================================
# 6. 安装 Docker Compose（独立版本）
# ============================================
echo ""
echo "📦 [6/8] 安装 Docker Compose..."

if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose 已安装: $(docker-compose --version)"
else
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r '.tag_name')
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    echo "✅ Docker Compose 安装完成: $(docker-compose --version)"
fi

# ============================================
# 7. 创建项目目录
# ============================================
echo ""
echo "📁 [7/8] 创建项目目录..."

PROJECT_DIR="/opt/HiFate-bazi"
mkdir -p ${PROJECT_DIR}
cd ${PROJECT_DIR}

# 创建日志目录
mkdir -p logs/{web,bazi-core,bazi-fortune,bazi-analyzer,rule-service,fortune-analyzer,payment-service,fortune-rule,intent-service,prompt-optimizer,desk-fengshui}

# 创建 Nginx 目录
mkdir -p nginx/{conf.d,ssl}

echo "✅ 目录创建完成: ${PROJECT_DIR}"

# ============================================
# 8. 系统优化
# ============================================
echo ""
echo "⚙️ [8/8] 系统优化..."

# 优化文件描述符限制
cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535
EOF

# 优化内核参数
cat >> /etc/sysctl.conf << 'EOF'
# HiFate 优化参数
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3
vm.swappiness = 10
EOF

sysctl -p 2>/dev/null || true

echo "✅ 系统优化完成"

# ============================================
# 完成
# ============================================
echo ""
echo "========================================"
echo "✅ HiFate ECS 初始化完成！"
echo "========================================"
echo ""
echo "📋 后续步骤："
echo "  1. 克隆代码仓库："
echo "     cd /opt/HiFate-bazi"
echo "     git clone https://github.com/your-org/HiFate-bazi.git ."
echo ""
echo "  2. 配置环境变量："
echo "     cp .env.aliyun.template .env"
echo "     vim .env  # 编辑配置"
echo ""
echo "  3. 首次部署："
echo "     bash scripts/aliyun/first_deploy.sh"
echo ""
echo "========================================"

# 显示系统信息
echo ""
echo "📊 系统信息："
echo "  Docker: $(docker --version)"
echo "  Docker Compose: $(docker-compose --version)"
echo "  内存: $(free -h | grep Mem | awk '{print $2}')"
echo "  磁盘: $(df -h / | tail -1 | awk '{print $4}') 可用"
echo "  CPU: $(nproc) 核"
echo "========================================"
