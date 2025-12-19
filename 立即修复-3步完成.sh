#!/bin/bash
# 立即修复：3 步完成

echo "============================================================"
echo "🔧 立即修复生产环境规则问题（3 步完成）"
echo "============================================================"

PROD_HOST="8.210.52.217"
SQL_FILE="scripts/temp_rules_export.sql"

# 检查 SQL 文件
if [ ! -f "$SQL_FILE" ]; then
    echo "❌ SQL 文件不存在，先导出..."
    python3 scripts/fix_production_rules.py
    if [ ! -f "$SQL_FILE" ]; then
        echo "❌ SQL 文件导出失败"
        exit 1
    fi
fi

echo ""
echo "步骤 1/3: 上传 SQL 文件到生产环境"
echo "============================================================"
echo "执行命令: scp $SQL_FILE root@${PROD_HOST}:/tmp/rules_import.sql"
echo "（需要输入 SSH 密码）"
echo ""
read -p "按 Enter 继续，或 Ctrl+C 取消..."

scp "$SQL_FILE" root@${PROD_HOST}:/tmp/rules_import.sql

if [ $? -ne 0 ]; then
    echo "❌ 上传失败"
    exit 1
fi

echo "✅ 上传成功"

echo ""
echo "步骤 2/3: 执行 SQL 并清除缓存"
echo "============================================================"
echo "执行命令: ssh root@${PROD_HOST} '...'"
echo "（需要输入 SSH 密码）"
echo ""
read -p "按 Enter 继续，或 Ctrl+C 取消..."

ssh root@${PROD_HOST} << 'EOF'
cd /opt/HiFate-bazi
echo "🔄 执行 SQL..."
docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql
if [ $? -eq 0 ]; then
    echo "✅ SQL 执行成功"
    echo "🧹 清除缓存..."
    curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check
    echo ""
    echo "✅ 缓存已清除"
else
    echo "❌ SQL 执行失败"
    exit 1
fi
EOF

if [ $? -ne 0 ]; then
    echo "❌ 执行失败"
    exit 1
fi

echo ""
echo "步骤 3/3: 验证修复结果"
echo "============================================================"
echo "⏳ 等待 5 秒让规则重新加载..."
sleep 5

bash scripts/verify_fix.sh

echo ""
echo "============================================================"
echo "✅ 修复完成！"
echo "============================================================"

