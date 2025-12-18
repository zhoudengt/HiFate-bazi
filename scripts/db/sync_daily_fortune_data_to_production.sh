#!/bin/bash
# 同步每日运势相关数据到生产环境
# 包括：建除十二神、幸运颜色、六十甲子、十神查询、十神象义、生肖刑冲破害等
#
# 使用方法：
#   bash scripts/db/sync_daily_fortune_data_to_production.sh [--node node1|node2|both]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
NODE="both"  # both, node1, node2

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# MySQL 配置
MYSQL_USER="root"
MYSQL_PASSWORD="Yuanqizhan@163"
MYSQL_DATABASE="hifate_bazi"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --node)
            NODE="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

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

# 从本地数据库导出所有每日运势数据
export_daily_fortune_data() {
    local output_file="/tmp/daily_fortune_data_$(date +%s).sql"
    
    echo "📥 从本地数据库导出每日运势数据..."
    
    # 使用独立的 Python 脚本导出
    python3 scripts/db/export_daily_fortune_data.py --output "$output_file" --database "$MYSQL_DATABASE" 2>&1
    
    local exit_code=$?
    
    # 直接检查文件是否存在（Python脚本会创建文件）
    if [ $exit_code -eq 0 ] && [ -f "$output_file" ]; then
        echo "$output_file"
        return 0
    else
        echo "❌ 数据导出失败 (退出码: $exit_code)" >&2
        return 1
    fi
}

# 导入数据到生产环境
import_to_production() {
    local node_ip=$1
    local node_name=$2
    local sql_file=$3
    
    echo ""
    echo -e "${BLUE}📤 导入数据到 $node_name...${NC}"
    
    # 上传 SQL 文件
    echo "📤 上传 SQL 文件..."
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no "$sql_file" root@$node_ip:/tmp/daily_fortune_data.sql
    else
        scp -o StrictHostKeyChecking=no "$sql_file" root@$node_ip:/tmp/daily_fortune_data.sql
    fi
    
    # 执行 SQL（通过 Docker 容器）
    echo "🔄 执行 SQL 脚本..."
    local mysql_container=$(ssh_exec $node_ip "docker ps --format '{{.Names}}' | grep -i mysql | head -1")
    if [ -z "$mysql_container" ]; then
        echo -e "${RED}❌ 未找到 MySQL 容器${NC}"
        return 1
    fi
    echo "  使用容器: $mysql_container"
    ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE < /tmp/daily_fortune_data.sql && rm /tmp/daily_fortune_data.sql"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $node_name 数据导入成功${NC}"
        
        # 验证数据
        echo "🔍 验证数据..."
        local jianchu_count=$(ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e 'SELECT COUNT(*) as count FROM daily_fortune_jianchu' -N 2>/dev/null | tail -1")
        local jianchu_score_count=$(ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e 'SELECT COUNT(*) as count FROM daily_fortune_jianchu WHERE score IS NOT NULL' -N 2>/dev/null | tail -1")
        local wannianli_count=$(ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e 'SELECT COUNT(*) as count FROM daily_fortune_lucky_color_wannianli' -N 2>/dev/null | tail -1")
        local shishen_count=$(ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e 'SELECT COUNT(*) as count FROM daily_fortune_lucky_color_shishen' -N 2>/dev/null | tail -1")
        
        echo "  建除十二神: $jianchu_count 条（有分数: $jianchu_score_count 条）"
        echo "  幸运颜色-万年历方位: $wannianli_count 条"
        echo "  幸运颜色-十神: $shishen_count 条"
    else
        echo -e "${RED}❌ $node_name 数据导入失败${NC}"
        return 1
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "🔄 同步每日运势数据到生产环境"
    echo "========================================"
    echo ""
    
    # 切换到项目根目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    cd "$PROJECT_ROOT"
    
    # 1. 导出本地数据
    echo -e "${BLUE}📋 第一步：导出本地数据${NC}"
    echo "----------------------------------------"
    
    SQL_FILE=$(export_daily_fortune_data 2>&1 | grep -E '^/tmp/.*\.sql$' | tail -1)
    local export_exit_code=${PIPESTATUS[0]}
    
    # 如果从输出中提取失败，尝试直接查找最近创建的SQL文件
    if [ -z "$SQL_FILE" ] || [ ! -f "$SQL_FILE" ]; then
        SQL_FILE=$(ls -t /tmp/daily_fortune_data_*.sql 2>/dev/null | head -1)
    fi
    
    if [ -n "$SQL_FILE" ] && [ -f "$SQL_FILE" ]; then
        echo -e "${GREEN}✓ 数据导出成功，文件: $SQL_FILE${NC}"
    else
        echo -e "${RED}❌ 数据导出失败${NC}"
        exit 1
    fi
    
    # 2. 导入到生产环境
    echo ""
    echo -e "${BLUE}📋 第二步：导入到生产环境${NC}"
    echo "----------------------------------------"
    
    if [ "$NODE" = "both" ] || [ "$NODE" = "node1" ]; then
        import_to_production "$NODE1_PUBLIC_IP" "Node1" "$SQL_FILE"
    fi
    
    if [ "$NODE" = "both" ] || [ "$NODE" = "node2" ]; then
        import_to_production "$NODE2_PUBLIC_IP" "Node2" "$SQL_FILE"
    fi
    
    # 3. 清理临时文件
    echo ""
    echo "🧹 清理临时文件..."
    rm -f "$SQL_FILE"
    echo -e "${GREEN}✅ 临时文件已清理${NC}"
    
    echo ""
    echo -e "${GREEN}✅ 每日运势数据同步完成${NC}"
}

# 执行主函数
main

