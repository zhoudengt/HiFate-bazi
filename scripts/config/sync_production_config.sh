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
AUTO_RESTART=false
VERIFY_CONFIG=false
ROLLBACK=false

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

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
        --auto-restart)
            AUTO_RESTART=true
            shift
            ;;
        --verify)
            VERIFY_CONFIG=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
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

# 配置验证（如果启用）
if [ "$VERIFY_CONFIG" = true ]; then
    echo ""
    echo "🔍 验证配置是否生效..."
    echo "----------------------------------------"
    
    # 验证bot_id等关键配置
    VERIFY_RESULT=$(ssh_exec "cd $PROJECT_DIR && source .env 2>/dev/null && \
        python3 << 'EOF'
import os
import sys
try:
    # 检查关键配置是否存在
    bot_id = os.getenv('COZE_BOT_ID', '')
    intent_bot_id = os.getenv('INTENT_BOT_ID', '')
    fortune_bot_id = os.getenv('FORTUNE_ANALYSIS_BOT_ID', '')
    
    print('✅ 配置验证通过')
    if bot_id:
        print(f'  COZE_BOT_ID: {bot_id[:20]}...')
    if intent_bot_id:
        print(f'  INTENT_BOT_ID: {intent_bot_id[:20]}...')
    if fortune_bot_id:
        print(f'  FORTUNE_ANALYSIS_BOT_ID: {fortune_bot_id[:20]}...')
except Exception as e:
    print(f'❌ 配置验证失败: {e}')
    sys.exit(1)
EOF" 2>&1)
    
    if echo "$VERIFY_RESULT" | grep -q "❌"; then
        echo -e "${RED}$VERIFY_RESULT${NC}"
        echo -e "${RED}❌ 配置验证失败${NC}"
        echo ""
        echo "正在恢复备份..."
        ssh_exec "cd $PROJECT_DIR && mv $BACKUP_FILE .env 2>/dev/null || true"
        exit 1
    else
        echo "$VERIFY_RESULT"
    fi
fi

# 自动重启服务（如果启用）
if [ "$AUTO_RESTART" = true ]; then
    echo ""
    echo "🔄 自动重启相关服务..."
    echo "----------------------------------------"
    
    # 检测配置变更类型，决定需要重启哪些服务
    RESTART_SERVICES=""
    
    # 检查是否修改了bot_id等应用配置
    if grep -q "BOT_ID\|COZE_ACCESS_TOKEN" "$LOCAL_ENV"; then
        RESTART_SERVICES="web"
    fi
    
    # 检查是否修改了数据库配置
    if grep -q "MYSQL_\|REDIS_" "$LOCAL_ENV"; then
        if [ -n "$RESTART_SERVICES" ]; then
            RESTART_SERVICES="$RESTART_SERVICES mysql redis"
        else
            RESTART_SERVICES="mysql redis"
        fi
    fi
    
    if [ -n "$RESTART_SERVICES" ]; then
        echo "需要重启的服务: $RESTART_SERVICES"
        for service in $RESTART_SERVICES; do
            echo "  重启 $service..."
            ssh_exec "cd $PROJECT_DIR/deploy/docker && docker-compose restart $service 2>&1" || {
                echo -e "${YELLOW}⚠️  重启 $service 失败，继续执行...${NC}"
            }
        done
        echo -e "${GREEN}✅ 服务重启完成${NC}"
    else
        echo "无需重启服务"
    fi
else
    # 提示需要重启的服务
    echo ""
    echo -e "${YELLOW}⚠️  注意：配置变更后可能需要重启相关服务${NC}"
    echo "如果配置变更影响以下服务，请重启："
    echo "  - Web服务（修改了应用配置，如bot_id）"
    echo "  - 微服务（修改了gRPC服务地址）"
    echo "  - 数据库/Redis服务（修改了数据库配置）"
    echo ""
    echo "重启命令示例："
    echo "  bash scripts/config/sync_production_config.sh --node $NODE --auto-restart"
fi

# 配置回滚功能
if [ "$ROLLBACK" = true ]; then
    echo ""
    echo "🔄 回滚配置..."
    echo "----------------------------------------"
    
    # 查找最新的备份文件
    LATEST_BACKUP=$(ssh_exec "cd $PROJECT_DIR && ls -t .env.backup.* 2>/dev/null | head -1")
    
    if [ -z "$LATEST_BACKUP" ]; then
        echo -e "${RED}❌ 未找到备份文件，无法回滚${NC}"
        exit 1
    fi
    
    echo "回滚到: $LATEST_BACKUP"
    ssh_exec "cd $PROJECT_DIR && cp $LATEST_BACKUP .env" || {
        echo -e "${RED}❌ 回滚失败${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✅ 配置回滚成功${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}✅ 配置同步完成${NC}"
echo "========================================"
echo ""
echo -e "${YELLOW}💡 提示：${NC}"
echo "  - 如需验证配置是否生效，使用: --verify"
echo "  - 如需自动重启服务，使用: --auto-restart"
echo "  - 如需回滚配置，使用: --rollback"
echo ""

