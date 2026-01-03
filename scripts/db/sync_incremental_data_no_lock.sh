#!/bin/bash
# 无锁表增量数据同步脚本（Shell包装）
# 调用Python脚本进行增量数据同步，避免锁表问题
#
# 使用方法：
#   bash scripts/db/sync_incremental_data_no_lock.sh [--node node1|node2] [--tables table1,table2] [--dry-run]
#
# 选项：
#   --node: 节点名称（node1 或 node2），默认同步到node1
#   --tables: 要同步的表列表（逗号分隔），默认同步所有表
#   --dry-run: 预览模式，不执行实际同步

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
NODE="node1"
TABLES=""
DRY_RUN=false

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
SSH_USER="root"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --node)
            NODE="$2"
            shift 2
            ;;
        --tables)
            TABLES="$2"
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
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 ${SSH_USER}@${TARGET_IP} "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 ${SSH_USER}@${TARGET_IP} "$cmd"
    fi
}

# SCP 上传函数
scp_file() {
    local local_file="$1"
    local remote_file="$2"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 "$local_file" ${SSH_USER}@${TARGET_IP}:"$remote_file"
    else
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 "$local_file" ${SSH_USER}@${TARGET_IP}:"$remote_file"
    fi
}

echo "============================================================"
echo "  无锁表增量数据同步工具 - $NODE"
echo "============================================================"
echo "节点: $NODE ($TARGET_IP)"
echo "模式: $([ "$DRY_RUN" = true ] && echo "预览模式（不执行）" || echo "执行模式")"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
if [ -n "$TABLES" ]; then
    echo "表列表: $TABLES"
fi
echo "============================================================"
echo ""

# 步骤1: 对比数据（可选）
echo -e "${BLUE}📊 第一步：对比数据${NC}"
echo "----------------------------------------"

COMPARE_ARGS="--compare --node $NODE"
if [ -n "$TABLES" ]; then
    COMPARE_ARGS="$COMPARE_ARGS --tables $TABLES"
fi

if python3 "$PROJECT_ROOT/scripts/db/sync_incremental_data_no_lock.py" $COMPARE_ARGS; then
    echo -e "${GREEN}✅ 数据对比完成${NC}"
else
    echo -e "${YELLOW}⚠️  数据对比失败，继续执行...${NC}"
fi

echo ""

# 步骤2: 检查生产环境中不存在的表
echo -e "${BLUE}🔍 第二步：检查生产环境表结构${NC}"
echo "----------------------------------------"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 获取生产环境MySQL容器
MYSQL_CONTAINER=$(ssh_exec "docker ps --format '{{.Names}}' | grep -E 'hifate-mysql-master|hifate-mysql-slave|hifate-mysql' | head -1" 2>/dev/null || echo "")
if [ -z "$MYSQL_CONTAINER" ]; then
    MYSQL_CONTAINER=$(ssh_exec "docker ps --format '{{.Names}}' | grep -i mysql | head -1" 2>/dev/null || echo "")
fi

# 获取生产环境数据库名和表列表
PROD_TABLES_FILE="/tmp/prod_tables_${TIMESTAMP}.txt"
if [ -n "$MYSQL_CONTAINER" ]; then
    CONTAINER_MYSQL_DATABASE=$(ssh_exec "docker exec ${MYSQL_CONTAINER} env | grep MYSQL_DATABASE | cut -d'=' -f2" 2>/dev/null || echo "")
    if [ -z "$CONTAINER_MYSQL_DATABASE" ]; then
        CONTAINER_MYSQL_DATABASE=$(ssh_exec "cd $PROJECT_DIR && source .env 2>/dev/null && echo \${MYSQL_DATABASE:-hifate_bazi}" 2>/dev/null || echo "hifate_bazi")
    fi
    
    # 获取生产环境中的表列表
    echo "  检查生产环境表..."
    CONTAINER_MYSQL_PASSWORD=$(ssh_exec "docker exec ${MYSQL_CONTAINER} env | grep MYSQL_ROOT_PASSWORD | cut -d'=' -f2" 2>/dev/null || echo "")
    if [ -z "$CONTAINER_MYSQL_PASSWORD" ]; then
        CONTAINER_MYSQL_PASSWORD=$(ssh_exec "cd $PROJECT_DIR && source .env 2>/dev/null && echo \${MYSQL_ROOT_PASSWORD:-Yuanqizhan@163}" 2>/dev/null || echo "Yuanqizhan@163")
    fi
    
    # 使用环境变量传递密码，避免命令行暴露
    PROD_TABLES=$(ssh_exec "docker exec ${MYSQL_CONTAINER} sh -c 'export MYSQL_PWD=\"${CONTAINER_MYSQL_PASSWORD}\" && mysql -uroot ${CONTAINER_MYSQL_DATABASE} -e \"SHOW TABLES\" -N 2>/dev/null | grep -v \"^Warning\"' 2>&1" || echo "")
    
    if [ -n "$PROD_TABLES" ]; then
        echo "$PROD_TABLES" > "$PROD_TABLES_FILE"
        PROD_TABLE_COUNT=$(echo "$PROD_TABLES" | wc -l | tr -d ' ')
        echo "  生产环境表数量: $PROD_TABLE_COUNT"
    else
        echo "  ⚠️  无法获取生产环境表列表，将尝试创建所有表"
        rm -f "$PROD_TABLES_FILE" 2>/dev/null || true
        PROD_TABLES_FILE=""
    fi
