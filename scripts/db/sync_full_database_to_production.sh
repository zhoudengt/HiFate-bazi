#!/bin/bash
# 完整数据库同步脚本
# 将本地数据库的所有表和数据同步到生产环境（Node1 和 Node2）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 本地数据库配置（从环境变量读取，或使用默认值）
LOCAL_MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
LOCAL_MYSQL_PORT="${MYSQL_PORT:-3306}"
LOCAL_MYSQL_USER="${MYSQL_USER:-root}"
LOCAL_MYSQL_PASS="${MYSQL_PASSWORD:-${MYSQL_ROOT_PASSWORD:-123456}}"
LOCAL_DB="${MYSQL_DATABASE:-hifate_bazi}"

# 生产环境配置
NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
SSH_USER="root"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
PROJECT_DIR="/opt/HiFate-bazi"
PROD_DB="${MYSQL_DATABASE:-hifate_bazi}"

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="/tmp/hifate_db_full_sync_${TIMESTAMP}.sql"
BACKUP_DIR="/tmp/hifate_db_backups"

# 自动模式（跳过交互式提示）
AUTO_MODE=false
if [ "$1" == "--auto" ] || [ "$1" == "-y" ]; then
    AUTO_MODE=true
fi

echo "============================================================"
echo "   HiFate 完整数据库同步工具（生产环境双节点）"
echo "============================================================"
echo ""
echo -e "${BLUE}本地数据库配置：${NC}"
echo "  主机: $LOCAL_MYSQL_HOST:$LOCAL_MYSQL_PORT"
echo "  用户: $LOCAL_MYSQL_USER"
echo "  数据库: $LOCAL_DB"
echo ""
echo -e "${BLUE}生产环境配置：${NC}"
echo "  Node1: $NODE1_IP"
echo "  Node2: $NODE2_IP"
echo "  数据库: $PROD_DB"
echo ""

# 函数：执行 SSH 命令（使用 sshpass）
ssh_exec() {
    local node_ip=$1
    local cmd=$2
    sshpass -p "${SSH_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 ${SSH_USER}@${node_ip} "$cmd"
}

# 函数：上传文件（使用 sshpass）
scp_file() {
    local node_ip=$1
    local local_file=$2
    local remote_file=$3
    sshpass -p "${SSH_PASSWORD}" scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 "$local_file" ${SSH_USER}@${node_ip}:"$remote_file"
}

# 函数：获取生产环境 MySQL 配置
get_prod_mysql_config() {
    local node_ip=$1
    local config=$(ssh_exec "$node_ip" "cd $PROJECT_DIR && source .env 2>/dev/null || true && \
        echo \"MYSQL_HOST=\${MYSQL_HOST:-localhost}\" && \
        echo \"MYSQL_PORT=\${MYSQL_PORT:-3306}\" && \
        echo \"MYSQL_USER=\${MYSQL_USER:-root}\" && \
        echo \"MYSQL_PASSWORD=\${MYSQL_PASSWORD:?MYSQL_PASSWORD env var required}\" && \
        echo \"MYSQL_DATABASE=\${MYSQL_DATABASE:-hifate_bazi}\"")
    
    echo "$config" | grep "MYSQL_HOST=" | cut -d'=' -f2
    echo "$config" | grep "MYSQL_PORT=" | cut -d'=' -f2
    echo "$config" | grep "MYSQL_USER=" | cut -d'=' -f2
    echo "$config" | grep "MYSQL_PASSWORD=" | cut -d'=' -f2
    echo "$config" | grep "MYSQL_DATABASE=" | cut -d'=' -f2
}

# 函数：备份生产环境数据库
backup_prod_database() {
    local node_ip=$1
    local node_name=$2
    
    echo -e "${YELLOW}📦 备份 $node_name 数据库...${NC}"
    
    # 获取 MySQL 配置
    local config=($(get_prod_mysql_config "$node_ip"))
    local mysql_host="${config[0]}"
    local mysql_port="${config[1]}"
    local mysql_user="${config[2]}"
    local mysql_pass="${config[3]}"
    local mysql_db="${config[4]}"
    
    local backup_file="${BACKUP_DIR}/backup_${node_name}_${TIMESTAMP}.sql"
    
    # 创建备份目录
    ssh_exec "$node_ip" "mkdir -p $BACKUP_DIR"
    
    # 执行备份
    if ssh_exec "$node_ip" "mysqldump -h${mysql_host} -P${mysql_port} -u${mysql_user} -p${mysql_pass} \
        --default-character-set=utf8mb4 \
        --single-transaction \
        --routines \
        --triggers \
        ${mysql_db} > ${backup_file} 2>&1"; then
        echo -e "${GREEN}  ✅ $node_name 备份成功: ${backup_file}${NC}"
        return 0
    else
        echo -e "${RED}  ❌ $node_name 备份失败${NC}"
        return 1
    fi
}

