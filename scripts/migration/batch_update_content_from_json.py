#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 JSON 文件批量修改规则内容（只修改 content 字段，其他字段不可改动）
支持从 JSON 文件读取规则，只更新 content 字段，保持 rule_code、conditions 等不变
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


def update_content_from_json(file_path: str, dry_run: bool = False) -> Dict[str, int]:
    """
    从 JSON 文件批量更新规则内容（只更新 content 字段）
    
    JSON 格式示例：
    [
        {
            "rule_code": "MARR-10156",
            "content": {
                "text": "注意关注，外来女人争丈夫。",
                "type": "description"
            }
        },
        {
            "rule_code": "MARR-10157",
            "content": {
                "text": "新内容",
                "type": "description"
            }
        }
    ]
    
    注意：只更新 content 字段，rule_code 用于匹配，其他字段会被忽略
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        rules_data = json.load(f)
    
    if not isinstance(rules_data, list):
        raise ValueError("JSON 文件必须包含一个规则数组")
    
    db = get_db_connection()
    success_count = 0
    failed_count = 0
    not_found_count = 0
    
    print(f"从文件读取到 {len(rules_data)} 条规则")
    print()
    
    for idx, rule_data in enumerate(rules_data, 1):
        try:
            rule_code = rule_data.get('rule_code')
            if not rule_code:
                print(f"  ⚠️  第 {idx} 条规则缺少 rule_code，跳过")
                failed_count += 1
                continue
            
            new_content = rule_data.get('content')
            if new_content is None:
                print(f"  ⚠️  规则 {rule_code} 缺少 content 字段，跳过")
                failed_count += 1
                continue
            
            # 查询当前规则（验证规则是否存在）
            # 先尝试精确匹配
            existing_rules = db.execute_query(
                'SELECT rule_code, content, conditions, rule_name FROM bazi_rules WHERE rule_code = %s',
                (rule_code,)
            )
            
            # 如果精确匹配失败，尝试模糊匹配（只匹配数字部分）
            if not existing_rules:
                # 提取数字部分（例如：从 "MARR-10156" 或 "10156" 提取 "10156"）
                import re
                number_match = re.search(r'(\d+)', str(rule_code))
                if number_match:
                    number_part = number_match.group(1)
                    # 使用 LIKE 匹配：匹配任何以数字结尾的 rule_code（如 MARR-10156, RULE-10156 等）
                    existing_rules = db.execute_query(
                        'SELECT rule_code, content, conditions, rule_name FROM bazi_rules WHERE rule_code LIKE %s',
                        (f'%-{number_part}',)  # 匹配 "*-10156" 格式
                    )
                    # 如果还是没找到，尝试匹配以数字开头的（如 10156）
                    if not existing_rules:
                        existing_rules = db.execute_query(
                            'SELECT rule_code, content, conditions, rule_name FROM bazi_rules WHERE rule_code = %s',
                            (number_part,)
                        )
                    # 如果找到了，显示匹配到的规则编号
                    if existing_rules:
                        matched_rule_code = existing_rules[0]['rule_code']
                        if matched_rule_code != rule_code:
                            print(f"  ℹ️  规则 {rule_code} 模糊匹配到 {matched_rule_code}")
            
            if not existing_rules:
                print(f"  ⚠️  规则 {rule_code} 不存在，跳过")
                not_found_count += 1
                continue
            
            existing_rule = existing_rules[0]
            # 使用实际匹配到的 rule_code（可能是模糊匹配的结果）
            actual_rule_code = existing_rule['rule_code']
            
            # 确保 new_content 是 JSON 字符串格式
            if isinstance(new_content, dict):
                new_content_json = json.dumps(new_content, ensure_ascii=False)
            elif isinstance(new_content, str):
                # 如果是字符串，尝试解析为 JSON，如果失败则包装为 {"text": ...}
                try:
                    json.loads(new_content)
                    new_content_json = new_content
                except:
                    new_content_json = json.dumps({"text": new_content}, ensure_ascii=False)
            else:
                new_content_json = json.dumps(new_content, ensure_ascii=False)
            
            if dry_run:
                # 显示对比信息
                old_content = existing_rule['content']
                if isinstance(old_content, str):
                    try:
                        old_content = json.loads(old_content)
                    except:
                        old_content = {"text": old_content}
                
                display_code = actual_rule_code if actual_rule_code != rule_code else rule_code
                print(f"  [模拟] 规则 {display_code}{' (原: ' + rule_code + ')' if actual_rule_code != rule_code else ''}:")
                print(f"    原内容: {json.dumps(old_content, ensure_ascii=False)}")
                print(f"    新内容: {new_content_json}")
                print(f"    规则名称: {existing_rule['rule_name']} (不变)")
                print(f"    规则条件: {json.dumps(existing_rule['conditions'], ensure_ascii=False)[:50]}... (不变)")
                print()
            else:
                # 只更新 content 字段，其他字段保持不变
                # 使用实际匹配到的 rule_code（可能是模糊匹配的结果）
                sql = """
                    UPDATE bazi_rules 
                    SET content = %s, updated_at = NOW()
                    WHERE rule_code = %s
                """
                db.execute_update(sql, (new_content_json, actual_rule_code))
                success_count += 1
                
                if idx % 10 == 0:
                    print(f"  进度: {idx}/{len(rules_data)} ({idx*100//len(rules_data)}%)")
        
        except Exception as e:
            failed_count += 1
            print(f"  ✗ 更新规则失败: {rule_data.get('rule_code', 'unknown')} - {e}")
            import traceback
            traceback.print_exc()
    
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
        'failed': failed_count,
        'not_found': not_found_count
    }


def export_rules_content_to_json(
    output_file: str,
    rule_type: Optional[str] = None,
    rule_code_pattern: Optional[str] = None
) -> int:
    """
    导出规则内容到 JSON 文件（只包含 rule_code 和 content，用于编辑）
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
        SELECT rule_code, content
        FROM bazi_rules 
        WHERE {where_sql}
        ORDER BY rule_code
    """
    
    rules = db.execute_query(query_sql, tuple(where_values))
    
    # 处理 JSON 字段
    rules_data = []
    for rule in rules:
        rule_dict = {
            'rule_code': rule['rule_code'],
        }
        
        # 解析 content
        if rule.get('content'):
            content = rule['content']
            if isinstance(content, str):
                try:
                    rule_dict['content'] = json.loads(content)
                except:
                    rule_dict['content'] = {"text": content}
            else:
                rule_dict['content'] = content
        else:
            rule_dict['content'] = {}
        
        rules_data.append(rule_dict)
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rules_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已导出 {len(rules_data)} 条规则内容到 {output_file}")
    return len(rules_data)


def main():
    parser = argparse.ArgumentParser(
        description='基于 JSON 文件批量修改规则内容（只修改 content 字段，其他字段不可改动）'
    )
    parser.add_argument('--mode', choices=['import', 'export'], required=True,
                       help='操作模式：import=从文件导入更新, export=导出规则内容到文件')
    
    # 导入模式
    parser.add_argument('--file', type=str, help='JSON 文件路径（import 模式）')
    
    # 导出模式
    parser.add_argument('--output', type=str, help='输出文件路径（export 模式）')
    parser.add_argument('--rule-type', type=str, help='规则类型筛选（可选）')
    parser.add_argument('--rule-code-pattern', type=str, help='规则代码模式（可选，支持 LIKE）')
    
    # 通用选项
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际更新数据库')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("基于 JSON 文件批量修改规则内容工具")
    print("（只修改 content 字段，其他字段不可改动）")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️  模拟运行模式（不会实际更新数据库）")
        print()
    
    try:
        if args.mode == 'import':
            if not args.file:
                print("❌ 错误：import 模式需要指定 --file 参数")
                return 1
            
            print(f"从文件导入规则内容: {args.file}")
            print()
            
            result = update_content_from_json(args.file, dry_run=args.dry_run)
            
            print("\n" + "=" * 60)
            print("更新结果：")
            print(f"  总计: {result['total']}")
            print(f"  成功: {result['success']}")
            print(f"  失败: {result['failed']}")
            print(f"  未找到: {result['not_found']}")
            print("=" * 60)
        
        elif args.mode == 'export':
            if not args.output:
                print("❌ 错误：export 模式需要指定 --output 参数")
                return 1
            
            print("导出规则内容到文件")
            if args.rule_type:
                print(f"  规则类型: {args.rule_type}")
            if args.rule_code_pattern:
                print(f"  规则代码模式: {args.rule_code_pattern}")
            print()
            
            count = export_rules_content_to_json(
                args.output,
                rule_type=args.rule_type,
                rule_code_pattern=args.rule_code_pattern
            )
            
            print("\n" + "=" * 60)
            print(f"✓ 导出完成，共 {count} 条规则")
            print(f"  编辑文件后，使用 --mode import --file {args.output} 导入更新")
            print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

