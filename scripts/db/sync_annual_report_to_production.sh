#!/bin/bash
# 年运报告数据库配置同步脚本
# 将年运报告配置（Bot ID和年份）同步到生产环境Docker MySQL
#
# 使用方法：
#   bash scripts/db/sync_annual_report_to_production.sh
#
# 功能：
#   1. 上传SQL脚本到生产服务器（Node1和Node2）
#   2. 在Docker MySQL容器中执行SQL脚本
#   3. 验证配置是否正确写入

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

# MySQL配置（从环境变量读取，默认值）
MYSQL_PASSWORD="${MYSQL_PASSWORD:?MYSQL_PASSWORD env var required}"
MYSQL_DATABASE="${MYSQL_DATABASE:-hifate_bazi}"

# SQL脚本路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SQL_FILE="$SCRIPT_DIR/setup_annual_report_config.sql"

echo "========================================"
echo "  年运报告数据库配置同步工具"
echo "========================================"
echo "Node1: $NODE1_PUBLIC_IP"
echo "Node2: $NODE2_PUBLIC_IP"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# 检查SQL文件是否存在
if [ ! -f "$SQL_FILE" ]; then
    echo -e "${RED}❌ SQL文件不存在: $SQL_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ SQL文件已找到: $SQL_FILE${NC}"
echo ""

# SSH执行函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        if command -v expect &> /dev/null; then
            expect << EOF
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
expect {
    "password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    eof
}
EOF
        else
            ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
        fi
    fi
}

# SCP上传函数
scp_upload() {
    local host=$1
    local local_file=$2
    local remote_file=$3
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no "$local_file" root@$host:"$remote_file"
    else
        scp -o StrictHostKeyChecking=no "$local_file" root@$host:"$remote_file"
    fi
}

# 导入数据到指定节点
import_to_node() {
    local node_ip=$1
    local node_name=$2
    
    echo ""
    echo -e "${BLUE}📤 同步配置到 $node_name ($node_ip)...${NC}"
    
    # 上传SQL文件
    echo "📤 上传SQL文件..."
    scp_upload $node_ip "$SQL_FILE" "/tmp/setup_annual_report_config.sql"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ $node_name SQL文件上传失败${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ SQL文件上传成功${NC}"
    
    # 查找MySQL容器
    echo "🔍 查找MySQL容器..."
    local mysql_container=$(ssh_exec $node_ip "docker ps --format '{{.Names}}' | grep -i mysql | head -1" || echo "")
    
    if [ -z "$mysql_container" ]; then
        echo -e "${YELLOW}⚠️  未找到MySQL容器，尝试直接连接MySQL...${NC}"
        # 尝试直接连接MySQL（非Docker环境）
        ssh_exec $node_ip "mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE < /tmp/setup_annual_report_config.sql && rm -f /tmp/setup_annual_report_config.sql"
    else
        echo "  使用容器: $mysql_container"
        # 在Docker容器中执行SQL
        ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE < /tmp/setup_annual_report_config.sql && rm -f /tmp/setup_annual_report_config.sql"
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $node_name 配置同步成功${NC}"
        
        # 验证配置
        echo "🔍 验证配置..."
        if [ -n "$mysql_container" ]; then
            local bot_id=$(ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e \"SELECT config_value FROM service_configs WHERE config_key='ANNUAL_REPORT_BOT_ID'\" -N 2>/dev/null | tail -1" || echo "")
            local year=$(ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e \"SELECT config_value FROM service_configs WHERE config_key='ANNUAL_REPORT_YEAR'\" -N 2>/dev/null | tail -1" || echo "")
        else
            local bot_id=$(ssh_exec $node_ip "mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e \"SELECT config_value FROM service_configs WHERE config_key='ANNUAL_REPORT_BOT_ID'\" -N 2>/dev/null | tail -1" || echo "")
            local year=$(ssh_exec $node_ip "mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e \"SELECT config_value FROM service_configs WHERE config_key='ANNUAL_REPORT_YEAR'\" -N 2>/dev/null | tail -1" || echo "")
        fi
        
        if [ -n "$bot_id" ] && [ -n "$year" ]; then
            echo "  Bot ID: $bot_id"
            echo "  年份: $year"
            echo -e "${GREEN}✅ $node_name 配置验证通过${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  $node_name 配置验证失败（可能配置未正确写入）${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ $node_name 配置同步失败${NC}"
        return 1
    fi
}

# 主函数
main() {
    echo "开始同步年运报告配置..."
    echo ""
    
    # 同步到Node1
    if import_to_node $NODE1_PUBLIC_IP "Node1"; then
        echo -e "${GREEN}✅ Node1 同步成功${NC}"
    else
        echo -e "${RED}❌ Node1 同步失败${NC}"
        exit 1
    fi
    
    # 同步到Node2
    if import_to_node $NODE2_PUBLIC_IP "Node2"; then
        echo -e "${GREEN}✅ Node2 同步成功${NC}"
    else
        echo -e "${RED}❌ Node2 同步失败${NC}"
        exit 1
    fi
    
    echo ""
    echo "========================================"
    echo -e "${GREEN}✅ 年运报告配置同步完成${NC}"
    echo "========================================"
    echo ""
    echo "配置内容："
    echo "  - ANNUAL_REPORT_BOT_ID: 7593296393016508450"
    echo "  - ANNUAL_REPORT_YEAR: 2026"
    echo ""
    echo "验证命令："
    echo "  ssh root@$NODE1_PUBLIC_IP \"docker exec -i \$(docker ps --format '{{.Names}}' | grep -i mysql | head -1) mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e \\\"SELECT config_key, config_value FROM service_configs WHERE config_key IN ('ANNUAL_REPORT_BOT_ID', 'ANNUAL_REPORT_YEAR')\\\"\""
}

# 执行主函数
main
