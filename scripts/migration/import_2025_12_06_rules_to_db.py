#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 2025.12.06算法公式--中午.xlsx 已解析规则到数据库

使用方法:
  python scripts/migration/import_2025_12_06_rules_to_db.py --dry-run  # 预览
  python scripts/migration/import_2025_12_06_rules_to_db.py            # 正式导入
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 导入解析器和数据库配置
from scripts.migration.import_2025_12_06_rules import analyze_rules, XLSX_FILE
from scripts.migration.import_2025_12_03_rules import RULE_TYPE_MAP, GENDER_MAP
from server.config.mysql_config import get_mysql_connection, return_mysql_connection


def import_rules_to_db(dry_run: bool = False) -> Dict[str, int]:
    """导入已解析的规则到数据库"""
    
    print("=" * 80)
    print("导入 2025.12.06算法公式--中午.xlsx 规则到数据库")
    print("=" * 80)
    
    if dry_run:
        print("\n⚠️  DRY RUN 模式，不会修改数据库\n")
    
    # 分析规则
    parsed_rules, failed_rules, failure_reasons = analyze_rules(xlsx_path=XLSX_FILE)
    
    total = len(parsed_rules) + len(failed_rules)
    success_rate = (len(parsed_rules) / total * 100) if total > 0 else 0
    
    print(f"\n📊 规则统计:")
    print(f"  - 总规则数: {total}")
    print(f"  - 成功解析: {len(parsed_rules)} 条 ({success_rate:.1f}%)")
    print(f"  - 无法解析: {len(failed_rules)} 条 ({100-success_rate:.1f}%)")
    
    if not parsed_rules:
        print("\n❌ 没有可导入的规则")
        return {"inserted": 0, "updated": 0, "skipped": 0}
    
    # 连接数据库
    conn = get_mysql_connection()
    inserted = 0
    updated = 0
    skipped = 0
    
    try:
        with conn.cursor() as cur:
            # 获取已存在的规则编码
            cur.execute("SELECT rule_code FROM bazi_rules WHERE rule_code LIKE 'FORMULA_事业_%'")
            rows = cur.fetchall()
            # 处理字典或元组格式
            if rows and isinstance(rows[0], dict):
                existing_codes = {row['rule_code'] for row in rows}
            else:
                existing_codes = {row[0] for row in rows}
            
            print(f"\n📝 开始导入规则...")
            
            for rule in parsed_rules:
                rule_id = rule['ID']
                rule_code = rule['rule_code']
                rule_type = RULE_TYPE_MAP.get(rule['类型'], rule['类型'].lower())
                conditions = rule['conditions']
                
                # 构建规则数据
                rule_name = f"{rule['类型']}规则-{rule_id}"
                rule_category = rule['类型']
                priority = 100  # 默认优先级
                content = {
                    "text": rule.get('结果', '')
                }
                description = {
                    "筛选条件1": rule.get('筛选条件1', ''),
                    "筛选条件2": rule.get('筛选条件2', ''),
                    "数量": rule.get('数量', ''),
                    "性别": rule.get('性别', '无论男女')
                }
                enabled = 1
                
                if dry_run:
                    if rule_code in existing_codes:
                        print(f"  [更新] {rule_code}: {rule_name}")
                    else:
                        print(f"  [新增] {rule_code}: {rule_name}")
                    continue
                
                # 检查是否存在
                if rule_code in existing_codes:
                    # 更新
                    update_sql = """
                        UPDATE bazi_rules
                        SET rule_name = %s, rule_type = %s, rule_category = %s, priority = %s,
                            conditions = %s, content = %s, description = %s, enabled = %s,
                            version = version + 1, updated_at = NOW()
                        WHERE rule_code = %s
                    """
                    cur.execute(update_sql, (
                        rule_name,
                        rule_type,
                        rule_category,
                        priority,
                        json.dumps(conditions, ensure_ascii=False),
                        json.dumps(content, ensure_ascii=False),
                        json.dumps(description, ensure_ascii=False),
                        enabled,
                        rule_code
                    ))
                    updated += 1
                    print(f"  ✅ 更新: {rule_code}")
                else:
                    # 插入
                    insert_sql = """
                        INSERT INTO bazi_rules 
                        (rule_code, rule_name, rule_type, rule_category, priority, conditions, content, description, enabled)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cur.execute(insert_sql, (
                        rule_code,
                        rule_name,
                        rule_type,
                        rule_category,
                        priority,
                        json.dumps(conditions, ensure_ascii=False),
                        json.dumps(content, ensure_ascii=False),
                        json.dumps(description, ensure_ascii=False),
                        enabled
                    ))
                    inserted += 1
                    print(f"  ✅ 新增: {rule_code}")
            
            if not dry_run:
                conn.commit()
                print(f"\n✅ 导入完成:")
                print(f"  - 新增: {inserted} 条")
                print(f"  - 更新: {updated} 条")
            else:
                print(f"\n📊 预览结果:")
                print(f"  - 将新增: {len([r for r in parsed_rules if r['rule_code'] not in existing_codes])} 条")
                print(f"  - 将更新: {len([r for r in parsed_rules if r['rule_code'] in existing_codes])} 条")
    
    except Exception as e:
        if not dry_run:
            conn.rollback()
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        return_mysql_connection(conn)
    
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description="导入 2025.12.06算法公式--中午.xlsx 规则到数据库")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不修改数据库")
    args = parser.parse_args()
    
    try:
        result = import_rules_to_db(dry_run=args.dry_run)
        
        if not args.dry_run:
            print(f"\n🎉 导入成功!")
            print(f"  - 新增: {result['inserted']} 条")
            print(f"  - 更新: {result['updated']} 条")
        else:
            print(f"\n💡 这是预览模式，实际导入请运行: python {__file__}")
    
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

