#!/bin/bash
# 手动同步规则到生产环境的脚本

echo "============================================================"
echo "📤 手动同步规则到生产环境"
echo "============================================================"

SQL_FILE="scripts/temp_rules_export.sql"
PROD_HOST="8.210.52.217"
PROD_USER="root"
PROD_PATH="/tmp/rules_import.sql"

# 检查 SQL 文件是否存在
if [ ! -f "$SQL_FILE" ]; then
    echo "❌ SQL 文件不存在: $SQL_FILE"
    echo "💡 请先运行: python3 scripts/fix_production_rules.py"
    exit 1
fi

echo ""
echo "📋 执行步骤:"
echo "  1. 上传 SQL 文件到生产环境"
echo "  2. 在生产环境执行 SQL"
echo "  3. 清除缓存"
echo "  4. 验证结果"
echo ""

# 步骤 1: 上传文件
echo "============================================================"
echo "步骤 1: 上传 SQL 文件到生产环境"
echo "============================================================"
echo "执行命令:"
echo "  scp $SQL_FILE ${PROD_USER}@${PROD_HOST}:${PROD_PATH}"
echo ""
read -p "按 Enter 继续执行上传，或 Ctrl+C 取消..." 

scp "$SQL_FILE" "${PROD_USER}@${PROD_HOST}:${PROD_PATH}"

if [ $? -eq 0 ]; then
    echo "✅ 文件上传成功"
else
    echo "❌ 文件上传失败"
    echo "💡 提示: 可能需要输入密码或配置 SSH 密钥"
    exit 1
fi

# 步骤 2: 执行 SQL
echo ""
echo "============================================================"
echo "步骤 2: 在生产环境执行 SQL"
echo "============================================================"
echo "执行命令:"
echo "  ssh ${PROD_USER}@${PROD_HOST} \"docker exec -i hifate-mysql-master mysql -uroot -p"${MYSQL_PASSWORD:?MYSQL_PASSWORD required}" hifate_bazi < ${PROD_PATH}\""
echo ""
read -p "按 Enter 继续执行 SQL，或 Ctrl+C 取消..."

ssh "${PROD_USER}@${PROD_HOST}" "docker exec -i hifate-mysql-master mysql -uroot -p"${MYSQL_PASSWORD:?MYSQL_PASSWORD required}" hifate_bazi < ${PROD_PATH}"

if [ $? -eq 0 ]; then
    echo "✅ SQL 执行成功"
else
    echo "❌ SQL 执行失败"
    exit 1
fi

# 步骤 3: 清除缓存
echo ""
echo "============================================================"
echo "步骤 3: 清除缓存"
echo "============================================================"
echo "执行命令:"
echo "  curl -X POST http://${PROD_HOST}:8001/api/v1/hot-reload/check"
echo ""
read -p "按 Enter 继续清除缓存，或 Ctrl+C 取消..."

curl -X POST "http://${PROD_HOST}:8001/api/v1/hot-reload/check"

if [ $? -eq 0 ]; then
    echo "✅ 缓存清除成功"
else
    echo "⚠️  缓存清除可能失败，但可以继续"
fi

# 步骤 4: 等待规则重新加载
echo ""
echo "⏳ 等待 5 秒让规则重新加载..."
sleep 5

# 步骤 5: 验证结果
echo ""
echo "============================================================"
echo "步骤 4: 验证结果"
echo "============================================================"
echo "测试生产环境 API..."
echo ""

curl -s -X POST "http://${PROD_HOST}:8001/api/v1/bazi/formula-analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1987-01-07",
    "solar_time": "09:00",
    "gender": "male"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
stats = data.get('data', {}).get('statistics', {})
print('✅ 生产环境匹配结果:')
print(f\"  总匹配数: {stats.get('total_matched', 0)}\")
print(f\"  财富: {stats.get('wealth_count', 0)}\")
print(f\"  婚姻: {stats.get('marriage_count', 0)}\")
print(f\"  事业: {stats.get('career_count', 0)}\")
print(f\"  身体: {stats.get('health_count', 0)}\")
print(f\"  总评: {stats.get('summary_count', 0)}\")
"

echo ""
echo "============================================================"
echo "✅ 同步完成！"
echo "============================================================"
echo ""
echo "💡 如果匹配数量仍然不足，请检查:"
echo "  1. 规则 enabled 状态是否正确"
echo "  2. 缓存是否已清除"
echo "  3. 规则类型格式是否正确"
echo ""

