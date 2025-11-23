#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修改规则匹配的内容
支持：
1. 批量修改规则内容（content）
2. 批量修改规则条件（conditions）
3. 批量修改规则名称、描述等
4. 支持按规则类型、规则代码等条件筛选
5. 支持从 JSON/CSV/Excel 文件批量导入修改
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from server.db.mysql_connector import get_db_connection
from server.db.rule_content_dao import RuleContentDAO


def update_rules_from_json(file_path: str, dry_run: bool = False) -> Dict[str, int]:
    """
    从 JSON 文件批量更新规则
    
    JSON 格式示例：
    [
        {
            "rule_code": "R001",
            "rule_name": "规则名称（可选）",
            "content": {"text": "新内容"},
            "conditions": {"year_pillar": "甲子"},
            "priority": 100,
            "enabled": true,
            "description": "描述（可选）"
        }
    ]
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        rules_data = json.load(f)
    
    if not isinstance(rules_data, list):
        raise ValueError("JSON 文件必须包含一个规则数组")
    
    db = get_db_connection()
    success_count = 0
    failed_count = 0
    updated_fields = []
    
    for idx, rule_data in enumerate(rules_data, 1):
        try:
            rule_code = rule_data.get('rule_code')
            if not rule_code:
                print(f"  ⚠️  第 {idx} 条规则缺少 rule_code，跳过")
                failed_count += 1
                continue
            
            # 构建 UPDATE SQL
            update_fields = []
            update_values = []
            
            if 'rule_name' in rule_data:
                update_fields.append("rule_name = %s")
                update_values.append(rule_data['rule_name'])
            
            if 'content' in rule_data:
                update_fields.append("content = %s")
                update_values.append(json.dumps(rule_data['content'], ensure_ascii=False))
                updated_fields.append('content')
            
            if 'conditions' in rule_data:
                update_fields.append("conditions = %s")
                update_values.append(json.dumps(rule_data['conditions'], ensure_ascii=False))
                updated_fields.append('conditions')
            
            if 'priority' in rule_data:
                update_fields.append("priority = %s")
                update_values.append(rule_data['priority'])
            
            if 'enabled' in rule_data:
                update_fields.append("enabled = %s")
                update_values.append(rule_data['enabled'])
            
            if 'description' in rule_data:
                update_fields.append("description = %s")
                update_values.append(rule_data['description'])
            
            if not update_fields:
                print(f"  ⚠️  规则 {rule_code} 没有需要更新的字段，跳过")
                continue
            
            update_fields.append("updated_at = NOW()")
            update_values.append(rule_code)
            
            sql = f"""
                UPDATE bazi_rules 
                SET {', '.join(update_fields)}
                WHERE rule_code = %s
            """
            
            if dry_run:
                print(f"  [模拟] 更新规则 {rule_code}: {', '.join(set(updated_fields))}")
            else:
                db.execute_update(sql, tuple(update_values))
                success_count += 1
                if idx % 10 == 0:
                    print(f"  进度: {idx}/{len(rules_data)} ({idx*100//len(rules_data)}%)")
        
        except Exception as e:
            failed_count += 1
            print(f"  ✗ 更新规则失败: {rule_data.get('rule_code', 'unknown')} - {e}")
    
    if not dry_run and success_count > 0:
        # 更新规则版本号
        try:
            RuleContentDAO.update_rule_version()
            print("\n✓ 规则版本号已更新")
        except Exception as e:
            print(f"\n⚠ 更新规则版本号失败: {e}")
    
    return {
        'total': len(rules_data),
        'success': success_count,
        'failed': failed_count
    }


def update_rules_by_filter(
    rule_type: Optional[str] = None,
    rule_code_pattern: Optional[str] = None,
    content_update: Optional[Dict] = None,
    conditions_update: Optional[Dict] = None,
    enabled: Optional[bool] = None,
    priority: Optional[int] = None,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    按条件批量更新规则
    
    Args:
        rule_type: 规则类型筛选（如 "marriage_ten_gods"）
        rule_code_pattern: 规则代码模式（支持 LIKE 查询，如 "R%", "%marriage%"）
        content_update: 要更新的内容字段（字典，会合并到现有 content）
        conditions_update: 要更新的条件字段（字典，会合并到现有 conditions）
        enabled: 是否启用
        priority: 优先级
        dry_run: 是否只是模拟运行
    """
    db = get_db_connection()
    
    # 构建查询条件
    where_clauses = []
    where_values = []
    
    if rule_type:
        where_clauses.append("rule_type = %s")
        where_values.append(rule_type)
    
    if rule_code_pattern:
        where_clauses.append("rule_code LIKE %s")
        where_values.append(rule_code_pattern)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # 查询匹配的规则
    query_sql = f"SELECT rule_code, content, conditions FROM bazi_rules WHERE {where_sql}"
    rules = db.execute_query(query_sql, tuple(where_values))
    
    if not rules:
        print(f"⚠️  没有找到匹配的规则")
        return {'total': 0, 'success': 0, 'failed': 0}
    
    print(f"找到 {len(rules)} 条匹配的规则")
    
    success_count = 0
    failed_count = 0
    
    for idx, rule in enumerate(rules, 1):
        try:
            rule_code = rule['rule_code']
            update_fields = []
            update_values = []
            
            # 更新 content
            if content_update:
                current_content = rule['content']
                if isinstance(current_content, str):
                    current_content = json.loads(current_content)
                elif current_content is None:
                    current_content = {}
                
                # 合并更新
                updated_content = {**current_content, **content_update}
                update_fields.append("content = %s")
                update_values.append(json.dumps(updated_content, ensure_ascii=False))
            
            # 更新 conditions
            if conditions_update:
                current_conditions = rule['conditions']
                if isinstance(current_conditions, str):
                    current_conditions = json.loads(current_conditions)
                elif current_conditions is None:
                    current_conditions = {}
                
                # 合并更新
                updated_conditions = {**current_conditions, **conditions_update}
                update_fields.append("conditions = %s")
                update_values.append(json.dumps(updated_conditions, ensure_ascii=False))
            
            # 更新 enabled
            if enabled is not None:
                update_fields.append("enabled = %s")
                update_values.append(enabled)
            
            # 更新 priority
            if priority is not None:
                update_fields.append("priority = %s")
                update_values.append(priority)
            
            if not update_fields:
                print(f"  ⚠️  规则 {rule_code} 没有需要更新的字段，跳过")
                continue
            
            update_fields.append("updated_at = NOW()")
            update_values.append(rule_code)
            
            sql = f"""
                UPDATE bazi_rules 
                SET {', '.join(update_fields)}
                WHERE rule_code = %s
            """
            
            if dry_run:
                print(f"  [模拟] 更新规则 {rule_code}")
            else:
                db.execute_update(sql, tuple(update_values))
                success_count += 1
                if idx % 10 == 0:
                    print(f"  进度: {idx}/{len(rules)} ({idx*100//len(rules)}%)")
        
        except Exception as e:
            failed_count += 1
            print(f"  ✗ 更新规则失败: {rule.get('rule_code', 'unknown')} - {e}")
    
    if not dry_run and success_count > 0:
        # 更新规则版本号
        try:
            RuleContentDAO.update_rule_version()
            print("\n✓ 规则版本号已更新")
        except Exception as e:
            print(f"\n⚠ 更新规则版本号失败: {e}")
    
    return {
        'total': len(rules),
        'success': success_count,
        'failed': failed_count
    }


