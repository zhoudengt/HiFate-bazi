#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新FORMULA规则的条件信息到数据库

从原始JSON文件读取"筛选条件1"和"筛选条件2"，更新数据库中的description字段
"""

import json
import os
import sys
from typing import Dict, List, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.db.mysql_connector import get_db_connection


def update_formula_rules_conditions(dry_run: bool = False):
    """
    更新FORMULA规则的条件信息到数据库
    
    Args:
        dry_run: 是否为试运行模式（只查询不更新）
    """
    print("=" * 80)
    if dry_run:
        print("试运行模式：查询需要更新的规则（不实际更新）")
    else:
        print("更新FORMULA规则的条件信息到数据库")
    print("=" * 80)
    
    # 1. 加载原始JSON文件
    json_file_path = os.path.join(project_root, 'docs', '2025.11.20算法公式.json')
    if not os.path.exists(json_file_path):
        print(f"❌ 错误：找不到规则文件 {json_file_path}")
        return False
    
    print(f"\n1. 加载原始JSON文件: {json_file_path}")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        rules_data = json.load(f)
    
    # 构建规则ID到原始数据的映射
    original_rules_data = {}
    for sheet_name, sheet_data in rules_data.items():
        if sheet_name == 'headers' or not isinstance(sheet_data, dict):
            continue
        rows = sheet_data.get('rows', [])
        for rule_row in rows:
            rule_id = rule_row.get('ID')
            if rule_id:
                original_rules_data[int(rule_id)] = rule_row
    
    print(f"   ✓ 成功加载 {len(original_rules_data)} 条规则")
    
    # 2. 连接数据库
    print("\n2. 连接数据库...")
    try:
        db = get_db_connection()
        print("   ✓ 数据库连接成功")
    except Exception as e:
        print(f"   ❌ 数据库连接失败: {e}")
        return False
    
    # 3. 查询所有FORMULA规则（conditions为空或{}的）
    print("\n3. 查询需要更新的规则...")
    sql = """
        SELECT rule_code, rule_name, rule_type, conditions, description
        FROM bazi_rules
        WHERE rule_code LIKE 'FORMULA_%'
        ORDER BY rule_code
    """
    
    all_formula_rules = db.execute_query(sql)
    print(f"   ✓ 找到 {len(all_formula_rules)} 条FORMULA规则")
    
    # 统计需要更新的规则
    need_update = []
    for rule in all_formula_rules:
        rule_code = rule.get('rule_code', '')
        if rule_code.startswith('FORMULA_'):
            rule_id = rule_code.replace('FORMULA_', '')
            try:
                rule_id_int = int(rule_id)
                # 检查原始JSON中是否有这条规则
                if rule_id_int in original_rules_data:
                    original_rule = original_rules_data[rule_id_int]
                    condition1 = original_rule.get('筛选条件1', '') or ''
                    condition2 = original_rule.get('筛选条件2', '') or ''
                    gender = original_rule.get('性别', '无论男女') or '无论男女'
                    
                    # 构建新的description（JSON格式）
                    new_description = json.dumps({
                        '筛选条件1': condition1,
                        '筛选条件2': condition2,
                        '性别': gender,
                        '原始描述': f'从FormulaRuleService迁移的{original_rule.get("类型", "未知")}规则'
                    }, ensure_ascii=False)
                    
                    need_update.append({
                        'rule_code': rule_code,
                        'rule_id': rule_id_int,
                        'condition1': condition1,
                        'condition2': condition2,
                        'gender': gender,
                        'new_description': new_description,
                        'old_description': rule.get('description', '')
                    })
            except ValueError:
                continue
    
    print(f"   ✓ 需要更新 {len(need_update)} 条规则")
    
    # 4. 显示需要更新的规则（前20条）
    if need_update:
        print("\n4. 需要更新的规则（前20条）:")
        print("-" * 80)
        for idx, rule_info in enumerate(need_update[:20], 1):
            print(f"\n{idx}. {rule_info['rule_code']}")
            print(f"   筛选条件1: '{rule_info['condition1']}'")
            print(f"   筛选条件2: '{rule_info['condition2']}'")
            print(f"   性别: '{rule_info['gender']}'")
        
        if len(need_update) > 20:
            print(f"\n   ... 还有 {len(need_update) - 20} 条规则")
    
    # 5. 更新数据库
    if not dry_run and need_update:
        print("\n5. 更新数据库...")
        print("-" * 80)
        
        success_count = 0
        failed_count = 0
        
        for idx, rule_info in enumerate(need_update, 1):
            try:
                update_sql = """
                    UPDATE bazi_rules
                    SET description = %s,
                        updated_at = NOW()
                    WHERE rule_code = %s
                """
                
                db.execute_update(
                    update_sql,
                    (rule_info['new_description'], rule_info['rule_code'])
                )
                
                success_count += 1
                if idx % 50 == 0:
                    print(f"  进度: {idx}/{len(need_update)} ({idx*100//len(need_update)}%)")
            except Exception as e:
                failed_count += 1
                print(f"  ✗ 更新失败 {rule_info['rule_code']}: {e}")
        
        # 更新规则版本号
        if success_count > 0:
            try:
                db.execute_update("UPDATE rule_version SET rule_version = rule_version + 1, updated_at = NOW()")
                print("\n✓ 规则版本号已更新")
            except Exception as e:
                print(f"\n⚠ 更新规则版本号失败: {e}")
        
        print("\n" + "=" * 80)
        print("更新完成！")
        print("=" * 80)
        print(f"总计: {len(need_update)}")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print("=" * 80)
        
        return failed_count == 0
    elif dry_run:
        print("\n5. 试运行模式：不会实际更新数据库")
        print("=" * 80)
        print(f"总计需要更新: {len(need_update)} 条规则")
        print("=" * 80)
        return True
    else:
        print("\n5. 没有需要更新的规则")
        print("=" * 80)
        return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='更新FORMULA规则的条件信息到数据库')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式（只查询不更新）')
    
    args = parser.parse_args()
    
    success = update_formula_rules_conditions(dry_run=args.dry_run)
    
    if success:
        print("\n✅ 操作完成！")
        sys.exit(0)
    else:
        print("\n❌ 操作失败！")
        sys.exit(1)


if __name__ == '__main__':
    main()

