#!/bin/bash
# HiFate-bazi 远程服务器快速部署脚本
# 使用方法：在远程服务器上执行此脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}HiFate-bazi 远程服务器部署${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否为 root 用户（允许 root，但给出提示）
if [ "$EUID" -eq 0 ]; then 
   echo -e "${YELLOW}⚠️  检测到使用 root 用户${NC}"
   echo -e "${YELLOW}使用 root 用户部署是允许的，但建议使用普通用户以提高安全性${NC}"
   echo -e "${YELLOW}继续使用 root 用户部署...${NC}"
   echo ""
fi

# 项目目录
PROJECT_DIR="/opt/HiFate-bazi"

# 判断是否为 root 用户
IS_ROOT=false
if [ "$EUID" -eq 0 ]; then 
   IS_ROOT=true
fi

# 根据用户类型设置命令前缀
if [ "$IS_ROOT" = true ]; then
    SUDO_CMD=""  # root 用户不需要 sudo
else
    SUDO_CMD="sudo"  # 普通用户需要 sudo
fi

# 步骤 1：检查 Docker
echo -e "${BLUE}[1/8] 检查 Docker 环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    echo -e "${YELLOW}正在安装 Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    $SUDO_CMD sh get-docker.sh
    if [ "$IS_ROOT" = false ]; then
        $SUDO_CMD usermod -aG docker $USER
        echo -e "${YELLOW}⚠️  请重新登录以使 Docker 组权限生效${NC}"
    fi
    rm get-docker.sh
fi

# 检查 Docker Compose（支持两种格式：docker-compose 和 docker compose）
DOCKER_COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo -e "${RED}❌ Docker Compose 未安装${NC}"
    echo -e "${YELLOW}正在安装 Docker Compose...${NC}"
    if command -v apt-get &> /dev/null; then
        $SUDO_CMD apt-get update
        $SUDO_CMD apt-get install -y docker-compose-plugin
    elif command -v yum &> /dev/null; then
        $SUDO_CMD yum install -y docker-compose-plugin
    fi
    
    # 重新检查
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}❌ Docker Compose 安装失败${NC}"
        echo -e "${YELLOW}请手动安装 Docker Compose${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Docker Compose 已安装（使用：$DOCKER_COMPOSE_CMD）${NC}"

echo -e "${GREEN}✅ Docker 环境检查通过${NC}"

# 步骤 2：检查当前目录状态
echo -e "${BLUE}[2/8] 检查项目目录...${NC}"

# 检查是否已经在项目目录中（通过检查是否有 deploy_remote.sh）
CURRENT_DIR=$(pwd)
if [ -f "scripts/deploy_remote.sh" ] || [ -f "deploy_remote.sh" ]; then
    echo -e "${GREEN}✅ 检测到已在项目目录中：$CURRENT_DIR${NC}"
    PROJECT_DIR="$CURRENT_DIR"
else
    # 不在项目目录中，需要创建或进入项目目录
    if [ ! -d "$PROJECT_DIR" ]; then
        $SUDO_CMD mkdir -p "$PROJECT_DIR"
        if [ "$IS_ROOT" = false ]; then
            $SUDO_CMD chown $USER:$USER "$PROJECT_DIR"
        fi
        echo -e "${GREEN}✅ 项目目录已创建：$PROJECT_DIR${NC}"
    else
        echo -e "${GREEN}✅ 项目目录已存在：$PROJECT_DIR${NC}"
    fi
    
    # 进入项目目录
    cd "$PROJECT_DIR" || {
        echo -e "${RED}❌ 无法进入项目目录${NC}"
        exit 1
    }
fi

# 步骤 3：检查代码
echo -e "${BLUE}[3/8] 检查代码...${NC}"

# 优先检查代码是否已存在（通过检查关键文件）
if [ -f "scripts/deploy_remote.sh" ] || [ -f "docker-compose.yml" ] || [ -f "server/main.py" ]; then
    echo -e "${GREEN}✅ 检测到代码已存在${NC}"
    
    # 如果有 .git，尝试更新（可选）
    if [ -d ".git" ]; then
        echo -e "${GREEN}✅ 检测到 Git 仓库，可以更新代码${NC}"
        echo -e "${YELLOW}是否更新代码？(Y/n): ${NC}"
        read -t 5 -p "" UPDATE_CODE || UPDATE_CODE="n"
        
        if [ "$UPDATE_CODE" != "n" ] && [ "$UPDATE_CODE" != "N" ]; then
            echo -e "${YELLOW}拉取最新代码...${NC}"
            timeout 30 git fetch origin 2>/dev/null || {
                echo -e "${YELLOW}⚠️  网络连接超时，跳过代码更新${NC}"
            }
            git checkout master 2>/dev/null || true
            timeout 60 git pull origin master 2>/dev/null || {
                echo -e "${YELLOW}⚠️  代码拉取失败，使用当前代码继续部署${NC}"
            }
            echo -e "${GREEN}✅ 代码检查完成${NC}"
        else
            echo -e "${GREEN}✅ 跳过代码更新，使用当前代码${NC}"
        fi
    else
        echo -e "${GREEN}✅ 代码已存在（ZIP 下载方式），直接使用当前代码${NC}"
        echo -e "${YELLOW}提示：如需更新代码，请重新下载 ZIP 包${NC}"
    fi