def export_rules_to_json(
    output_file: str,
    rule_type: Optional[str] = None,
    rule_code_pattern: Optional[str] = None
) -> int:
    """
    导出规则到 JSON 文件（用于编辑后批量更新）
    """
    db = get_db_connection()
    
    # 构建查询条件
    where_clauses = []
    where_values = []
    
    if rule_type:
        where_clauses.append("rule_type = %s")
        where_values.append(rule_type)
    
    if rule_code_pattern:
        where_clauses.append("rule_code LIKE %s")
        where_values.append(rule_code_pattern)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    query_sql = f"""
        SELECT rule_code, rule_name, rule_type, priority, 
               conditions, content, enabled, description
        FROM bazi_rules 
        WHERE {where_sql}
        ORDER BY rule_type, rule_code
    """
    
    rules = db.execute_query(query_sql, tuple(where_values))
    
    # 处理 JSON 字段
    rules_data = []
    for rule in rules:
        rule_dict = {
            'rule_code': rule['rule_code'],
            'rule_name': rule['rule_name'],
            'rule_type': rule['rule_type'],
            'priority': rule['priority'],
            'enabled': rule['enabled'],
        }
        
        # 解析 JSON 字段
        if rule.get('conditions'):
            conditions = rule['conditions']
            if isinstance(conditions, str):
                rule_dict['conditions'] = json.loads(conditions)
            else:
                rule_dict['conditions'] = conditions
        
        if rule.get('content'):
            content = rule['content']
            if isinstance(content, str):
                rule_dict['content'] = json.loads(content)
            else:
                rule_dict['content'] = content
        
        if rule.get('description'):
            rule_dict['description'] = rule['description']
        
        rules_data.append(rule_dict)
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rules_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已导出 {len(rules_data)} 条规则到 {output_file}")
    return len(rules_data)