else
    echo "  ⚠️  未找到MySQL容器，将尝试创建所有表"
    rm -f "$PROD_TABLES_FILE" 2>/dev/null || true
    PROD_TABLES_FILE=""
fi

# 步骤3: 生成增量SQL（包含表结构和数据）
echo ""
echo -e "${BLUE}📝 第三步：生成增量SQL（包含表结构和数据）${NC}"
echo "----------------------------------------"

SQL_FILE="/tmp/hifate_incremental_sync_${TIMESTAMP}.sql"

SYNC_ARGS="--sync --create-missing-tables"
if [ -n "$TABLES" ]; then
    SYNC_ARGS="$SYNC_ARGS --tables $TABLES"
fi
SYNC_ARGS="$SYNC_ARGS --output $SQL_FILE"

# 如果能够获取生产环境表列表，传递给Python脚本
if [ -n "$PROD_TABLES_FILE" ] && [ -f "$PROD_TABLES_FILE" ]; then
    export PROD_TABLES_FILE="$PROD_TABLES_FILE"
fi

if python3 "$PROJECT_ROOT/scripts/db/sync_incremental_data_no_lock.py" $SYNC_ARGS; then
    if [ ! -f "$SQL_FILE" ]; then
        echo -e "${RED}❌ SQL文件生成失败${NC}"
        [ -n "$PROD_TABLES_FILE" ] && rm -f "$PROD_TABLES_FILE" 2>/dev/null || true
        exit 1
    fi
    echo -e "${GREEN}✅ SQL文件生成成功${NC}"
    # 清理临时文件
    [ -n "$PROD_TABLES_FILE" ] && rm -f "$PROD_TABLES_FILE" 2>/dev/null || true
else
    echo -e "${RED}❌ SQL文件生成失败${NC}"
    [ -n "$PROD_TABLES_FILE" ] && rm -f "$PROD_TABLES_FILE" 2>/dev/null || true
    exit 1
fi

# 预览模式
if [ "$DRY_RUN" = true ]; then
    echo ""
    echo -e "${YELLOW}⚠️  预览模式：不会执行实际同步${NC}"
    echo "SQL文件: $SQL_FILE"
    echo "文件大小: $(ls -lh "$SQL_FILE" | awk '{print $5}')"
    echo ""
    echo "如需执行同步，请移除 --dry-run 参数："
    echo "  bash scripts/db/sync_incremental_data_no_lock.sh --node $NODE"
    exit 0
fi

# 步骤4: 上传SQL文件到生产环境
echo ""
echo -e "${BLUE}📤 第四步：上传SQL文件到 $NODE${NC}"
echo "----------------------------------------"

REMOTE_SQL_FILE="/tmp/hifate_incremental_sync_${TIMESTAMP}.sql"
scp_file "$SQL_FILE" "$REMOTE_SQL_FILE" || {
    echo -e "${RED}❌ 上传SQL文件失败${NC}"
    exit 1
}
echo -e "${GREEN}✅ SQL文件上传成功${NC}"

# 步骤5: 执行SQL（使用事务，无锁表）
echo ""
echo -e "${BLUE}🔄 第五步：执行增量同步（无锁表）${NC}"
echo "----------------------------------------"

