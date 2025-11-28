#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修改规则内容（只改内容，不改规则编号、条件等）
支持：
1. 给所有规则内容添加前缀/后缀
2. 替换规则内容中的文本
3. 修改特定规则的内容
"""

import argparse
import json
import os
import sys
import re
from typing import Any, Dict, List, Optional

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from server.db.mysql_connector import get_db_connection
from server.db.rule_content_dao import RuleContentDAO


def update_rule_content_by_code(rule_code: str, new_content: str, dry_run: bool = False) -> bool:
    """
    修改指定规则的内容
    
    Args:
        rule_code: 规则编号
        new_content: 新内容（字符串）
        dry_run: 是否模拟运行
    """
    db = get_db_connection()
    
    # 查询当前规则
    rules = db.execute_query(
        'SELECT rule_code, content FROM bazi_rules WHERE rule_code = %s',
        (rule_code,)
    )
    
    if not rules:
        print(f"❌ 未找到规则: {rule_code}")
        return False
    
    rule = rules[0]
    current_content = rule['content']
    
    # 解析当前内容
    if isinstance(current_content, str):
        try:
            current_content = json.loads(current_content)
        except:
            current_content = {'text': current_content}
    elif current_content is None:
        current_content = {}
    
    # 更新内容
    # 如果 content 是字典，更新 text 字段；否则直接替换
    if isinstance(current_content, dict):
        if 'text' in current_content:
            current_content['text'] = new_content
        else:
            # 如果没有 text 字段，添加一个
            current_content['text'] = new_content
    else:
        current_content = {'text': new_content}
    
    if dry_run:
        print(f"[模拟] 规则 {rule_code}:")
        print(f"  原内容: {rule['content']}")
        print(f"  新内容: {json.dumps(current_content, ensure_ascii=False)}")
        return True
    
    # 更新数据库
    sql = """
        UPDATE bazi_rules 
        SET content = %s, updated_at = NOW()
        WHERE rule_code = %s
    """
    db.execute_update(sql, (json.dumps(current_content, ensure_ascii=False), rule_code))
    print(f"✓ 已更新规则 {rule_code}")
    return True


def batch_add_prefix_to_all_rules(prefix: str, dry_run: bool = False) -> Dict[str, int]:
    """
    给所有规则内容添加前缀
    
    Args:
        prefix: 要添加的前缀（如 "注意关注，"）
        dry_run: 是否模拟运行
    """
    db = get_db_connection()
    rules = db.execute_query('SELECT rule_code, content FROM bazi_rules WHERE enabled = 1')
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for idx, rule in enumerate(rules, 1):
        try:
            rule_code = rule['rule_code']
            current_content = rule['content']
            
            # 解析当前内容
            if isinstance(current_content, str):
                try:
                    current_content = json.loads(current_content)
                except:
                    current_content = {'text': current_content}
            elif current_content is None:
                current_content = {}
            
            # 获取文本内容
            if isinstance(current_content, dict):
                text = current_content.get('text', '')
                if not text:
                    # 如果没有 text 字段，尝试其他字段
                    text = str(current_content)
            else:
                text = str(current_content)
            
            # 检查是否已有前缀
            if text.startswith(prefix):
                skipped_count += 1
                if idx % 100 == 0:
                    print(f"  进度: {idx}/{len(rules)} (已跳过 {skipped_count} 条)")
                continue
            
            # 添加前缀
            new_text = prefix + text
            
            # 更新内容
            if isinstance(current_content, dict):
                current_content['text'] = new_text
            else:
                current_content = {'text': new_text}
            
            if dry_run:
                if idx <= 5:  # 只显示前5条
                    print(f"  [模拟] 规则 {rule_code}: {text[:30]}... -> {new_text[:50]}...")
            else:
                sql = """
                    UPDATE bazi_rules 
                    SET content = %s, updated_at = NOW()
                    WHERE rule_code = %s
                """
                db.execute_update(sql, (json.dumps(current_content, ensure_ascii=False), rule_code))
                success_count += 1
                if idx % 100 == 0:
                    print(f"  进度: {idx}/{len(rules)} ({idx*100//len(rules)}%)")
        
        except Exception as e:
            failed_count += 1
            print(f"  ✗ 更新规则失败: {rule.get('rule_code', 'unknown')} - {e}")
    
    return {
        'total': len(rules),
        'success': success_count,
        'failed': failed_count,
        'skipped': skipped_count
    }


def batch_replace_content_text(
    old_text: str,
    new_text: str,
    rule_type: Optional[str] = None,
    rule_code_pattern: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    批量替换规则内容中的文本
    
    Args:
        old_text: 要替换的旧文本
        new_text: 新文本
        rule_type: 规则类型筛选（可选）
        rule_code_pattern: 规则代码模式（可选）
        dry_run: 是否模拟运行
    """
    db = get_db_connection()
    
    # 构建查询条件
    where_clauses = ['enabled = 1']
    where_values = []
    
    if rule_type:
        where_clauses.append('rule_type = %s')
        where_values.append(rule_type)
    
    if rule_code_pattern:
        where_clauses.append('rule_code LIKE %s')
        where_values.append(rule_code_pattern)
    
    where_sql = ' AND '.join(where_clauses)
    
    rules = db.execute_query(
        f'SELECT rule_code, content FROM bazi_rules WHERE {where_sql}',
        tuple(where_values)
    )
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for idx, rule in enumerate(rules, 1):
        try:
            rule_code = rule['rule_code']
            current_content = rule['content']
            
            # 解析当前内容
            if isinstance(current_content, str):
                try:
                    current_content = json.loads(current_content)
                except:
                    current_content = {'text': current_content}
            elif current_content is None:
                current_content = {}
            
            # 获取文本内容
            if isinstance(current_content, dict):
                text = current_content.get('text', '')
            else:
                text = str(current_content)
            
            # 检查是否包含要替换的文本
            if old_text not in text:
                skipped_count += 1
                continue
            
            # 替换文本
            new_content_text = text.replace(old_text, new_text)
            
            # 更新内容
            if isinstance(current_content, dict):
                current_content['text'] = new_content_text
            else:
                current_content = {'text': new_content_text}
            
            if dry_run:
                if idx <= 5:  # 只显示前5条
                    print(f"  [模拟] 规则 {rule_code}: {text[:50]}... -> {new_content_text[:50]}...")
            else:
                sql = """
                    UPDATE bazi_rules 
                    SET content = %s, updated_at = NOW()
                    WHERE rule_code = %s
                """
                db.execute_update(sql, (json.dumps(current_content, ensure_ascii=False), rule_code))
                success_count += 1
                if idx % 100 == 0:
                    print(f"  进度: {idx}/{len(rules)} ({idx*100//len(rules)}%)")
        
        except Exception as e:
            failed_count += 1
            print(f"  ✗ 更新规则失败: {rule.get('rule_code', 'unknown')} - {e}")
    
    return {
        'total': len(rules),
        'success': success_count,
        'failed': failed_count,
        'skipped': skipped_count
    }