def main():
    parser = argparse.ArgumentParser(description='批量修改规则匹配的内容')
    parser.add_argument('--mode', choices=['import', 'filter', 'export'], required=True,
                       help='操作模式：import=从文件导入, filter=按条件筛选更新, export=导出规则')
    
    # 导入模式
    parser.add_argument('--file', type=str, help='JSON 文件路径（import 模式）')
    
    # 筛选模式
    parser.add_argument('--rule-type', type=str, help='规则类型筛选（如 marriage_ten_gods）')
    parser.add_argument('--rule-code-pattern', type=str, help='规则代码模式（支持 LIKE，如 R%）')
    parser.add_argument('--content-update', type=str, help='要更新的内容（JSON 字符串，会合并到现有 content）')
    parser.add_argument('--conditions-update', type=str, help='要更新的条件（JSON 字符串，会合并到现有 conditions）')
    parser.add_argument('--enabled', type=lambda x: x.lower() == 'true', help='是否启用（true/false）')
    parser.add_argument('--priority', type=int, help='优先级')
    
    # 导出模式
    parser.add_argument('--output', type=str, help='输出文件路径（export 模式）')
    
    # 通用选项
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际更新数据库')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("批量修改规则工具")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️  模拟运行模式（不会实际更新数据库）")
        print()
    
    try:
        if args.mode == 'import':
            if not args.file:
                print("❌ 错误：import 模式需要指定 --file 参数")
                return
            
            if not os.path.exists(args.file):
                print(f"❌ 错误：文件不存在: {args.file}")
                return
            
            print(f"从文件导入规则: {args.file}")
            result = update_rules_from_json(args.file, dry_run=args.dry_run)
            print(f"\n总计: {result['total']}")
            print(f"成功: {result['success']}")
            print(f"失败: {result['failed']}")
        
        elif args.mode == 'filter':
            content_update = None
            if args.content_update:
                content_update = json.loads(args.content_update)
            
            conditions_update = None
            if args.conditions_update:
                conditions_update = json.loads(args.conditions_update)
            
            print("按条件筛选更新规则")
            if args.rule_type:
                print(f"  规则类型: {args.rule_type}")
            if args.rule_code_pattern:
                print(f"  规则代码模式: {args.rule_code_pattern}")
            if content_update:
                print(f"  内容更新: {content_update}")
            if conditions_update:
                print(f"  条件更新: {conditions_update}")
            if args.enabled is not None:
                print(f"  启用状态: {args.enabled}")
            if args.priority is not None:
                print(f"  优先级: {args.priority}")
            print()
            
            result = update_rules_by_filter(
                rule_type=args.rule_type,
                rule_code_pattern=args.rule_code_pattern,
                content_update=content_update,
                conditions_update=conditions_update,
                enabled=args.enabled,
                priority=args.priority,
                dry_run=args.dry_run
            )
            print(f"\n总计: {result['total']}")
            print(f"成功: {result['success']}")
            print(f"失败: {result['failed']}")
        
        elif args.mode == 'export':
            if not args.output:
                print("❌ 错误：export 模式需要指定 --output 参数")
                return
            
            print("导出规则到文件")
            if args.rule_type:
                print(f"  规则类型: {args.rule_type}")
            if args.rule_code_pattern:
                print(f"  规则代码模式: {args.rule_code_pattern}")
            print()
            
            count = export_rules_to_json(
                args.output,
                rule_type=args.rule_type,
                rule_code_pattern=args.rule_code_pattern
            )
            print(f"\n✓ 导出完成，共 {count} 条规则")
            print(f"  编辑文件后，使用 --mode import --file {args.output} 导入更新")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())