# 获取数据库配置（从服务器环境变量）
# 注意：密码可能包含特殊字符，需要特殊处理
DB_CONFIG=$(ssh_exec "cd $PROJECT_DIR && source .env 2>/dev/null || true && \
    echo \"MYSQL_HOST=\${MYSQL_HOST:-localhost}\" && \
    echo \"MYSQL_PORT=\${MYSQL_PORT:-3306}\" && \
    echo \"MYSQL_USER=\${MYSQL_USER:-root}\" && \
    echo \"MYSQL_PASSWORD=\${MYSQL_PASSWORD:-Yuanqizhan@163}\" && \
    echo \"MYSQL_DATABASE=\${MYSQL_DATABASE:-hifate_bazi}\" && \
    echo \"MYSQL_ROOT_PASSWORD=\${MYSQL_ROOT_PASSWORD:-Yuanqizhan@163}\"")

MYSQL_HOST=$(echo "$DB_CONFIG" | grep "^MYSQL_HOST=" | cut -d'=' -f2- | tr -d '\r')
MYSQL_PORT=$(echo "$DB_CONFIG" | grep "^MYSQL_PORT=" | cut -d'=' -f2- | tr -d '\r')
MYSQL_USER=$(echo "$DB_CONFIG" | grep "^MYSQL_USER=" | cut -d'=' -f2- | tr -d '\r')
# 优先使用MYSQL_PASSWORD，如果没有则使用MYSQL_ROOT_PASSWORD
MYSQL_PASSWORD=$(echo "$DB_CONFIG" | grep "^MYSQL_PASSWORD=" | cut -d'=' -f2- | tr -d '\r')
if [ -z "$MYSQL_PASSWORD" ] || [ "$MYSQL_PASSWORD" = "Yuanqizhan@163" ]; then
    MYSQL_PASSWORD=$(echo "$DB_CONFIG" | grep "^MYSQL_ROOT_PASSWORD=" | cut -d'=' -f2- | tr -d '\r')
fi
MYSQL_DATABASE=$(echo "$DB_CONFIG" | grep "^MYSQL_DATABASE=" | cut -d'=' -f2- | tr -d '\r')

# 执行SQL（尝试多种方式：Docker容器、mysql命令、Python脚本）
echo "执行SQL脚本（使用事务，无锁表）..."

# 方式1：尝试使用Docker容器（如果MySQL在Docker中）
# 优先使用 hifate-mysql-master，如果没有则使用其他MySQL容器
MYSQL_CONTAINER=$(ssh_exec "docker ps --format '{{.Names}}' | grep -E 'hifate-mysql-master|hifate-mysql-slave|hifate-mysql' | head -1" 2>/dev/null || echo "")
if [ -z "$MYSQL_CONTAINER" ]; then
    MYSQL_CONTAINER=$(ssh_exec "docker ps --format '{{.Names}}' | grep -i mysql | head -1" 2>/dev/null || echo "")
fi

if [ -n "$MYSQL_CONTAINER" ]; then
    echo "  使用Docker容器: $MYSQL_CONTAINER"
    # 从容器环境变量获取MySQL root密码和数据库名
    CONTAINER_MYSQL_PASSWORD=$(ssh_exec "docker exec ${MYSQL_CONTAINER} env | grep MYSQL_ROOT_PASSWORD | cut -d'=' -f2" 2>/dev/null || echo "")
    CONTAINER_MYSQL_DATABASE=$(ssh_exec "docker exec ${MYSQL_CONTAINER} env | grep MYSQL_DATABASE | cut -d'=' -f2" 2>/dev/null || echo "")
    
    # 如果容器内没有环境变量，尝试从.env文件读取
    if [ -z "$CONTAINER_MYSQL_PASSWORD" ]; then
        CONTAINER_MYSQL_PASSWORD=$(ssh_exec "cd $PROJECT_DIR && source .env 2>/dev/null && echo \${MYSQL_ROOT_PASSWORD:-Yuanqizhan@163}" 2>/dev/null || echo "Yuanqizhan@163")
    fi
    if [ -z "$CONTAINER_MYSQL_DATABASE" ]; then
        CONTAINER_MYSQL_DATABASE="$MYSQL_DATABASE"
    fi
    
    echo "  数据库: ${CONTAINER_MYSQL_DATABASE}"
    
    # 执行SQL（使用容器内的密码和数据库名）
    # 注意：使用 --force 参数，即使遇到错误也继续执行
    SYNC_OUTPUT=$(ssh_exec "cat $REMOTE_SQL_FILE | docker exec -i ${MYSQL_CONTAINER} mysql -uroot -p'${CONTAINER_MYSQL_PASSWORD}' \
        --default-character-set=utf8mb4 \
        --force \
        ${CONTAINER_MYSQL_DATABASE} 2>&1" || echo "failed")
    
    # 检查是否有严重错误（排除表不存在的警告）
    if echo "$SYNC_OUTPUT" | grep -q "ERROR" && ! echo "$SYNC_OUTPUT" | grep -q "doesn't exist"; then
        echo "  发现严重错误（非表不存在错误）"
    fi
