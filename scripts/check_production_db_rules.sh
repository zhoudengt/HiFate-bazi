#!/bin/bash
# 检查生产环境数据库中的规则

echo "================================================================================"
echo "🔍 检查生产环境数据库中的规则"
echo "================================================================================"

ssh root@8.210.52.217 << 'EOF'
cd /opt/HiFate-bazi
docker exec hifate-mysql-master mysql -uroot -p"${MYSQL_PASSWORD:?MYSQL_PASSWORD required}" hifate_bazi -e "
SELECT 
    COUNT(*) as total_rules,
    SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_rules,
    SUM(CASE WHEN enabled = 0 THEN 1 ELSE 0 END) as disabled_rules,
    SUM(CASE WHEN rule_code LIKE 'FORMULA_%' THEN 1 ELSE 0 END) as formula_rules,
    SUM(CASE WHEN rule_code LIKE 'FORMULA_%' AND enabled = 1 THEN 1 ELSE 0 END) as enabled_formula_rules
FROM bazi_rules;
"

echo ""
echo "按类型统计 FORMULA_ 规则（enabled=1）:"
docker exec hifate-mysql-master mysql -uroot -p"${MYSQL_PASSWORD:?MYSQL_PASSWORD required}" hifate_bazi -e "
SELECT 
    rule_type,
    COUNT(*) as count
FROM bazi_rules
WHERE rule_code LIKE 'FORMULA_%' AND enabled = 1
GROUP BY rule_type
ORDER BY count DESC;
"
EOF
