#!/bin/bash
# 检查生产环境规则数量

echo "============================================================"
echo "🔍 检查生产环境规则数据"
echo "============================================================"

# 检查 Node1 数据库规则数量
echo ""
echo "📊 Node1 (8.210.52.217) 数据库规则统计:"
ssh root@8.210.52.217 << 'EOF'
cd /opt/HiFate-bazi
docker exec hifate-mysql-master mysql -uroot -p"${MYSQL_PASSWORD:?MYSQL_PASSWORD required}" hifate_bazi -e "
SELECT 
    '总规则数' as type,
    COUNT(*) as count
FROM bazi_rules 
WHERE rule_code LIKE 'FORMULA_%'
UNION ALL
SELECT 
    '启用规则数' as type,
    COUNT(*) as count
FROM bazi_rules 
WHERE rule_code LIKE 'FORMULA_%' AND enabled = 1
UNION ALL
SELECT 
    CONCAT('类型: ', rule_type) as type,
    COUNT(*) as count
FROM bazi_rules 
WHERE rule_code LIKE 'FORMULA_%' AND enabled = 1
GROUP BY rule_type
ORDER BY type;
"
EOF

echo ""
echo "📊 测试八字 (1987-01-07 09:00 男) 匹配结果:"
echo "正在调用生产环境 API..."
curl -s -X POST http://8.210.52.217:8001/api/v1/bazi/formula-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1987-01-07",
    "solar_time": "09:00",
    "gender": "male"
  }' | python3 -m json.tool | grep -A 20 "statistics"

echo ""
echo "============================================================"
echo "💡 建议检查项:"
echo "  1. 数据库规则数量是否一致"
echo "  2. 规则 enabled 状态是否正确"
echo "  3. 缓存是否影响（清除缓存后重新测试）"
echo "============================================================"

