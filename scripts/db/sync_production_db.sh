#!/bin/bash
# 数据库同步脚本
# 执行数据库变更并自动生成回滚脚本
#
# 使用方法：
#   bash scripts/db/sync_production_db.sh --node node1 --deployment-id 20250115_143000
#
# 选项：
#   --node: 节点名称（node1 或 node2）
#   --deployment-id: 部署ID（用于查找同步脚本）
#   --dry-run: 预览模式，不执行实际变更

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
NODE=""
DEPLOYMENT_ID=""
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
        --deployment-id)
            DEPLOYMENT_ID="$2"
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

if [ -z "$DEPLOYMENT_ID" ]; then
    echo -e "${RED}错误：必须指定 --deployment-id 参数${NC}"
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

# 查找同步脚本
SYNC_SCRIPT="scripts/db/sync_${DEPLOYMENT_ID}.sql"

if [ ! -f "$SYNC_SCRIPT" ]; then
    echo -e "${YELLOW}⚠️  同步脚本不存在: $SYNC_SCRIPT${NC}"
    echo -e "${YELLOW}⚠️  可能没有数据库变更，跳过数据库同步${NC}"
    exit 0
fi

echo "========================================"
echo "🔄 数据库同步到 $NODE"
echo "========================================"
echo "节点: $NODE ($TARGET_IP)"
echo "部署ID: $DEPLOYMENT_ID"
echo "同步脚本: $SYNC_SCRIPT"
echo "模式: $([ "$DRY_RUN" = true ] && echo "预览模式（不执行）" || echo "执行模式")"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# 检查同步脚本内容
if [ ! -s "$SYNC_SCRIPT" ]; then
    echo -e "${YELLOW}⚠️  同步脚本为空，无需同步${NC}"
    exit 0
fi

# 预览模式
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}📋 预览模式：将执行的 SQL 语句${NC}"
    echo "----------------------------------------"
    cat "$SYNC_SCRIPT"
    echo "----------------------------------------"
    echo -e "${GREEN}✅ 预览完成（未执行实际变更）${NC}"
    exit 0
fi

# 执行模式
echo "📤 上传同步脚本到 $NODE..."
scp_exec() {
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$1" root@$TARGET_IP:"$2"
    else
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$1" root@$TARGET_IP:"$2"
    fi
}

REMOTE_SCRIPT="$PROJECT_DIR/scripts/db/sync_${DEPLOYMENT_ID}.sql"
scp_exec "$SYNC_SCRIPT" "$REMOTE_SCRIPT" || {
    echo -e "${RED}❌ 上传同步脚本失败${NC}"
    exit 1
}
echo -e "${GREEN}✅ 同步脚本上传成功${NC}"

# 执行数据库同步
echo ""
echo "🔄 执行数据库同步..."
echo "----------------------------------------"

# 获取数据库配置（从服务器环境变量）
DB_RESULT=$(ssh_exec "cd $PROJECT_DIR && source .env 2>/dev/null || true && \
    echo \"MYSQL_HOST=\${MYSQL_HOST:-localhost}\" && \
    echo \"MYSQL_PORT=\${MYSQL_PORT:-3306}\" && \
    echo \"MYSQL_USER=\${MYSQL_USER:-root}\" && \
    echo \"MYSQL_PASSWORD=\${MYSQL_PASSWORD:-Yuanqizhan@163}\" && \
    echo \"MYSQL_DATABASE=\${MYSQL_DATABASE:-hifate_bazi}\"")

MYSQL_HOST=$(echo "$DB_RESULT" | grep "MYSQL_HOST=" | cut -d'=' -f2)
MYSQL_PORT=$(echo "$DB_RESULT" | grep "MYSQL_PORT=" | cut -d'=' -f2)
MYSQL_USER=$(echo "$DB_RESULT" | grep "MYSQL_USER=" | cut -d'=' -f2)
MYSQL_PASSWORD=$(echo "$DB_RESULT" | grep "MYSQL_PASSWORD=" | cut -d'=' -f2)
MYSQL_DATABASE=$(echo "$DB_RESULT" | grep "MYSQL_DATABASE=" | cut -d'=' -f2)

# 执行 SQL 脚本
SYNC_OUTPUT=$(ssh_exec "cd $PROJECT_DIR && \
    mysql -h\${MYSQL_HOST:-localhost} -P\${MYSQL_PORT:-3306} -u\${MYSQL_USER:-root} -p\${MYSQL_PASSWORD:-Yuanqizhan@163} \${MYSQL_DATABASE:-hifate_bazi} < $REMOTE_SCRIPT 2>&1" || echo "failed")

if echo "$SYNC_OUTPUT" | grep -q "failed\|error\|Error"; then
    echo -e "${RED}❌ 数据库同步失败${NC}"
    echo "错误信息: $SYNC_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✅ 数据库同步成功${NC}"

# 验证同步结果
echo ""
echo "🔍 验证同步结果..."
echo "----------------------------------------"

# 验证表是否存在
echo "验证表结构同步..."
VALIDATION_SQL="SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name IN ("
TABLE_NAMES=()

# 从同步脚本中提取表名（如果有新增表）
if grep -q "CREATE TABLE" "$SYNC_SCRIPT"; then
    while IFS= read -r line; do
        if [[ "$line" =~ CREATE\ TABLE.*\`([^\`]+)\` ]]; then
            TABLE_NAMES+=("${BASH_REMATCH[1]}")
        fi
    done < "$SYNC_SCRIPT"
fi

if [ ${#TABLE_NAMES[@]} -gt 0 ]; then
    for table in "${TABLE_NAMES[@]}"; do
        TABLE_EXISTS=$(ssh_exec "cd $PROJECT_DIR && \
            mysql -h\${MYSQL_HOST:-localhost} -P\${MYSQL_PORT:-3306} -u\${MYSQL_USER:-root} -p\${MYSQL_PASSWORD:-Yuanqizhan@163} \${MYSQL_DATABASE:-hifate_bazi} -e \"SHOW TABLES LIKE '$table'\" 2>&1" | grep -c "$table" || echo "0")
        if [ "$TABLE_EXISTS" -gt 0 ]; then
            echo -e "  ✅ 表 $table 已创建"
        else
            echo -e "  ❌ 表 $table 创建失败"
        fi
    done
fi

# 提示运行数据一致性验证
echo ""
echo -e "${YELLOW}💡 建议运行数据一致性验证：${NC}"
echo "  python3 scripts/db/verify_data_consistency.py"

echo ""
echo -e "${GREEN}✅ 数据库同步完成${NC}"
echo "========================================"
echo ""

