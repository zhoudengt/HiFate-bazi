#!/bin/bash
# ============================================
# 一次性初始化：在服务器上创建 staging 目录
# ============================================
# 用途：为 Phase 2（代码目录隔离）初始化 staging 仓库
# 执行环境：本地执行，通过 SSH 在服务器上操作
# 零停机：不影响任何运行中的服务
#
# 使用方法：
#   bash deploy/scripts/init_staging.sh              # 在 Node1 上初始化
#   bash deploy/scripts/init_staging.sh --node2      # 在 Node2 上也初始化
#   bash deploy/scripts/init_staging.sh --check      # 只检查状态
# ============================================

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# 加载配置
CONFIG_FILE="${SCRIPT_DIR}/deploy.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# 配置
NODE1_PUBLIC_IP="${NODE1_PUBLIC_IP:-}"
NODE2_PUBLIC_IP="${NODE2_PUBLIC_IP:-}"
NODE2_PRIVATE_IP="${NODE2_PRIVATE_IP:-}"
SSH_PASSWORD="${SSH_PASSWORD:-}"
PROJECT_DIR="${PROJECT_DIR:-/opt/HiFate-bazi}"
STAGING_DIR="${PROJECT_DIR}-staging"
ROLLBACK_DIR="${PROJECT_DIR}-rollback"
GIT_REPO="${GIT_REPO:-https://github.com/zhoudengt/HiFate-bazi}"
GIT_BRANCH="${GIT_BRANCH:-master}"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# SSH 函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    local ssh_alias=""
    if [ "$host" = "$NODE1_PUBLIC_IP" ]; then
        ssh_alias="hifate-node1"
    elif [ "$host" = "$NODE2_PUBLIC_IP" ]; then
        ssh_alias="hifate-node2"
    fi
    
    if [ -n "$ssh_alias" ]; then
        if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no $ssh_alias "$cmd" 2>/dev/null; then
            return 0
        fi
    fi
    
    if [ -n "$SSH_PASSWORD" ] && command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    fi
}

# 参数解析
INIT_NODE2=false
CHECK_ONLY=false

while [ $# -gt 0 ]; do
    case "$1" in
        --node2) INIT_NODE2=true; shift ;;
        --check) CHECK_ONLY=true; shift ;;
        --help|-h)
            echo "初始化 staging 目录"
            echo ""
            echo "用法:"
            echo "  $0              在 Node1 上初始化 staging 目录"
            echo "  $0 --node2      同时在 Node2 上初始化"
            echo "  $0 --check      只检查当前状态"
            exit 0
            ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# 验证配置
if [ -z "$NODE1_PUBLIC_IP" ]; then
    echo -e "${RED}NODE1_PUBLIC_IP 未配置${NC}"
    exit 1
fi

# ==================== 检查模式 ====================

check_node() {
    local host=$1
    local name=$2
    
    echo -e "${BLUE}检查 ${name}...${NC}"
    
    local has_live=$(ssh_exec $host "[ -d $PROJECT_DIR ] && echo 'yes' || echo 'no'" 2>/dev/null)
    local has_staging=$(ssh_exec $host "[ -d $STAGING_DIR ] && echo 'yes' || echo 'no'" 2>/dev/null)
    local has_rollback=$(ssh_exec $host "[ -d $ROLLBACK_DIR ] && echo 'yes' || echo 'no'" 2>/dev/null)
    
    echo "  ${PROJECT_DIR}:          ${has_live}"
    echo "  ${STAGING_DIR}:  ${has_staging}"
    echo "  ${ROLLBACK_DIR}: ${has_rollback}"
    
    if [ "$has_staging" = "yes" ]; then
        local staging_commit=$(ssh_exec $host "cd $STAGING_DIR && git rev-parse --short HEAD 2>/dev/null" || echo "unknown")
        local live_commit=$(ssh_exec $host "cd $PROJECT_DIR && git rev-parse --short HEAD 2>/dev/null" || echo "unknown")
        echo "  staging commit:  $staging_commit"
        echo "  live commit:     $live_commit"
        echo -e "  ${GREEN}staging 已就绪${NC}"
    else
        echo -e "  ${YELLOW}staging 未初始化${NC}"
    fi
    echo ""
}

if [ "$CHECK_ONLY" = "true" ]; then
    echo "========================================"
    echo "Staging 目录状态检查"
    echo "========================================"
    echo ""
    check_node "$NODE1_PUBLIC_IP" "Node1"
    if [ -n "$NODE2_PUBLIC_IP" ]; then
        check_node "$NODE2_PUBLIC_IP" "Node2"
    fi
    exit 0
fi

# ==================== 初始化 Node1 ====================

init_node() {
    local host=$1
    local name=$2
    
    echo -e "${BLUE}在 ${name} 上初始化 staging 目录...${NC}"
    echo "----------------------------------------"
    
    # 检查是否已存在
    local has_staging=$(ssh_exec $host "[ -d $STAGING_DIR ] && echo 'yes' || echo 'no'" 2>/dev/null)
    if [ "$has_staging" = "yes" ]; then
        echo -e "${YELLOW}${name} staging 目录已存在，跳过初始化${NC}"
        echo "如需重新初始化，请先删除: ssh root@${host} 'rm -rf ${STAGING_DIR}'"
        return 0
    fi
    
    # 方式1: 从现有仓库硬链接拷贝（更快，节省磁盘）
    echo "从 ${PROJECT_DIR} 创建 staging 目录（硬链接拷贝）..."
    ssh_exec $host "cp -al $PROJECT_DIR $STAGING_DIR" || {
        # 降级方式2: git clone
        echo -e "${YELLOW}硬链接拷贝失败，使用 git clone...${NC}"
        ssh_exec $host "cd /opt && git clone $GIT_REPO HiFate-bazi-staging" || {
            echo -e "${RED}${name} staging 初始化失败${NC}"
            return 1
        }
    }
    
    # 确保 staging 在正确分支
    ssh_exec $host "cd $STAGING_DIR && git fetch origin && git checkout $GIT_BRANCH && git pull origin $GIT_BRANCH" 2>/dev/null || true
    
    # 创建 rollback 目录（空的，等第一次部署时填充）
    ssh_exec $host "mkdir -p $ROLLBACK_DIR" 2>/dev/null || true
    
    # 验证
    local staging_commit=$(ssh_exec $host "cd $STAGING_DIR && git rev-parse --short HEAD 2>/dev/null" || echo "unknown")
    echo -e "${GREEN}${name} staging 初始化完成 (commit: ${staging_commit})${NC}"
    echo ""
}

echo "========================================"
echo "初始化 Staging 目录"
echo "========================================"
echo ""
echo "这个操作是零停机的，不影响任何运行中的服务。"
echo ""
echo "将创建:"
echo "  ${STAGING_DIR}   - Git 仓库（git pull 在这里）"
echo "  ${ROLLBACK_DIR}  - 回滚备份"
echo ""
echo "容器继续挂载 ${PROJECT_DIR}（不变）"
echo ""

init_node "$NODE1_PUBLIC_IP" "Node1"

if [ "$INIT_NODE2" = "true" ] && [ -n "$NODE2_PUBLIC_IP" ]; then
    init_node "$NODE2_PUBLIC_IP" "Node2"
fi

echo "========================================"
echo -e "${GREEN}初始化完成${NC}"
echo "========================================"
echo ""
echo "下一步："
echo "  1. 验证状态: bash deploy/scripts/init_staging.sh --check"
echo "  2. 使用门控发布: bash deploy/scripts/gated_deploy.sh"
echo "     脚本会自动检测 staging 目录，存在则使用隔离模式"
echo ""