# 函数：导入数据库到生产环境
import_to_production() {
    local node_ip=$1
    local node_name=$2
    local sql_file=$3
    
    echo -e "${BLUE}📥 导入数据到 $node_name...${NC}"
    
    # 获取 MySQL 配置
    local config=($(get_prod_mysql_config "$node_ip"))
    local mysql_host="${config[0]}"
    local mysql_port="${config[1]}"
    local mysql_user="${config[2]}"
    local mysql_pass="${config[3]}"
    local mysql_db="${config[4]}"
    
    local remote_file="/tmp/hifate_db_sync_${TIMESTAMP}.sql"
    
    # 上传 SQL 文件（重试机制）
    echo "  上传 SQL 文件..."
    local upload_success=false
    for i in {1..3}; do
        if scp_file "$node_ip" "$sql_file" "$remote_file"; then
            upload_success=true
            break
        else
            echo "  上传失败，重试 $i/3..."
            sleep 2
        fi
    done
    
    if [ "$upload_success" = false ]; then
        echo -e "${RED}  ❌ 上传 SQL 文件失败（已重试3次）${NC}"
        return 1
    fi
    
    # 导入数据库（尝试多种方式）
    echo "  导入数据库..."
    
    # 方式1：尝试使用 mysql 命令（查找常见路径）
    local mysql_cmd=""
    for path in "/usr/bin/mysql" "/usr/local/bin/mysql" "/opt/mysql/bin/mysql" "mysql"; do
        if ssh_exec "$node_ip" "command -v $path >/dev/null 2>&1 || [ -f $path ]"; then
            mysql_cmd="$path"
            break
        fi
    done
    
    # 如果找到 mysql 命令，使用它
    if [ -n "$mysql_cmd" ] && [ "$mysql_cmd" != "mysql" ]; then
        echo "  使用 MySQL 客户端: $mysql_cmd"
        local import_output=$(ssh_exec "$node_ip" "$mysql_cmd -h${mysql_host} -P${mysql_port} -u${mysql_user} -p${mysql_pass} \
            --default-character-set=utf8mb4 \
            ${mysql_db} < ${remote_file} 2>&1" || echo "failed")
    else
        # 方式2：尝试使用 Python 脚本（如果 pymysql 可用）
        echo "  尝试使用 Python 脚本..."
        local import_output=$(ssh_exec "$node_ip" "cd $PROJECT_DIR && \
            python3 -c 'import pymysql' 2>/dev/null && \
            python3 scripts/db/import_sql_to_production.py ${remote_file} \
            --host ${mysql_host} --port ${mysql_port} --user ${mysql_user} \
            --password ${mysql_pass} --database ${mysql_db} 2>&1 || echo 'failed'")
        
        # 如果 Python 失败，尝试安装 pymysql 或使用其他方法
        if echo "$import_output" | grep -q "No module named 'pymysql'"; then
            echo "  安装 pymysql..."
            ssh_exec "$node_ip" "pip3 install pymysql --quiet 2>&1 || pip install pymysql --quiet 2>&1" || true
            import_output=$(ssh_exec "$node_ip" "cd $PROJECT_DIR && \
                python3 scripts/db/import_sql_to_production.py ${remote_file} \
                --host ${mysql_host} --port ${mysql_port} --user ${mysql_user} \
                --password ${mysql_pass} --database ${mysql_db} 2>&1" || echo "failed")
        fi
    fi
    
    if echo "$import_output" | grep -q "failed\|error\|Error\|❌"; then
        echo -e "${RED}  ❌ 导入失败: $import_output${NC}"
        return 1
    fi
    
    echo "$import_output"
    
    # 清理远程临时文件
    ssh_exec "$node_ip" "rm -f ${remote_file}"
    
    echo -e "${GREEN}  ✅ $node_name 导入成功${NC}"
    return 0
}

# 函数：验证同步结果
verify_sync_result() {
    local node_ip=$1
    local node_name=$2
    
    echo -e "${BLUE}🔍 验证 $node_name 同步结果...${NC}"
    
    # 获取 MySQL 配置
    local config=($(get_prod_mysql_config "$node_ip"))
    local mysql_host="${config[0]}"
    local mysql_port="${config[1]}"
    local mysql_user="${config[2]}"
    local mysql_pass="${config[3]}"
    local mysql_db="${config[4]}"
    
    # 检查表数量
    local table_count=$(ssh_exec "$node_ip" "mysql -h${mysql_host} -P${mysql_port} -u${mysql_user} -p${mysql_pass} \
        ${mysql_db} -e 'SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = DATABASE()' -N 2>/dev/null" | tail -1 || echo "0")
    
    echo "  表数量: $table_count"
    
    # 检查关键表是否存在
    local key_tables=("bazi_rules" "daily_fortune_jianchu" "daily_fortune_zodiac" "rizhu_liujiazi")
    for table in "${key_tables[@]}"; do
        local exists=$(ssh_exec "$node_ip" "mysql -h${mysql_host} -P${mysql_port} -u${mysql_user} -p${mysql_pass} \
            ${mysql_db} -e 'SHOW TABLES LIKE \"${table}\"' -N 2>/dev/null" | grep -c "$table" || echo "0")
        if [ "$exists" -gt 0 ]; then
            echo -e "  ${GREEN}✅ 表 $table 存在${NC}"
        else
            echo -e "  ${YELLOW}⚠️  表 $table 不存在${NC}"
        fi
    done
    
    # 检查 bazi_rules 表数据量
    local rules_count=$(ssh_exec "$node_ip" "mysql -h${mysql_host} -P${mysql_port} -u${mysql_user} -p${mysql_pass} \
        ${mysql_db} -e 'SELECT COUNT(*) FROM bazi_rules WHERE enabled = 1' -N 2>/dev/null" | tail -1 || echo "0")
    echo "  bazi_rules 启用规则数: $rules_count"
}

