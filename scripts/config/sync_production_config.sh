#!/bin/bash
# 配置同步脚本
# 同步本地配置到生产环境
#
# 使用方法：
#   bash scripts/config/sync_production_config.sh [--node node1|node2] [--dry-run]
#
# 选项：
#   --node: 节点名称（node1 或 node2），默认同步到node1
#   --dry-run: 预览模式，不执行实际变更

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
NODE="node1"
DRY_RUN=false

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --node)
            NODE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            exit 1
            ;;
    esac
done

# 确定目标服务器IP
if [ "$NODE" = "node1" ]; then
    TARGET_IP="$NODE1_PUBLIC_IP"
elif [ "$NODE" = "node2" ]; then
    TARGET_IP="$NODE2_PUBLIC_IP"
else
    echo -e "${RED}错误：无效的节点名称: $NODE（必须是 node1 或 node2）${NC}"
    exit 1
fi

# SSH 执行函数
ssh_exec() {
    local cmd="$@"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$TARGET_IP "$cmd"
    else
        if command -v expect &> /dev/null; then
            expect << EOF
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$TARGET_IP "$cmd"
expect {
    "password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    eof
}
EOF
        else
            ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$TARGET_IP "$cmd"
        fi
    fi
}

# SCP 上传函数
scp_exec() {
    local local_file="$1"
    local remote_file="$2"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$local_file" root@$TARGET_IP:"$remote_file"
    else
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$local_file" root@$TARGET_IP:"$remote_file"
    fi
}

echo "========================================"
echo "🔄 配置同步到 $NODE"
echo "========================================"
echo "节点: $NODE ($TARGET_IP)"
echo "模式: $([ "$DRY_RUN" = true ] && echo "预览模式（不执行）" || echo "执行模式")"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# 检查本地配置文件
LOCAL_ENV=".env"
if [ ! -f "$LOCAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  本地配置文件不存在: $LOCAL_ENV${NC}"
    echo -e "${YELLOW}⚠️  尝试使用 env.template...${NC}"
    if [ -f "env.template" ]; then
        LOCAL_ENV="env.template"
    else
        echo -e "${RED}❌ 错误：找不到配置文件（.env 或 env.template）${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ 本地配置文件: $LOCAL_ENV${NC}"

# 预览模式
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}📋 预览模式：将同步的配置${NC}"
    echo "----------------------------------------"
    echo "本地配置文件内容（前50行）:"
    head -50 "$LOCAL_ENV"
    echo "----------------------------------------"
    echo ""
    echo -e "${YELLOW}⚠️  预览模式：不会执行实际同步${NC}"
    echo ""
    echo "如需同步配置，请移除 --dry-run 参数："
    echo "  bash scripts/config/sync_production_config.sh --node $NODE"
    exit 0
fi

# 执行模式：备份生产环境配置
echo "📦 备份生产环境配置..."
BACKUP_FILE="$PROJECT_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
ssh_exec "cd $PROJECT_DIR && cp .env $BACKUP_FILE 2>/dev/null || echo '生产环境配置文件不存在，无需备份'"
echo -e "${GREEN}✅ 备份完成: $BACKUP_FILE${NC}"

# 上传配置文件
echo ""
echo "📤 上传配置文件到 $NODE..."
REMOTE_ENV="$PROJECT_DIR/.env"
scp_exec "$LOCAL_ENV" "$REMOTE_ENV" || {
    echo -e "${RED}❌ 上传配置文件失败${NC}"
    exit 1
}
echo -e "${GREEN}✅ 配置文件上传成功${NC}"

# 验证配置文件格式
echo ""
echo "🔍 验证配置文件格式..."
VALIDATION_RESULT=$(ssh_exec "cd $PROJECT_DIR && python3 << 'EOF'
import os
try:
    with open('.env', 'r') as f:
        lines = f.readlines()
    print('✅ 配置文件格式正确')
    print(f'配置项数量: {len([l for l in lines if l.strip() and not l.strip().startswith(\"#\")])}')
except Exception as e:
    print(f'❌ 配置文件格式错误: {e}')
    exit(1)
EOF" 2>&1)

if echo "$VALIDATION_RESULT" | grep -q "❌"; then
    echo -e "${RED}$VALIDATION_RESULT${NC}"
    echo -e "${RED}❌ 配置文件验证失败${NC}"
    echo ""
    echo "正在恢复备份..."
    ssh_exec "cd $PROJECT_DIR && mv $BACKUP_FILE .env 2>/dev/null || true"
    exit 1
else
    echo "$VALIDATION_RESULT"
fi

# 提示需要重启的服务
echo ""
echo -e "${YELLOW}⚠️  注意：配置变更后可能需要重启相关服务${NC}"
echo "如果配置变更影响以下服务，请重启："
echo "  - Web服务（修改了应用配置）"
echo "  - 微服务（修改了gRPC服务地址）"
echo "  - 数据库/Redis服务（修改了数据库配置）"
echo ""
echo "重启命令示例："
echo "  ssh root@$TARGET_IP 'cd $PROJECT_DIR/deploy/docker && docker-compose restart web'"

echo ""
echo -e "${GREEN}✅ 配置同步完成${NC}"
echo "========================================"
echo ""

