#!/bin/bash
# 检查并修复生产环境数据库规则

echo "============================================================"
echo "🔍 检查生产环境数据库规则"
echo "============================================================"

PROD_HOST="8.210.52.217"
PROD_USER="root"
SQL_FILE="scripts/temp_rules_export.sql"

# 检查 SQL 文件
if [ ! -f "$SQL_FILE" ]; then
    echo "❌ SQL 文件不存在: $SQL_FILE"
    echo "💡 先运行: python3 scripts/fix_production_rules.py"
    exit 1
fi

echo ""
echo "步骤 1: 检查生产环境数据库规则数量"
echo "============================================================"

# 通过 SSH 检查生产环境数据库
ssh ${PROD_USER}@${PROD_HOST} << 'EOF'
cd /opt/HiFate-bazi
echo "📊 生产环境数据库规则统计:"
docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi -e "
SELECT 
    rule_type,
    COUNT(*) as total,
    SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count
FROM bazi_rules 
WHERE rule_code LIKE 'FORMULA_%' 
  AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
GROUP BY rule_type
ORDER BY rule_type;
"
EOF

if [ $? -ne 0 ]; then
    echo "❌ 无法连接生产环境，请检查 SSH 配置"
    exit 1
fi

echo ""
echo "============================================================"
echo "步骤 2: 对比本地和生产环境规则数量"
echo "============================================================"

# 获取本地规则数量
echo "📊 本地数据库规则统计:"
mysql -h localhost -u root -p123456 hifate_bazi -e "
SELECT 
    rule_type,
    COUNT(*) as total,
    SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count
FROM bazi_rules 
WHERE rule_code LIKE 'FORMULA_%' 
  AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
GROUP BY rule_type
ORDER BY rule_type;
" 2>/dev/null || echo "⚠️  无法连接本地数据库（可能需要密码）"

echo ""
echo "============================================================"
echo "步骤 3: 同步规则到生产环境"
echo "============================================================"

read -p "是否同步规则到生产环境？(y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "已取消"
    exit 0
fi

# 上传 SQL 文件
echo "📤 上传 SQL 文件..."
scp "$SQL_FILE" ${PROD_USER}@${PROD_HOST}:/tmp/rules_import.sql

if [ $? -ne 0 ]; then
    echo "❌ 上传失败，请检查 SSH 配置"
    exit 1
fi

# 执行 SQL
echo "🔄 执行 SQL..."
ssh ${PROD_USER}@${PROD_HOST} << 'EOF'
cd /opt/HiFate-bazi
docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql
if [ $? -eq 0 ]; then
    echo "✅ SQL 执行成功"
else
    echo "❌ SQL 执行失败"
    exit 1
fi
EOF

if [ $? -ne 0 ]; then
    echo "❌ 同步失败"
    exit 1
fi

# 清除缓存
echo ""
echo "🧹 清除缓存..."
curl -X POST http://${PROD_HOST}:8001/api/v1/hot-reload/check

# 等待
echo ""
echo "⏳ 等待 5 秒让规则重新加载..."
sleep 5

# 验证
echo ""
echo "============================================================"
echo "步骤 4: 验证修复结果"
echo "============================================================"

bash scripts/verify_fix.sh

echo ""
echo "============================================================"
echo "✅ 完成！"
echo "============================================================"