else
    # 方式2：尝试使用mysql命令
    echo "  尝试使用mysql命令..."
    SYNC_OUTPUT=$(ssh_exec "cd $PROJECT_DIR && \
        mysql -h\${MYSQL_HOST:-localhost} -P\${MYSQL_PORT:-3306} -u\${MYSQL_USER:-root} -p\${MYSQL_PASSWORD:-Yuanqizhan@163} \
        --default-character-set=utf8mb4 \
        \${MYSQL_DATABASE:-hifate_bazi} < $REMOTE_SQL_FILE 2>&1" || echo "failed")
    
    # 方式3：如果mysql命令失败，尝试使用Python脚本
    if echo "$SYNC_OUTPUT" | grep -q "command not found\|failed"; then
        echo "  尝试使用Python脚本..."
        SYNC_OUTPUT=$(ssh_exec "cd $PROJECT_DIR && \
            python3 -c 'import pymysql' 2>/dev/null && \
            python3 << 'PYEOF'
import pymysql
import os
import sys

# 从环境变量读取配置
host = os.getenv('MYSQL_HOST', 'localhost')
port = int(os.getenv('MYSQL_PORT', '3306'))
user = os.getenv('MYSQL_USER', 'root')
password = os.getenv('MYSQL_PASSWORD', 'Yuanqizhan@163')
database = os.getenv('MYSQL_DATABASE', 'hifate_bazi')
sql_file = '$REMOTE_SQL_FILE'

try:
    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset='utf8mb4')
    with conn.cursor() as cursor:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
            # 执行SQL（按语句分割）
            for statement in sql_content.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
                            print(f'Warning: {e}')
            conn.commit()
    conn.close()
    print('✅ SQL执行成功')
except Exception as e:
    print(f'❌ SQL执行失败: {e}')
    sys.exit(1)
PYEOF
" 2>&1 || echo "failed")
    fi
fi

if echo "$SYNC_OUTPUT" | grep -q "failed\|error\|Error"; then
    echo -e "${RED}❌ 数据同步失败${NC}"
    echo "错误信息: $SYNC_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✅ 数据同步成功${NC}"

# 步骤6: 验证同步结果
echo ""
echo -e "${BLUE}🔍 第六步：验证同步结果${NC}"
echo "----------------------------------------"

# 再次对比数据，验证同步结果
COMPARE_ARGS="--compare --node $NODE"
if [ -n "$TABLES" ]; then
    COMPARE_ARGS="$COMPARE_ARGS --tables $TABLES"
fi

if python3 "$PROJECT_ROOT/scripts/db/sync_incremental_data_no_lock.py" $COMPARE_ARGS 2>&1 | grep -q "数据一致\|一致表数"; then
    echo -e "${GREEN}✅ 数据同步验证通过${NC}"
else
    echo -e "${YELLOW}⚠️  数据同步验证未完全通过，请手动检查${NC}"
fi

# 清理远程临时文件
echo ""
echo -e "${BLUE}🧹 清理临时文件${NC}"
echo "----------------------------------------"
ssh_exec "rm -f $REMOTE_SQL_FILE" || true
echo -e "${GREEN}✅ 临时文件已清理${NC}"

# 完成
echo ""
echo "============================================================"
echo -e "${GREEN}✅ 增量数据同步完成！${NC}"
echo "============================================================"
echo ""
echo -e "${YELLOW}💡 建议：${NC}"
echo "  1. 测试接口是否正常"
echo "  2. 如果接口正常，可以清理本地临时SQL文件"
echo ""

