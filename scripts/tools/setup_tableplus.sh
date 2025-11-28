#!/bin/bash
# TablePlus 快速配置脚本

echo "=========================================="
echo "TablePlus 连接配置"
echo "=========================================="
echo ""

# 检查 TablePlus 是否安装
if [ ! -d "/Applications/TablePlus.app" ]; then
    echo "❌ TablePlus 未安装，请先安装 TablePlus"
    exit 1
fi

echo "✓ TablePlus 已安装"
echo ""

# 打开 TablePlus
echo "正在打开 TablePlus..."
open -a TablePlus

sleep 2

echo ""
echo "=========================================="
echo "请在 TablePlus 中创建以下连接："
echo "=========================================="
echo ""
echo "【MySQL 连接】"
echo "  名称: HiFate MySQL"
echo "  主机: localhost"
echo "  端口: 3306"
echo "  用户: root"
echo "  密码: 123456"
echo "  数据库: hifate_bazi"
echo ""
echo "【Redis 连接】"
echo "  名称: HiFate Redis"
echo "  主机: localhost"
echo "  端口: 6379"
echo "  密码: (留空)"
echo ""
echo "=========================================="
echo "快速创建连接（使用 URL Scheme）"
echo "=========================================="
echo ""

# MySQL 连接 URL
mysql_url="tableplus://?name=HiFate%20MySQL&host=localhost&port=3306&user=root&password=123456&database=hifate_bazi"
echo "正在创建 MySQL 连接..."
open "$mysql_url" 2>/dev/null || echo "⚠ 请手动创建 MySQL 连接"

sleep 1

# Redis 连接 URL
redis_url="tableplus://?name=HiFate%20Redis&host=localhost&port=6379"
echo "正在创建 Redis 连接..."
open "$redis_url" 2>/dev/null || echo "⚠ 请手动创建 Redis 连接"

echo ""
echo "=========================================="
echo "连接信息已显示，请按照上述信息配置"
echo "=========================================="








































