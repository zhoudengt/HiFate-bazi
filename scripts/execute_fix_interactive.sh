#!/bin/bash
# 交互式执行修复脚本

set -e

echo "================================================================================"
echo "🔧 执行修复：同步规则到生产环境"
echo "================================================================================"

# 检查 SQL 文件是否存在
SQL_FILE="scripts/temp_rules_export.sql"
if [ ! -f "$SQL_FILE" ]; then
    echo "❌ SQL 文件不存在: $SQL_FILE"
    exit 1
fi

echo ""
echo "✅ SQL 文件已找到: $SQL_FILE ($(du -h "$SQL_FILE" | cut -f1))"
echo ""

# 步骤 1: 上传 SQL 文件
echo "📤 步骤 1: 上传 SQL 文件到生产环境..."
echo "   命令: scp $SQL_FILE root@8.210.52.217:/tmp/rules_import.sql"
echo "   提示: 需要输入服务器密码"
echo ""

read -p "按 Enter 继续（或 Ctrl+C 取消）..." 

scp "$SQL_FILE" root@8.210.52.217:/tmp/rules_import.sql

if [ $? -eq 0 ]; then
    echo "✅ 文件上传成功"
else
    echo "❌ 文件上传失败"
    exit 1
fi

echo ""
echo "📥 步骤 2: 执行 SQL 并清理缓存..."
echo "   命令: ssh root@8.210.52.217 'cd /opt/HiFate-bazi && docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql && curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check'"
echo "   提示: 需要输入服务器密码"
echo ""

read -p "按 Enter 继续（或 Ctrl+C 取消）..." 

ssh root@8.210.52.217 'cd /opt/HiFate-bazi && docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql && curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check'

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SQL 执行成功，缓存已清理"
    echo ""
    echo "🔍 步骤 3: 验证修复结果..."
    echo ""
    
    # 等待几秒让服务生效
    sleep 3
    
    # 运行验证脚本
    python3 scripts/check_status.py
    
    echo ""
    echo "================================================================================"
    echo "✅ 修复完成！"
    echo "================================================================================"
else
    echo ""
    echo "❌ SQL 执行失败，请检查错误信息"
    exit 1
fi

