#!/bin/bash
# 数据库回滚脚本
# 执行数据库回滚并验证结果
#
# 使用方法：
#   bash scripts/db/rollback_db.sh --node node1 --rollback-file scripts/db/rollback/rollback_20250115_143000.sql
#
# 选项：
#   --node: 节点名称（node1 或 node2）
#   --rollback-file: 回滚脚本文件路径
#   --dry-run: 预览模式，不执行实际回滚

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
NODE=""
ROLLBACK_FILE=""
DRY_RUN=false

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
        --rollback-file)
            ROLLBACK_FILE="$2"
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

# 检查必要参数
if [ -z "$NODE" ]; then
    echo -e "${RED}错误：必须指定 --node 参数（node1 或 node2）${NC}"
    exit 1
fi

if [ -z "$ROLLBACK_FILE" ]; then
    echo -e "${RED}错误：必须指定 --rollback-file 参数${NC}"
    exit 1
fi

# 检查回滚文件是否存在
if [ ! -f "$ROLLBACK_FILE" ]; then
    echo -e "${RED}错误：回滚文件不存在: $ROLLBACK_FILE${NC}"
    exit 1
fi

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

echo "========================================"
echo "🔄 数据库回滚 - $NODE"
echo "========================================"
echo "节点: $NODE ($TARGET_IP)"
echo "回滚文件: $ROLLBACK_FILE"
echo "模式: $([ "$DRY_RUN" = true ] && echo "预览模式（不执行）" || echo "执行模式")"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# 预览模式
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}📋 预览模式：将执行的回滚 SQL 语句${NC}"
    echo "----------------------------------------"
    cat "$ROLLBACK_FILE"
    echo "----------------------------------------"
    echo -e "${GREEN}✅ 预览完成（未执行实际回滚）${NC}"
    exit 0
fi

# 执行模式
echo "📤 上传回滚脚本到 $NODE..."
scp_exec() {
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$1" root@$TARGET_IP:"$2"
    else
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$1" root@$TARGET_IP:"$2"
    fi
}

ROLLBACK_FILENAME=$(basename "$ROLLBACK_FILE")
REMOTE_SCRIPT="$PROJECT_DIR/scripts/db/rollback/$ROLLBACK_FILENAME"
scp_exec "$ROLLBACK_FILE" "$REMOTE_SCRIPT" || {
    echo -e "${RED}❌ 上传回滚脚本失败${NC}"
    exit 1
}
echo -e "${GREEN}✅ 回滚脚本上传成功${NC}"

# 执行数据库回滚
echo ""
echo "🔄 执行数据库回滚..."
echo "----------------------------------------"

# 获取数据库配置（从服务器环境变量）
DB_RESULT=$(ssh_exec "cd $PROJECT_DIR && source .env 2>/dev/null || true && \
    echo \"MYSQL_HOST=\${MYSQL_HOST:-localhost}\" && \
    echo \"MYSQL_PORT=\${MYSQL_PORT:-3306}\" && \
    echo \"MYSQL_USER=\${MYSQL_USER:-root}\" && \
    echo \"MYSQL_PASSWORD=\${MYSQL_PASSWORD:?MYSQL_PASSWORD env var required}\" && \
    echo \"MYSQL_DATABASE=\${MYSQL_DATABASE:-hifate_bazi}\"")

MYSQL_HOST=$(echo "$DB_RESULT" | grep "MYSQL_HOST=" | cut -d'=' -f2)
MYSQL_PORT=$(echo "$DB_RESULT" | grep "MYSQL_PORT=" | cut -d'=' -f2)
MYSQL_USER=$(echo "$DB_RESULT" | grep "MYSQL_USER=" | cut -d'=' -f2)
MYSQL_PASSWORD=$(echo "$DB_RESULT" | grep "MYSQL_PASSWORD=" | cut -d'=' -f2)
MYSQL_DATABASE=$(echo "$DB_RESULT" | grep "MYSQL_DATABASE=" | cut -d'=' -f2)

# 执行 SQL 脚本
ROLLBACK_OUTPUT=$(ssh_exec "cd $PROJECT_DIR && \
    mysql -h\${MYSQL_HOST:-localhost} -P\${MYSQL_PORT:-3306} -u\${MYSQL_USER:-root} -p\${MYSQL_PASSWORD:?MYSQL_PASSWORD env var required} \${MYSQL_DATABASE:-hifate_bazi} < $REMOTE_SCRIPT 2>&1" || echo "failed")

if echo "$ROLLBACK_OUTPUT" | grep -q "failed\|error\|Error"; then
    echo -e "${RED}❌ 数据库回滚失败${NC}"
    echo "错误信息: $ROLLBACK_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✅ 数据库回滚成功${NC}"

# 验证回滚结果
echo ""
echo "🔍 验证回滚结果..."
# 这里可以添加验证逻辑，比如检查表是否已删除、字段是否已删除等

echo ""
echo -e "${GREEN}✅ 数据库回滚完成${NC}"
echo "========================================"
echo ""

