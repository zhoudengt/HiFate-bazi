#!/bin/bash
# 同步幸运颜色数据到生产环境
# 用途：将本地数据库的幸运颜色数据同步到生产环境双机
#
# 使用方法：
#   bash scripts/db/sync_lucky_colors_to_production.sh [--node node1|node2|both]

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
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

# MySQL 配置
MYSQL_USER="root"
MYSQL_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
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

# 从本地数据库导出数据
export_lucky_colors() {
    local output_file="/tmp/lucky_colors_$(date +%s).sql"
    
    echo "📥 从本地数据库导出幸运颜色数据..." >&2
    
    # 使用独立的 Python 脚本导出（将错误输出到stderr，正常输出到stdout）
    local script_output=$(python3 scripts/db/export_lucky_colors.py --output "$output_file" --database "$MYSQL_DATABASE" 2>&1)
    local exit_code=$?
    
    # 显示脚本输出（除了最后一行文件路径）
    local line_count=$(echo "$script_output" | wc -l | tr -d ' ')
    if [ "$line_count" -gt 1 ]; then
        echo "$script_output" | sed '$d' >&2
    else
        echo "$script_output" >&2
    fi
    
    if [ $exit_code -eq 0 ] && [ -f "$output_file" ]; then
        # 输出文件路径到stdout（供调用者捕获）
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
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no "$sql_file" root@$node_ip:/tmp/lucky_colors.sql
    else
        scp -o StrictHostKeyChecking=no "$sql_file" root@$node_ip:/tmp/lucky_colors.sql
    fi
    
    # 执行 SQL（通过 Docker 容器）
    echo "🔄 执行 SQL 脚本..."
    # 查找 MySQL 容器名称
    local mysql_container=$(ssh_exec $node_ip "docker ps --format '{{.Names}}' | grep -i mysql | head -1")
    if [ -z "$mysql_container" ]; then
        echo -e "${RED}❌ 未找到 MySQL 容器${NC}"
        return 1
    fi
    echo "  使用容器: $mysql_container"
    ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE < /tmp/lucky_colors.sql && rm /tmp/lucky_colors.sql"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $node_name 数据导入成功${NC}"
        
        # 验证数据
        echo "🔍 验证数据..."
        local mysql_container=$(ssh_exec $node_ip "docker ps --format '{{.Names}}' | grep -i mysql | head -1")
        local wannianli_count=$(ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e 'SELECT COUNT(*) as count FROM daily_fortune_lucky_color_wannianli' -N 2>/dev/null | tail -1")
        local shishen_count=$(ssh_exec $node_ip "docker exec -i $mysql_container mysql -uroot -p$MYSQL_PASSWORD $MYSQL_DATABASE -e 'SELECT COUNT(*) as count FROM daily_fortune_lucky_color_shishen' -N 2>/dev/null | tail -1")
        
        echo "  万年历方位: $wannianli_count 条"
        echo "  十神: $shishen_count 条"
    else
        echo -e "${RED}❌ $node_name 数据导入失败${NC}"
        return 1
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "🔄 同步幸运颜色数据到生产环境"
    echo "========================================"
    echo ""
    
    # 1. 导出本地数据
    echo -e "${BLUE}📋 第一步：导出本地数据${NC}"
    echo "----------------------------------------"
    
    # 切换到项目根目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    cd "$PROJECT_ROOT"
    
    SQL_FILE=$(export_lucky_colors)
    local export_exit_code=$?
    
    if [ $export_exit_code -ne 0 ] || [ -z "$SQL_FILE" ] || [ ! -f "$SQL_FILE" ]; then
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
    echo -e "${GREEN}✅ 幸运颜色数据同步完成${NC}"
}

# 执行主函数
main

