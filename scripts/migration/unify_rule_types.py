#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一规则类型命名 - 迁移 formula_* 格式到标准格式

将数据库中的 formula_wealth, formula_marriage 等格式统一为 wealth, marriage 等标准格式
"""

import sys
import os
import argparse

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

# 规则类型映射：formula_* -> 标准格式
RULE_TYPE_MAPPING = {
    'formula_wealth': 'wealth',
    'formula_marriage': 'marriage',
    'formula_career': 'career',
    'formula_children': 'children',
    'formula_character': 'character',
    'formula_summary': 'summary',
    'formula_health': 'health',
    'formula_peach_blossom': 'peach_blossom',
    'formula_shishen': 'shishen',
    'formula_parents': 'parents',
}

def check_rule_types(conn, dry_run=True):
    """检查需要迁移的规则类型"""
    with conn.cursor() as cursor:
        # 查找所有 formula_* 格式的规则类型
        cursor.execute("""
            SELECT DISTINCT rule_type, COUNT(*) as count
            FROM bazi_rules
            WHERE rule_type LIKE 'formula_%'
            GROUP BY rule_type
            ORDER BY rule_type
        """)
        results = cursor.fetchall()
        
        print("\n=== 需要迁移的规则类型 ===")
        total_count = 0
        for row in results:
            rule_type = row['rule_type']
            count = row['count']
            total_count += count
            new_type = RULE_TYPE_MAPPING.get(rule_type, rule_type.replace('formula_', ''))
            print(f"  {rule_type} -> {new_type}: {count} 条规则")
        
        print(f"\n总计: {total_count} 条规则需要迁移")
        
        # 检查是否有冲突（标准格式已存在）
        cursor.execute("""
            SELECT r1.rule_type as old_type, r2.rule_type as new_type, COUNT(*) as count
            FROM bazi_rules r1
            LEFT JOIN bazi_rules r2 ON r2.rule_type = %s
            WHERE r1.rule_type LIKE 'formula_%'
            GROUP BY r1.rule_type, r2.rule_type
        """, (RULE_TYPE_MAPPING.get('formula_wealth', 'wealth'),))
        
        conflicts = cursor.fetchall()
        if conflicts:
            print("\n⚠️  警告：发现可能的冲突（标准格式已存在）")
            for conflict in conflicts:
                print(f"  {conflict['old_type']} -> {conflict['new_type']}: {conflict['count']} 条")
        
        return results

def migrate_rule_types(conn, dry_run=True):
    """迁移规则类型"""
    if dry_run:
        print("\n=== DRY RUN 模式，不会修改数据库 ===\n")
    
    migrated_count = 0
    
    with conn.cursor() as cursor:
        for old_type, new_type in RULE_TYPE_MAPPING.items():
            # 检查是否存在
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM bazi_rules
                WHERE rule_type = %s
            """, (old_type,))
            result = cursor.fetchone()
            count = result['count'] if result else 0
            
            if count == 0:
                continue
            
            if dry_run:
                print(f"将迁移: {old_type} -> {new_type} ({count} 条规则)")
            else:
                # 执行迁移
                cursor.execute("""
                    UPDATE bazi_rules
                    SET rule_type = %s
                    WHERE rule_type = %s
                """, (new_type, old_type))
                migrated_count += cursor.rowcount
                print(f"✅ 已迁移: {old_type} -> {new_type} ({cursor.rowcount} 条规则)")
    
    if not dry_run:
        conn.commit()
        print(f"\n✅ 迁移完成，共迁移 {migrated_count} 条规则")
    else:
        print(f"\n预览完成，将迁移 {migrated_count} 条规则")
    
    return migrated_count

def main():
    parser = argparse.ArgumentParser(description='统一规则类型命名')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不修改数据库')
    args = parser.parse_args()
    
    print("=" * 60)
    print("统一规则类型命名 - 迁移 formula_* 格式到标准格式")
    print("=" * 60)
    
    conn = get_mysql_connection()
    try:
        # 1. 检查需要迁移的规则
        results = check_rule_types(conn, args.dry_run)
        
        if not results:
            print("\n✅ 没有需要迁移的规则类型")
            return
        
        # 2. 执行迁移
        migrate_rule_types(conn, args.dry_run)
        
        if args.dry_run:
            print("\n💡 提示：运行时不加 --dry-run 参数将正式执行迁移")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        if not args.dry_run:
            conn.rollback()
    finally:
        return_mysql_connection(conn)

if __name__ == '__main__':
    main()
