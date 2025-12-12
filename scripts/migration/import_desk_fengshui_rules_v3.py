#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入办公桌风水规则 V3（扩充版，80-100条规则）
确保新规则正确编码，支持批量导入
"""

import sys
import os
import json

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

try:
    from server.config.mysql_config import get_mysql_connection, return_mysql_connection
    import pymysql
except ImportError:
    print("❌ 无法导入MySQL配置模块")
    sys.exit(1)


def ensure_utf8(text):
    """确保文本是UTF-8编码"""
    if isinstance(text, bytes):
        return text.decode('utf-8')
    if isinstance(text, str):
        return text
    return str(text)


def import_rules_from_sql_file(sql_file_path, dry_run=True):
    """
    从SQL文件导入规则
    
    Args:
        sql_file_path: SQL文件路径
        dry_run: 是否为预览模式
    """
    if not os.path.exists(sql_file_path):
        print(f"❌ SQL文件不存在: {sql_file_path}")
        return
    
    print(f"📖 读取SQL文件: {sql_file_path}")
    
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 解析SQL语句
    statements = []
    current_statement = ""
    
    for line in sql_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('--'):
            continue
        
        current_statement += line + " "
        
        if line.endswith(';'):
            statements.append(current_statement.strip())
            current_statement = ""
    
    print(f"📊 找到 {len(statements)} 条SQL语句")
    
    if dry_run:
        print("🔍 预览模式：不会修改数据库")
        print("=" * 80)
        for i, stmt in enumerate(statements[:5], 1):
            print(f"{i}. {stmt[:100]}...")
        if len(statements) > 5:
            print(f"... 还有 {len(statements) - 5} 条语句")
        print("=" * 80)
        print(f"💡 使用 --execute 参数执行实际导入")
        return
    
    # 执行导入
    conn = get_mysql_connection()
    try:
        # 确保连接使用utf8mb4字符集
        conn.set_charset('utf8mb4')
        cursor = conn.cursor()
        # 执行SET NAMES确保会话级别字符集
        cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        success_count = 0
        error_count = 0
        
        for i, stmt in enumerate(statements, 1):
            try:
                cursor.execute(stmt)
                success_count += 1
                if i % 10 == 0:
                    print(f"  ✅ 已执行 {i}/{len(statements)} 条语句")
            except Exception as e:
                error_count += 1
                print(f"  ❌ 第 {i} 条语句执行失败: {e}")
                print(f"     语句: {stmt[:100]}...")
        
        conn.commit()
        cursor.close()
        
        print("=" * 80)
        print(f"✅ 导入完成: {success_count} 条成功")
        if error_count > 0:
            print(f"⚠️  导入失败: {error_count} 条")
        
    except Exception as e:
        print(f"❌ 导入过程出错: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        return_mysql_connection(conn)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='导入办公桌风水规则V3')
    parser.add_argument('--sql-file', type=str, 
                       default='server/db/migrations/import_desk_fengshui_rules_v3.sql',
                       help='SQL文件路径')
    parser.add_argument('--execute', action='store_true', 
                       help='执行实际导入（默认是预览模式）')
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        print("🔍 预览模式：不会修改数据库")
    else:
        print("⚠️  执行模式：将修改数据库")
        response = input("确认继续？(yes/no): ")
        if response.lower() != 'yes':
            print("已取消")
            return
    
    print("\n开始导入规则...")
    import_rules_from_sql_file(args.sql_file, dry_run=dry_run)


if __name__ == '__main__':
    main()