def main():
    parser = argparse.ArgumentParser(description='批量修改规则内容（只改内容，不改规则编号、条件等）')
    parser.add_argument('--mode', choices=['single', 'prefix', 'replace'], required=True,
                       help='操作模式：single=修改单个规则, prefix=给所有规则添加前缀, replace=批量替换文本')
    
    # 单个规则模式
    parser.add_argument('--rule-code', type=str, help='规则编号（single 模式）')
    parser.add_argument('--new-content', type=str, help='新内容（single 模式）')
    
    # 前缀模式
    parser.add_argument('--prefix', type=str, help='要添加的前缀（prefix 模式，如 "注意关注，"）')
    
    # 替换模式
    parser.add_argument('--old-text', type=str, help='要替换的旧文本（replace 模式）')
    parser.add_argument('--new-text', type=str, help='新文本（replace 模式）')
    parser.add_argument('--rule-type', type=str, help='规则类型筛选（可选）')
    parser.add_argument('--rule-code-pattern', type=str, help='规则代码模式（可选，支持 LIKE）')
    
    # 通用选项
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际更新数据库')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("批量修改规则内容工具")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️  模拟运行模式（不会实际更新数据库）")
        print()
    
    try:
        if args.mode == 'single':
            if not args.rule_code or not args.new_content:
                print("❌ 错误：single 模式需要指定 --rule-code 和 --new-content 参数")
                return 1
            
            print(f"修改规则 {args.rule_code} 的内容")
            print(f"新内容: {args.new_content}")
            print()
            
            success = update_rule_content_by_code(args.rule_code, args.new_content, dry_run=args.dry_run)
            if success and not args.dry_run:
                RuleContentDAO.update_rule_version()
                print("\n✓ 规则版本号已更新")
        
        elif args.mode == 'prefix':
            if not args.prefix:
                print("❌ 错误：prefix 模式需要指定 --prefix 参数")
                return 1
            
            print(f"给所有规则内容添加前缀: \"{args.prefix}\"")
            print()
            
            result = batch_add_prefix_to_all_rules(args.prefix, dry_run=args.dry_run)
            print(f"\n总计: {result['total']}")
            print(f"成功: {result['success']}")
            print(f"失败: {result['failed']}")
            print(f"跳过: {result['skipped']} (已有前缀)")
            
            if not args.dry_run and result['success'] > 0:
                RuleContentDAO.update_rule_version()
                print("\n✓ 规则版本号已更新")
        
        elif args.mode == 'replace':
            if not args.old_text or not args.new_text:
                print("❌ 错误：replace 模式需要指定 --old-text 和 --new-text 参数")
                return 1
            
            print(f"批量替换规则内容中的文本")
            print(f"旧文本: \"{args.old_text}\"")
            print(f"新文本: \"{args.new_text}\"")
            if args.rule_type:
                print(f"规则类型: {args.rule_type}")
            if args.rule_code_pattern:
                print(f"规则代码模式: {args.rule_code_pattern}")
            print()
            
            result = batch_replace_content_text(
                args.old_text,
                args.new_text,
                rule_type=args.rule_type,
                rule_code_pattern=args.rule_code_pattern,
                dry_run=args.dry_run
            )
            print(f"\n总计: {result['total']}")
            print(f"成功: {result['success']}")
            print(f"失败: {result['failed']}")
            print(f"跳过: {result['skipped']} (不包含旧文本)")
            
            if not args.dry_run and result['success'] > 0:
                RuleContentDAO.update_rule_version()
                print("\n✓ 规则版本号已更新")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())