else
    # 代码不存在，需要克隆或下载
    echo -e "${YELLOW}⚠️  代码不存在，需要下载代码${NC}"
    
    # 检查是否有 .git（可能是空目录）
    if [ -d ".git" ]; then
        echo -e "${YELLOW}检测到 .git 目录，尝试拉取代码...${NC}"
        git pull origin master 2>/dev/null || {
            echo -e "${RED}❌ Git 拉取失败，请手动下载代码${NC}"
            echo -e "${YELLOW}建议：使用 ZIP 包下载方式${NC}"
            exit 1
        }
    else
        echo -e "${RED}❌ 代码不存在，请先下载代码${NC}"
        echo -e "${YELLOW}下载方式：${NC}"
        echo -e "  1. 使用 ZIP 包：wget https://github.com.cnpmjs.org/zhoudengt/HiFate-bazi/archive/refs/heads/master.zip"
        echo -e "  2. 使用 Git：git clone https://github.com.cnpmjs.org/zhoudengt/HiFate-bazi.git ."
        exit 1
    fi
fi

# 步骤 4：配置环境变量
echo -e "${BLUE}[4/8] 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
    if [ -f "env.template" ]; then
        cp env.template .env
        chmod 600 .env
        echo -e "${YELLOW}⚠️  已创建 .env 文件，请编辑配置：${NC}"
        echo -e "${YELLOW}   vim .env${NC}"
        echo ""
        echo -e "${YELLOW}必须修改以下配置：${NC}"
        echo -e "  - MYSQL_ROOT_PASSWORD（数据库密码）"
        echo -e "  - SECRET_KEY（应用密钥）"
        echo ""
        read -p "按 Enter 继续（已编辑 .env 文件）..."
    else
        echo -e "${RED}❌ env.template 文件不存在${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env 文件已存在${NC}"
    read -p "是否重新配置环境变量？(y/N): " RECONFIG
    if [ "$RECONFIG" == "y" ] || [ "$RECONFIG" == "Y" ]; then
        vim .env
        chmod 600 .env
    fi
fi

# 步骤 5：检查端口占用
echo -e "${BLUE}[5/8] 检查端口占用...${NC}"
if command -v netstat &> /dev/null; then
    if netstat -tlnp 2>/dev/null | grep -q ":8001 "; then
        echo -e "${YELLOW}⚠️  端口 8001 已被占用${NC}"
        read -p "是否继续？(y/N): " CONTINUE
        if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
            exit 1
        fi
    else
        echo -e "${GREEN}✅ 端口 8001 可用${NC}"
    fi
fi

# 步骤 6：停止旧容器
echo -e "${BLUE}[6/8] 停止旧容器...${NC}"
$DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true
echo -e "${GREEN}✅ 旧容器已停止${NC}"

# 步骤 7：构建镜像
echo -e "${BLUE}[7/8] 构建 Docker 镜像...${NC}"
echo -e "${YELLOW}这可能需要几分钟，请耐心等待...${NC}"

# 询问是否使用缓存（默认使用，加速构建）
echo -e "${YELLOW}是否使用缓存构建？(Y/n): ${NC}"
read -t 5 -p "" USE_CACHE || USE_CACHE="y"

if [ "$USE_CACHE" == "n" ] || [ "$USE_CACHE" == "N" ]; then
    echo -e "${YELLOW}⚠️  使用 --no-cache 构建（会较慢，但确保完全重新构建）...${NC}"
$DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
else
    echo -e "${GREEN}✅ 使用缓存构建（更快，推荐）...${NC}"
    $DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml build
fi

echo -e "${GREEN}✅ 镜像构建完成${NC}"

# 步骤 8：启动服务
echo -e "${BLUE}[8/8] 启动服务...${NC}"
$DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml up -d
echo -e "${GREEN}✅ 服务已启动${NC}"

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 20

# 健康检查
echo -e "${BLUE}执行健康检查...${NC}"
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 健康检查通过！服务运行正常${NC}"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}⏳ 等待服务启动... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
            sleep 5
        else
            echo -e "${RED}❌ 健康检查失败${NC}"
            echo -e "${YELLOW}查看日志：${NC}"
            $DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml logs --tail=50
            exit 1
        fi
    fi
done

# 显示服务状态
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 获取服务器 IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo -e "服务状态："
$DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml ps
echo ""
echo -e "访问地址："
echo -e "  - 主服务: ${GREEN}http://${SERVER_IP}:8001${NC}"
echo -e "  - 算法公式: ${GREEN}http://${SERVER_IP}:8001/frontend/formula-analysis.html${NC}"
echo -e "  - 运势分析: ${GREEN}http://${SERVER_IP}:8001/frontend/fortune.html${NC}"
echo -e "  - 面相分析 V2: ${GREEN}http://${SERVER_IP}:8001/frontend/face-analysis-v2.html${NC}"
echo -e "  - 办公桌风水: ${GREEN}http://${SERVER_IP}:8001/frontend/desk-fengshui.html${NC}"
echo ""
echo -e "常用命令："
echo -e "  查看日志: ${YELLOW}$DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml logs -f${NC}"
echo -e "  查看状态: ${YELLOW}$DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml ps${NC}"
echo -e "  重启服务: ${YELLOW}$DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml restart${NC}"
echo -e "  停止服务: ${YELLOW}$DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml down${NC}"
echo ""

