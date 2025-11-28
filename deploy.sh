#!/bin/bash
# ============================================
# HiFate-bazi 一键部署脚本
# 基于 Gitee（码云）+ 阿里云 ECS
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# 配置区域（请修改为你的实际配置）
# ============================================
SERVER="root@123.57.216.15"              # 阿里云 ECS 地址
SERVER_PORT="22"                          # SSH 端口
REMOTE_PATH="/opt/HiFate-bazi"           # 服务器项目路径
GITEE_REPO="https://gitee.com/zhoudengtang/hifate-prod.git"  # Gitee 仓库地址
BRANCH="master"                           # 分支名
HEALTH_URL="http://localhost:8001/api/v1/health"
HEALTH_TIMEOUT=60

# SSH 命令简化
SSH_CMD="ssh -p $SERVER_PORT $SERVER"
SCP_CMD="scp -P $SERVER_PORT"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   HiFate-bazi 部署工具${NC}"
echo -e "${GREEN}   服务器: $SERVER${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Gitee 已配置
echo -e "Gitee 仓库: ${BLUE}${GITEE_REPO}${NC}"
echo ""

# 选择操作
echo "请选择操作："
echo -e "  ${BLUE}1) 部署到服务器（推荐）${NC}"
echo "     → 本地 push 到 Gitee，服务器 pull 并重启"
echo "  2) 仅推送到 Gitee"
echo "  3) 仅更新服务器（服务器从 Gitee pull）"
echo "  4) 重启服务器服务"
echo "  5) 查看服务器日志"
echo "  6) 初始化服务器环境（首次使用）"
echo ""
read -p "选择 [1/2/3/4/5/6]: " choice

case $choice in
    1)
        echo -e "\n${YELLOW}>>> 完整部署流程${NC}"
        
        # 1. 推送到 Gitee
        echo ""
        echo "📤 推送代码到 Gitee..."
        if ! git remote | grep -q "gitee"; then
            echo "   添加 Gitee 远程仓库..."
            git remote add gitee $GITEE_REPO
        fi
        git push gitee $BRANCH
        
        # 2. 服务器拉取并部署
        echo ""
        echo "🚀 服务器部署中..."
        $SSH_CMD << EOF
cd $REMOTE_PATH

echo "📂 拉取最新代码..."
git pull gitee $BRANCH

echo "🐳 零停机重启服务..."
docker-compose up -d --build --force-recreate

echo ""
echo "🏥 健康检查（最多等待 ${HEALTH_TIMEOUT} 秒）..."
for i in \$(seq 1 $HEALTH_TIMEOUT); do
    if curl -sf $HEALTH_URL > /dev/null 2>&1; then
        echo "✅ 服务健康！耗时 \${i} 秒"
        exit 0
    fi
    sleep 1
    if [ \$((i % 10)) -eq 0 ]; then
        echo "   等待中... \${i}/${HEALTH_TIMEOUT} 秒"
    fi
done

echo "⚠️ 健康检查超时，请检查服务日志"
exit 1
EOF
        
        echo -e "\n${GREEN}✅ 部署完成！${NC}"
        ;;
    
    2)
        echo -e "\n${YELLOW}>>> 推送到 Gitee${NC}"
        if ! git remote | grep -q "gitee"; then
            git remote add gitee $GITEE_REPO
        fi
        git push gitee $BRANCH
        echo -e "\n${GREEN}✅ 已推送到 Gitee${NC}"
        ;;
    
    3)
        echo -e "\n${YELLOW}>>> 服务器更新${NC}"
        $SSH_CMD << EOF
cd $REMOTE_PATH
echo "📂 拉取最新代码..."
git pull gitee $BRANCH

echo "🐳 零停机重启服务..."
docker-compose up -d --build --force-recreate

echo "✅ 更新完成"
EOF
        ;;
    
    4)
        echo -e "\n${YELLOW}>>> 重启服务${NC}"
        $SSH_CMD << EOF
cd $REMOTE_PATH
docker-compose up -d --force-recreate
echo "✅ 服务已重启"
EOF
        ;;
    
    5)
        echo -e "\n${YELLOW}>>> 查看服务器日志${NC}"
        $SSH_CMD "cd $REMOTE_PATH && docker-compose logs -f --tail=100"
        ;;
    
    6)
        echo -e "\n${YELLOW}>>> 初始化服务器环境${NC}"
        echo ""
        echo "将在服务器上执行："
        echo "  1. 创建项目目录: $REMOTE_PATH"
        echo "  2. 克隆 Gitee 仓库"
        echo "  3. 启动 Docker 服务"
        echo ""
        read -p "确认初始化？[y/N]: " confirm
        
        if [[ $confirm == "y" || $confirm == "Y" ]]; then
            $SSH_CMD << EOF
echo "📁 创建项目目录..."
mkdir -p $REMOTE_PATH
cd $REMOTE_PATH

echo "📥 克隆 Gitee 仓库..."
if [ -d ".git" ]; then
    echo "   项目已存在，更新代码..."
    git pull gitee $BRANCH || git pull origin $BRANCH
else
    git clone $GITEE_REPO .
    git remote add gitee $GITEE_REPO 2>/dev/null || true
fi

echo ""
echo "🐳 启动 Docker 服务..."
docker-compose up -d --build

echo ""
echo "=========================================="
echo "✅ 服务器初始化完成！"
echo "=========================================="
echo ""
echo "项目目录: $REMOTE_PATH"
echo "Gitee 仓库: $GITEE_REPO"
echo ""
echo "后续部署只需在本地执行:"
echo "  ./deploy.sh → 选择 1"
echo ""
EOF
        fi
        ;;
    
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "服务器地址: http://123.57.216.15:8001"
echo -e "健康检查:   http://123.57.216.15:8001/api/v1/health"
echo -e "${GREEN}========================================${NC}"
