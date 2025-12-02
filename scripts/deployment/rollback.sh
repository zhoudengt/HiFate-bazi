#!/bin/bash
# ============================================
# 数据库回滚脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# 回滚脚本目录
ROLLBACK_DIR="$PROJECT_ROOT/scripts/migration/rollback"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   数据库回滚工具${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查回滚脚本目录
if [ ! -d "$ROLLBACK_DIR" ]; then
    echo -e "${YELLOW}⚠️  回滚脚本目录不存在，创建中...${NC}"
    mkdir -p "$ROLLBACK_DIR"
fi

# 列出可用的回滚脚本
echo -e "${BLUE}可用的回滚脚本：${NC}"
echo ""

rollback_scripts=($(ls -1t "$ROLLBACK_DIR"/*.sql 2>/dev/null | head -10))
if [ ${#rollback_scripts[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠️  没有找到回滚脚本${NC}"
    echo ""
    echo "回滚脚本应放在: $ROLLBACK_DIR/"
    echo "文件名格式: rollback_YYYYMMDD_HHMMSS_description.sql"
    exit 0
fi

# 显示回滚脚本列表
for i in "${!rollback_scripts[@]}"; do
    script="${rollback_scripts[$i]}"
    script_name=$(basename "$script")
    echo "  $((i+1)). $script_name"
done
echo "  0. 退出"
echo ""

# 选择回滚脚本
read -p "请选择要执行的回滚脚本 [0-${#rollback_scripts[@]}]: " choice

if [ "$choice" == "0" ] || [ -z "$choice" ]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

if [ "$choice" -lt 1 ] || [ "$choice" -gt ${#rollback_scripts[@]} ]; then
    echo -e "${RED}❌ 无效的选择${NC}"
    exit 1
fi

selected_script="${rollback_scripts[$((choice-1))]}"
script_name=$(basename "$selected_script")

echo ""
echo -e "${YELLOW}选中的回滚脚本: ${script_name}${NC}"
echo ""

# 确认执行
read -p "确认执行回滚？这将修改数据库！[y/N]: " confirm
if [[ $confirm != "y" && $confirm != "Y" ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

# 读取数据库配置
if [ -f ".env" ]; then
    source .env
fi

MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-${MYSQL_ROOT_PASSWORD:-123456}}"
MYSQL_DATABASE="${MYSQL_DATABASE:-hifate_bazi}"

echo ""
echo -e "${BLUE}执行回滚...${NC}"
echo -e "  数据库: ${MYSQL_DATABASE}@${MYSQL_HOST}:${MYSQL_PORT}"
echo ""

# 执行回滚脚本
if command -v mysql &> /dev/null; then
    mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
        "$MYSQL_DATABASE" < "$selected_script"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 回滚成功${NC}"
        
        # 记录回滚日志
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 执行回滚: $script_name" >> "$ROLLBACK_DIR/rollback.log"
    else
        echo -e "${RED}❌ 回滚失败${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ mysql 命令未找到，请安装 MySQL 客户端${NC}"
    exit 1
fi

echo ""

