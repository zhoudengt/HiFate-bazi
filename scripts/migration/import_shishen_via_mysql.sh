#!/bin/bash
# 通过mysql命令行导入十神命格规则
# 避开pymysql依赖问题

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
JSON_FILE="$PROJECT_ROOT/docs/十神命格.json"
SQL_FILE="/tmp/import_shishen_rules.sql"

echo "============================================================"
echo "📥 导入十神命格规则（使用mysql命令行）"
echo "============================================================"

# 检查JSON文件
if [ ! -f "$JSON_FILE" ]; then
    echo "❌ JSON文件不存在: $JSON_FILE"
    exit 1
fi

echo "✅ JSON文件存在"
echo "📖 解析JSON并生成SQL..."

# 使用Python生成SQL
python3 << PYTHON_SCRIPT
import json
import sys
import os

json_file = "$JSON_FILE"
sql_file = "$SQL_FILE"

# 读取JSON
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 规则类型映射
RULE_TYPE_MAP = {
    "性格": {
        "日柱": "character_day_pillar",
        "月柱": "character_month_pillar",
        "年柱": "character_year_pillar",
        "时柱": "character_hour_pillar",
        "default": "character_general"
    },
    "婚配": {
        "日柱": "marriage_day_pillar",
        "月柱": "marriage_month_pillar",
        "年柱": "marriage_year_pillar",
        "时柱": "marriage_hour_pillar",
        "default": "marriage_general"
    },
    "十神命格": {
        "月柱": "destiny_pattern",
        "default": "destiny_pattern"
    }
}

def generate_rule_code(rule_id, category):
    prefix_map = {
        "性格": "CHAR",
        "婚配": "MARR",
        "十神命格": "DEST"
    }
    prefix = prefix_map.get(category, "RULE")
    return f"{prefix}-{rule_id}"

def escape_sql(text):
    """转义SQL字符串"""
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

# 生成SQL
sql_statements = []
sql_statements.append("-- 导入十神命格规则")
sql_statements.append("USE bazi;")
sql_statements.append("")

total_rules = 0

for sheet_name, sheet_data in data['sheets'].items():
    records = sheet_data['data']
    print(f"处理工作表: {sheet_name} ({len(records)}条)")
    
    for record in records:
        rule_id = record.get('ID')
        category = record.get('类型', sheet_name)
        gender_str = record.get('性别', '')
        condition1 = record.get('筛选条件1', '')
        condition2 = record.get('筛选条件2', '')
        result = record.get('结果', '')
        
        if not rule_id or not result:
            continue
        
        # 生成rule_code
        rule_code = generate_rule_code(rule_id, category)
        
        # 确定rule_type
        type_map = RULE_TYPE_MAP.get(category, {})
        rule_type = type_map.get(condition1, type_map.get("default", "general"))
        
        # 解析性别
        gender = None
        if gender_str and gender_str != "无论男女":
            if gender_str in ["男", "male", "男命", "男性"]:
                gender = "male"
            elif gender_str in ["女", "female", "女命", "女性"]:
                gender = "female"
        
        # 生成conditions
        conditions = {"all": []}
        
        if condition1 in ["日柱", "月柱", "年柱", "时柱"]:
            pillar_map = {
                "日柱": "day",
                "月柱": "month",
                "年柱": "year",
                "时柱": "hour"
            }
            pillar = pillar_map[condition1]
            
            # 简单的干支匹配
            import re
            ganzhi_list = re.findall(r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]', condition2)
            if ganzhi_list:
                conditions["all"].append({
                    "pillar_in": {
                        "pillar": pillar,
                        "values": ganzhi_list
                    }
                })
        
        if not conditions["all"]:
            conditions = {"all": [{"always": True}]}
        
        # 如果有性别限制，添加到conditions
        if gender:
            conditions["all"].insert(0, {"gender": gender})
        
        # 生成content
        content = {
            "text": result,
            "type": "description"
        }
        
        # 生成rule_name
        rule_name = f"{category}-{condition2[:20] if len(condition2) <= 20 else condition2[:20]+'...'}"
        
        # 生成description
        description = f"{category}规则 - {condition1}: {condition2}"
        
        # 生成SQL
        conditions_json = json.dumps(conditions, ensure_ascii=False)
        content_json = json.dumps(content, ensure_ascii=False)
        
        sql = f"""
INSERT INTO bazi_rules (rule_code, rule_name, rule_type, conditions, content, description, priority, enabled)
VALUES ('{escape_sql(rule_code)}', '{escape_sql(rule_name)}', '{escape_sql(rule_type)}', 
'{escape_sql(conditions_json)}', '{escape_sql(content_json)}', '{escape_sql(description)}', 100, 1)
ON DUPLICATE KEY UPDATE
    rule_name = VALUES(rule_name),
    rule_type = VALUES(rule_type),
    conditions = VALUES(conditions),
    content = VALUES(content),
    description = VALUES(description),
    updated_at = NOW();
"""
        sql_statements.append(sql)
        total_rules += 1

# 更新规则版本号
sql_statements.append("")
sql_statements.append("-- 更新规则版本号")
sql_statements.append("UPDATE rule_version SET rule_version = rule_version + 1, updated_at = NOW();")

# 写入SQL文件
with open(sql_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(sql_statements))

print(f"✅ SQL文件生成完成: {sql_file}")
print(f"📊 总计规则数: {total_rules}")

PYTHON_SCRIPT

if [ $? -ne 0 ]; then
    echo "❌ SQL生成失败"
    exit 1
fi

echo "✅ SQL文件生成成功: $SQL_FILE"
echo ""
echo "🔄 导入到数据库..."

# 从配置文件读取数据库信息
DB_HOST="127.0.0.1"
DB_PORT="3306"
DB_USER="root"
DB_PASS="123456"
DB_NAME="bazi"

# 执行SQL
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$SQL_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 规则导入成功！"
    echo ""
    echo "📊 统计信息:"
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
        SELECT 
            SUBSTRING_INDEX(rule_code, '-', 1) as 类型,
            COUNT(*) as 数量
        FROM bazi_rules 
        WHERE rule_code LIKE 'CHAR-%' OR rule_code LIKE 'MARR-%' OR rule_code LIKE 'DEST-%'
        GROUP BY SUBSTRING_INDEX(rule_code, '-', 1);
    "
    rm -f "$SQL_FILE"
    echo ""
    echo "✅ 导入完成！"
else
    echo "❌ 规则导入失败"
    echo "SQL文件保存在: $SQL_FILE"
    exit 1
fi