# 主函数
main() {
    # 1. 导出本地数据库
    echo -e "${BLUE}📤 第一步：导出本地数据库${NC}"
    echo "----------------------------------------"
    
    echo "正在导出数据库..."
    if mysqldump -h${LOCAL_MYSQL_HOST} -P${LOCAL_MYSQL_PORT} -u${LOCAL_MYSQL_USER} -p${LOCAL_MYSQL_PASS} \
        --default-character-set=utf8mb4 \
        --single-transaction \
        --routines \
        --triggers \
        --add-drop-database \
        --databases ${LOCAL_DB} > "${DUMP_FILE}" 2>&1; then
        local file_size=$(ls -lh "${DUMP_FILE}" | awk '{print $5}')
        echo -e "${GREEN}✅ 导出成功${NC}"
        echo "  文件: ${DUMP_FILE}"
        echo "  大小: ${file_size}"
    else
        echo -e "${RED}❌ 导出失败${NC}"
        exit 1
    fi
    
    # 2. 备份生产环境数据库（可选，但强烈推荐）
    echo ""
    echo -e "${YELLOW}📦 第二步：备份生产环境数据库（推荐）${NC}"
    echo "----------------------------------------"
    if [ "$AUTO_MODE" = true ]; then
        echo "自动模式：跳过备份（加快同步速度）"
        backup_choice="n"
    else
        read -p "是否备份生产环境数据库？(y/N): " backup_choice
    fi
    if [[ "$backup_choice" =~ ^[Yy]$ ]]; then
        backup_prod_database "$NODE1_IP" "Node1" || echo -e "${YELLOW}⚠️  Node1 备份失败，继续执行...${NC}"
        backup_prod_database "$NODE2_IP" "Node2" || echo -e "${YELLOW}⚠️  Node2 备份失败，继续执行...${NC}"
    else
        echo -e "${YELLOW}⚠️  跳过备份（不推荐）${NC}"
    fi
    
    # 3. 同步到 Node1
    echo ""
    echo -e "${BLUE}📥 第三步：同步到 Node1${NC}"
    echo "----------------------------------------"
    if import_to_production "$NODE1_IP" "Node1" "$DUMP_FILE"; then
        verify_sync_result "$NODE1_IP" "Node1"
    else
        echo -e "${RED}❌ Node1 同步失败${NC}"
        exit 1
    fi
    
    # 4. 同步到 Node2
    echo ""
    echo -e "${BLUE}📥 第四步：同步到 Node2${NC}"
    echo "----------------------------------------"
    if import_to_production "$NODE2_IP" "Node2" "$DUMP_FILE"; then
        verify_sync_result "$NODE2_IP" "Node2"
    else
        echo -e "${RED}❌ Node2 同步失败${NC}"
        exit 1
    fi
    
    # 5. 清理临时文件
    echo ""
    echo -e "${BLUE}🧹 第五步：清理临时文件${NC}"
    echo "----------------------------------------"
    if [ "$AUTO_MODE" = true ]; then
        echo "自动模式：保留临时文件（便于检查）"
        cleanup_choice="n"
    else
        read -p "是否删除本地临时 SQL 文件？(Y/n): " cleanup_choice
    fi
    if [[ ! "$cleanup_choice" =~ ^[Nn]$ ]]; then
        rm -f "${DUMP_FILE}"
        echo -e "${GREEN}✅ 临时文件已清理${NC}"
    else
        echo -e "${YELLOW}⚠️  保留临时文件: ${DUMP_FILE}${NC}"
    fi
    
    # 完成
    echo ""
    echo "============================================================"
    echo -e "${GREEN}✅ 数据库同步完成！${NC}"
    echo "============================================================"
    echo ""
    echo -e "${YELLOW}💡 建议：${NC}"
    echo "  1. 测试接口是否正常："
    echo "     curl -X POST http://${NODE1_IP}:8001/api/v1/children-study/stream \\"
    echo "       -H 'Content-Type: application/json' \\"
    echo "       -d '{\"solar_date\": \"1990-01-15\", \"solar_time\": \"12:00\", \"gender\": \"male\"}'"
    echo ""
    echo "  2. 如果接口正常，可以清理备份文件（保留最近3个备份）"
    echo ""
}

# 执行主函数
main

