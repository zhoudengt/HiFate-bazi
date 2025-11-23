#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入十神命格.xlsx中的三类规则到数据库
- 性格规则 (character_*)
- 婚配规则 (marriage_*)  
- 十神命格规则 (destiny_pattern)
"""

import sys
import os
import json
import re
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

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

def parse_condition(category: str, condition1: str, condition2: str) -> Dict[str, Any]:
    """
    解析筛选条件，生成conditions JSON
    
    Args:
        category: 类别（性格/婚配/十神命格）
        condition1: 筛选条件1（如"日柱"）
        condition2: 筛选条件2（如"甲子"或具体条件）
        
    Returns:
        conditions字典
    """
    conditions = {"all": []}
    
    # 处理日柱/月柱/年柱/时柱
    if condition1 in ["日柱", "月柱", "年柱", "时柱"]:
        pillar_map = {
            "日柱": "day",
            "月柱": "month", 
            "年柱": "year",
            "时柱": "hour"
        }
        pillar = pillar_map[condition1]
        
        # 检查condition2是否包含复杂条件
        if "主星" in condition2 or "副星" in condition2:
            # 十神命格的复杂条件
            conditions["all"].append({
                "custom": {
                    "type": "ten_gods_pattern",
                    "description": condition2
                }
            })
        else:
            # 简单的干支匹配
            ganzhi_list = re.findall(r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]', condition2)
            if ganzhi_list:
                conditions["all"].append({
                    "pillar_in": {
                        "pillar": pillar,
                        "values": ganzhi_list
                    }
                })
    
    return conditions if conditions["all"] else {"all": [{"always": True}]}

def generate_rule_code(rule_id: int, category: str) -> str:
    """
    生成规则代码
    
    Args:
        rule_id: 规则ID
        category: 类别
        
    Returns:
        规则代码
    """
    prefix_map = {
        "性格": "CHAR",
        "婚配": "MARR",
        "十神命格": "DEST"
    }
    prefix = prefix_map.get(category, "RULE")
    return f"{prefix}-{rule_id}"

def parse_gender(gender_str: str) -> Optional[str]:
    """
    解析性别
    
    Args:
        gender_str: 性别字符串
        
    Returns:
        male/female/None
    """
    if not gender_str or gender_str == "无论男女":
        return None
    if gender_str in ["男", "male", "男命", "男性"]:
        return "male"
    if gender_str in ["女", "female", "女命", "女性"]:
        return "female"
    return None

def import_rules_from_json(json_path: str, dry_run: bool = False):
    """
    从JSON文件导入规则到数据库
    
    Args:
        json_path: JSON文件路径
        dry_run: 是否为试运行（不写入数据库）
    """
    print("=" * 60)
    print("📥 导入十神命格规则")
    print("=" * 60)
    
    # 读取JSON
    print(f"\n📖 读取JSON文件: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 连接数据库
    db = None
    if not dry_run:
        from server.db.mysql_connector import get_db_connection
        db = get_db_connection()
        print("✅ 已连接数据库")
    else:
        print("⚠️  试运行模式（不写入数据库）")
    
    total_inserted = 0
    total_updated = 0
    total_skipped = 0
    
    # 遍历每个工作表
    for sheet_name, sheet_data in data['sheets'].items():
        print(f"\n{'='*60}")
        print(f"处理工作表: {sheet_name}")
        print(f"{'='*60}")
        
        records = sheet_data['data']
        print(f"记录数: {len(records)}")
        
        for idx, record in enumerate(records, 1):
            rule_id = record.get('ID')
            category = record.get('类型', sheet_name)
            gender_str = record.get('性别', '')
            condition1 = record.get('筛选条件1', '')
            condition2 = record.get('筛选条件2', '')
            result = record.get('结果', '')
            
            if not rule_id or not result:
                print(f"  ⚠️  跳过第{idx}条（缺少ID或结果）")
                total_skipped += 1
                continue
            
            # 生成rule_code
            rule_code = generate_rule_code(rule_id, category)
            
            # 确定rule_type
            type_map = RULE_TYPE_MAP.get(category, {})
            rule_type = type_map.get(condition1, type_map.get("default", "general"))
            
            # 解析性别
            gender = parse_gender(gender_str)
            
            # 生成conditions
            conditions = parse_condition(category, condition1, condition2)
            
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
            
            print(f"\n  [{idx}/{len(records)}] {rule_code}")
            print(f"    类型: {rule_type}")
            print(f"    条件: {condition1} = {condition2[:30]}...")
            print(f"    性别: {gender or '无限制'}")
            
            if dry_run:
                print(f"    [试运行] 将写入数据库")
                print(f"    conditions: {json.dumps(conditions, ensure_ascii=False)[:100]}...")
                print(f"    content: {json.dumps(content, ensure_ascii=False)[:100]}...")
                continue
            
            # 检查规则是否已存在
            existing = db.execute_query(
                "SELECT id FROM bazi_rules WHERE rule_code = %s",
                (rule_code,)
            )
            
            if existing:
                # 更新现有规则
                db.execute_update(
                    """
                    UPDATE bazi_rules
                    SET rule_name = %s,
                        rule_type = %s,
                        conditions = %s,
                        content = %s,
                        description = %s,
                        updated_at = NOW()
                    WHERE rule_code = %s
                    """,
                    (rule_name, rule_type, json.dumps(conditions, ensure_ascii=False),
                     json.dumps(content, ensure_ascii=False), description, rule_code)
                )
                print(f"    ✅ 已更新")
                total_updated += 1
            else:
                # 插入新规则
                db.execute_update(
                    """
                    INSERT INTO bazi_rules 
                    (rule_code, rule_name, rule_type, conditions, content, description, priority, enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, 100, 1)
                    """,
                    (rule_code, rule_name, rule_type, json.dumps(conditions, ensure_ascii=False),
                     json.dumps(content, ensure_ascii=False), description)
                )
                print(f"    ✅ 已插入")
                total_inserted += 1
    
    # 更新规则版本号
    if not dry_run and (total_inserted > 0 or total_updated > 0):
        db.execute_update(
            "UPDATE rule_version SET rule_version = rule_version + 1, updated_at = NOW()"
        )
        print("\n✅ 已更新规则版本号")
    
    # 打印统计信息
    print("\n" + "=" * 60)
    print("📊 导入统计")
    print("=" * 60)
    print(f"新增规则: {total_inserted}")
    print(f"更新规则: {total_updated}")
    print(f"跳过规则: {total_skipped}")
    print(f"总计: {total_inserted + total_updated + total_skipped}")
    print("=" * 60)
    
    if not dry_run:
        print("\n✅ 导入完成！")
    else:
        print("\n⚠️  试运行完成！使用 --no-dry-run 参数写入数据库")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='导入十神命格规则到数据库')
    parser.add_argument('--json', default=os.path.join(PROJECT_ROOT, 'docs', '十神命格.json'),
                        help='JSON文件路径')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='试运行模式（不写入数据库）')
    parser.add_argument('--no-dry-run', action='store_true',
                        help='实际执行（写入数据库）')
    
    args = parser.parse_args()
    
    # 如果指定了--no-dry-run，则不是试运行
    dry_run = not args.no_dry_run
    
    if not os.path.exists(args.json):
        print(f"❌ 文件不存在: {args.json}")
        sys.exit(1)
    
    import_rules_from_json(args.json, dry_run=dry_run)

if __name__ == '__main__':
    main()

