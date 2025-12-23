#!/bin/bash
# -*- coding: utf-8 -*-
"""
生产环境表检查和更新脚本（双节点）

功能：
1. 在 Node1 和 Node2 上检查并创建表
2. 可选择更新数据

使用方法：
  bash scripts/db/check_and_update_tables_production.sh                    # 只检查表，不更新数据
  bash scripts/db/check_and_update_tables_production.sh --update-data   # 检查表并更新数据
"""

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 节点配置
NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
SSH_USER="root"

# 检查参数
UPDATE_DATA=false
if [ "$1" == "--update-data" ]; then
    UPDATE_DATA=true
fi

echo "============================================================"
echo "生产环境表检查和更新（双节点）"
echo "============================================================"
echo ""

# 函数：在节点上执行脚本
execute_on_node() {
    local node_ip=$1
    local node_name=$2
    local update_flag=$3
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📡 执行节点: $node_name ($node_ip)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 构建命令
    local cmd="cd $PROJECT_DIR && python3 scripts/db/check_and_update_tables_production.py"
    if [ "$update_flag" == "true" ]; then
        cmd="$cmd --update-data"
    fi
    
    # 执行命令
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $SSH_USER@$node_ip "$cmd"; then
        echo -e "${GREEN}✅ $node_name 执行成功${NC}"
        return 0
    else
        echo -e "${RED}❌ $node_name 执行失败${NC}"
        return 1
    fi
}

# 执行 Node1
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 开始执行 Node1..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ! execute_on_node "$NODE1_IP" "Node1" "$UPDATE_DATA"; then
    echo -e "${RED}❌ Node1 执行失败，停止执行${NC}"
    exit 1
fi

# 执行 Node2
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 开始执行 Node2..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ! execute_on_node "$NODE2_IP" "Node2" "$UPDATE_DATA"; then
    echo -e "${RED}❌ Node2 执行失败${NC}"
    exit 1
fi

# 完成
echo ""
echo "============================================================"
echo -e "${GREEN}✅ 所有节点执行完成${NC}"
echo "============================================================"

