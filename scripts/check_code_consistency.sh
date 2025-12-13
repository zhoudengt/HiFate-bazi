#!/bin/bash
# 代码一致性检查脚本
# 用途：检查本地、GitHub、服务器代码是否一致
# 使用：bash scripts/check_code_consistency.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 服务器配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# SSH 执行函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    fi
}

echo "========================================"
echo "🔍 代码一致性检查"
echo "========================================"
echo ""

# 1. 检查本地代码
echo "📋 检查本地代码..."
LOCAL_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "无法获取")
LOCAL_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "无法获取")
LOCAL_STATUS=$(git status --porcelain 2>/dev/null || echo "")

if [ -n "$LOCAL_STATUS" ]; then
    echo -e "${YELLOW}⚠️  本地有未提交的更改：${NC}"
    echo "$LOCAL_STATUS" | sed 's/^/  /'
else
    echo -e "${GREEN}✅ 本地无未提交的更改${NC}"
fi

echo "  分支: $LOCAL_BRANCH"
echo "  提交: $LOCAL_COMMIT"
echo ""

# 2. 检查 GitHub 代码
echo "📋 检查 GitHub 代码..."
GITHUB_COMMIT=$(git ls-remote origin master 2>/dev/null | cut -f1 || echo "无法获取")

if [ "$GITHUB_COMMIT" = "无法获取" ]; then
    echo -e "${RED}❌ 无法连接到 GitHub${NC}"
else
    echo "  提交: $GITHUB_COMMIT"
    if [ "$LOCAL_COMMIT" = "$GITHUB_COMMIT" ]; then
        echo -e "${GREEN}✅ 本地与 GitHub 一致${NC}"
    else
        echo -e "${YELLOW}⚠️  本地与 GitHub 不一致${NC}"
        echo "  本地:  $LOCAL_COMMIT"
        echo "  GitHub: $GITHUB_COMMIT"
    fi
fi
echo ""

# 3. 检查服务器代码（Node1）
echo "📋 检查 Node1 代码..."
NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null || echo "无法获取")
NODE1_STATUS=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git status --porcelain" 2>/dev/null || echo "")

if [ "$NODE1_COMMIT" = "无法获取" ]; then
    echo -e "${RED}❌ 无法连接到 Node1${NC}"
else
    echo "  提交: $NODE1_COMMIT"
    if [ -n "$NODE1_STATUS" ]; then
        echo -e "${YELLOW}⚠️  Node1 有本地未提交的更改：${NC}"
        echo "$NODE1_STATUS" | sed 's/^/  /'
    else
        echo -e "${GREEN}✅ Node1 无本地未提交的更改${NC}"
    fi
    
    if [ "$NODE1_COMMIT" = "$GITHUB_COMMIT" ] && [ "$GITHUB_COMMIT" != "无法获取" ]; then
        echo -e "${GREEN}✅ Node1 与 GitHub 一致${NC}"
    elif [ "$GITHUB_COMMIT" != "无法获取" ]; then
        echo -e "${YELLOW}⚠️  Node1 与 GitHub 不一致${NC}"
    fi
fi
echo ""

# 4. 检查服务器代码（Node2）
echo "📋 检查 Node2 代码..."
NODE2_COMMIT=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null || echo "无法获取")
NODE2_STATUS=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git status --porcelain" 2>/dev/null || echo "")

if [ "$NODE2_COMMIT" = "无法获取" ]; then
    echo -e "${RED}❌ 无法连接到 Node2${NC}"
else
    echo "  提交: $NODE2_COMMIT"
    if [ -n "$NODE2_STATUS" ]; then
        echo -e "${YELLOW}⚠️  Node2 有本地未提交的更改：${NC}"
        echo "$NODE2_STATUS" | sed 's/^/  /'
    else
        echo -e "${GREEN}✅ Node2 无本地未提交的更改${NC}"
    fi
    
    if [ "$NODE2_COMMIT" = "$GITHUB_COMMIT" ] && [ "$GITHUB_COMMIT" != "无法获取" ]; then
        echo -e "${GREEN}✅ Node2 与 GitHub 一致${NC}"
    elif [ "$GITHUB_COMMIT" != "无法获取" ]; then
        echo -e "${YELLOW}⚠️  Node2 与 GitHub 不一致${NC}"
    fi
fi
echo ""

# 5. 总结
echo "========================================"
echo "📊 一致性检查总结"
echo "========================================"

ALL_CONSISTENT=true

# 检查本地与GitHub
if [ "$LOCAL_COMMIT" != "$GITHUB_COMMIT" ] && [ "$GITHUB_COMMIT" != "无法获取" ]; then
    echo -e "${YELLOW}⚠️  本地与 GitHub 不一致${NC}"
    ALL_CONSISTENT=false
fi

# 检查Node1与GitHub
if [ "$NODE1_COMMIT" != "$GITHUB_COMMIT" ] && [ "$GITHUB_COMMIT" != "无法获取" ] && [ "$NODE1_COMMIT" != "无法获取" ]; then
    echo -e "${YELLOW}⚠️  Node1 与 GitHub 不一致${NC}"
    ALL_CONSISTENT=false
fi

# 检查Node2与GitHub
if [ "$NODE2_COMMIT" != "$GITHUB_COMMIT" ] && [ "$GITHUB_COMMIT" != "无法获取" ] && [ "$NODE2_COMMIT" != "无法获取" ]; then
    echo -e "${YELLOW}⚠️  Node2 与 GitHub 不一致${NC}"
    ALL_CONSISTENT=false
fi

# 检查服务器本地更改
if [ -n "$NODE1_STATUS" ] || [ -n "$NODE2_STATUS" ]; then
    echo -e "${YELLOW}⚠️  服务器上有本地未提交的更改${NC}"
    ALL_CONSISTENT=false
fi

if [ "$ALL_CONSISTENT" = true ]; then
    echo -e "${GREEN}✅ 代码一致性检查通过！${NC}"
    echo ""
    echo "所有环境代码版本一致："
    echo "  本地:  $LOCAL_COMMIT"
    echo "  GitHub: $GITHUB_COMMIT"
    echo "  Node1:  $NODE1_COMMIT"
    echo "  Node2:  $NODE2_COMMIT"
    exit 0
else
    echo -e "${RED}❌ 代码一致性检查失败！${NC}"
    echo ""
    echo "建议操作："
    echo "  1. 如果有未提交的更改，先提交：git add . && git commit -m '...'"
    echo "  2. 推送到 GitHub：git push origin master"
    echo "  3. 在服务器上拉取：ssh root@server 'cd /opt/HiFate-bazi && git pull origin master'"
    echo "  4. 或使用增量部署脚本：bash deploy/scripts/incremental_deploy_production.sh"
    exit 1
fi

