#!/bin/bash
# HiFate-bazi 服务器初始化脚本
# 用途：在生产服务器上快速初始化部署环境
# 使用方法：bash scripts/setup_server.sh

set -e

echo "=========================================="
echo "🚀 HiFate-bazi 服务器初始化脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}❌ 请使用 root 用户运行此脚本${NC}"
  exit 1
fi

# 项目目录
PROJECT_DIR="/opt/HiFate-bazi"

echo -e "${GREEN}📋 步骤 1/7: 检测操作系统...${NC}"

# 改进的操作系统检测逻辑
OS=""
if [ -f /etc/os-release ]; then
  # 使用 /etc/os-release（更通用）
  . /etc/os-release
  case $ID in
    centos|rhel|fedora|almalinux|rocky|alibaba|alinux|anolis)
      OS="centos"
      echo "✅ 检测到基于 RedHat 的系统: $PRETTY_NAME"
      ;;
    ubuntu|debian)
      OS="ubuntu"
      echo "✅ 检测到基于 Debian 的系统: $PRETTY_NAME"
      ;;
    *)
      # 尝试通过包管理器判断
      if command -v yum &> /dev/null || command -v dnf &> /dev/null; then
        OS="centos"
        echo "✅ 通过包管理器检测到 RedHat 系列系统"
      elif command -v apt &> /dev/null || command -v apt-get &> /dev/null; then
        OS="ubuntu"
        echo "✅ 通过包管理器检测到 Debian 系列系统"
      else
        echo -e "${YELLOW}⚠️  无法自动检测操作系统，尝试使用 yum...${NC}"
        if command -v yum &> /dev/null; then
          OS="centos"
          echo "✅ 使用 yum 包管理器"
        elif command -v apt-get &> /dev/null; then
          OS="ubuntu"
          echo "✅ 使用 apt-get 包管理器"
        fi
      fi
      ;;
  esac
elif [ -f /etc/redhat-release ]; then
  OS="centos"
  echo "✅ 检测到 RedHat 系列系统"
elif [ -f /etc/lsb-release ]; then
  OS="ubuntu"
  echo "✅ 检测到 Ubuntu 系统"
else
  # 最后的回退：通过包管理器判断
  if command -v yum &> /dev/null || command -v dnf &> /dev/null; then
    OS="centos"
    echo "✅ 通过包管理器检测到 RedHat 系列系统"
  elif command -v apt &> /dev/null || command -v apt-get &> /dev/null; then
    OS="ubuntu"
    echo "✅ 通过包管理器检测到 Debian 系列系统"
  else
    echo -e "${RED}❌ 无法检测操作系统，请手动安装 Docker 和 Docker Compose${NC}"
    echo "   系统信息："
    cat /etc/*release 2>/dev/null || echo "   无法获取系统信息"
    exit 1
  fi
fi

echo -e "${GREEN}📋 步骤 2/7: 更新系统包...${NC}"
if [ "$OS" = "centos" ]; then
  yum update -y || dnf update -y
  # 尝试安装 epel-release（如果可用）
  yum install -y epel-release 2>/dev/null || dnf install -y epel-release 2>/dev/null || echo "⚠️  EPEL 仓库不可用，跳过"
elif [ "$OS" = "ubuntu" ]; then
  apt update && apt upgrade -y
fi

echo -e "${GREEN}📋 步骤 3/7: 安装基础软件...${NC}"
if [ "$OS" = "centos" ]; then
  yum install -y git curl wget vim net-tools lsof 2>/dev/null || dnf install -y git curl wget vim net-tools lsof
elif [ "$OS" = "ubuntu" ]; then
  apt install -y git curl wget vim net-tools lsof
fi

echo -e "${GREEN}📋 步骤 4/7: 安装 Docker 和 Docker Compose...${NC}"
if ! command -v docker &> /dev/null; then
  if [ "$OS" = "centos" ]; then
    # Alibaba Cloud Linux 使用 yum
    yum install -y docker 2>/dev/null || dnf install -y docker
  elif [ "$OS" = "ubuntu" ]; then
    apt install -y docker.io
  fi
  
  systemctl start docker
  systemctl enable docker
  echo "✅ Docker 已安装并启动"
else
  echo "✅ Docker 已安装"
fi

# 安装 Docker Compose
if ! command -v docker-compose &> /dev/null; then
  echo "📥 安装 Docker Compose..."
  curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  echo "✅ Docker Compose 已安装"
else
  echo "✅ Docker Compose 已安装"
fi

echo -e "${GREEN}📋 步骤 5/7: 配置防火墙...${NC}"
if [ "$OS" = "centos" ]; then
  if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port=80/tcp
    firewall-cmd --permanent --add-port=443/tcp
    firewall-cmd --permanent --add-port=8001/tcp
    firewall-cmd --permanent --add-port=22/tcp
    firewall-cmd --reload
    echo "✅ 防火墙规则已配置"
  else
    echo "⚠️  firewalld 未运行，跳过防火墙配置"
  fi
elif [ "$OS" = "ubuntu" ]; then
  if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 8001/tcp
    ufw allow 22/tcp
    echo "✅ 防火墙规则已配置"
  else
    echo "⚠️  ufw 未安装，跳过防火墙配置"
  fi
fi

echo -e "${GREEN}📋 步骤 6/7: 创建项目目录...${NC}"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 创建必要的目录
mkdir -p backups
mkdir -p logs
chmod 755 $PROJECT_DIR

echo "✅ 项目目录已创建: $PROJECT_DIR"

echo -e "${GREEN}📋 步骤 7/7: 配置 Git 仓库...${NC}"
if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "📥 初始化 Git 仓库..."
  read -p "请输入 Git 仓库地址 (默认: https://gitee.com/zhoudengtang/hifate-prod.git): " GIT_REPO
  GIT_REPO=${GIT_REPO:-https://gitee.com/zhoudengtang/hifate-prod.git}
  
  git clone $GIT_REPO $PROJECT_DIR || {
    echo "⚠️  Git 克隆失败，请手动克隆或初始化"
    echo "    cd $PROJECT_DIR"
    echo "    git init"
    echo "    git remote add origin $GIT_REPO"
  }
else
  echo "✅ Git 仓库已存在"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 服务器初始化完成！${NC}"
echo "=========================================="
echo ""
echo "📋 后续步骤："
echo ""
echo "1. 配置环境变量："
echo "   cd $PROJECT_DIR"
echo "   cp env.template .env"
echo "   vim .env  # 修改密码和配置"
echo "   chmod 600 .env"
echo ""
echo "2. 生成 SSH 密钥（用于 GitHub Actions）："
echo "   ssh-keygen -t ed25519 -C 'github-actions' -f ~/.ssh/github_actions"
echo "   cat ~/.ssh/github_actions  # 复制到 GitHub Secrets 的 PROD_SSH_PRIVATE_KEY"
echo "   cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys"
echo "   chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "3. 首次构建基础镜像（可选，但推荐）："
echo "   cd $PROJECT_DIR"
echo "   chmod +x scripts/docker/build_base.sh"
echo "   ./scripts/docker/build_base.sh"
echo ""
echo "4. 测试部署："
echo "   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
echo "   curl http://localhost:8001/health"
echo ""
echo "=========================================="

