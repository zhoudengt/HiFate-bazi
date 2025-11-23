#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
"""

import sys
import os

# 添加项目根目录到路径（从 server/db 回到项目根：上移3级）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.db.mysql_connector import MySQLConnector
from server.config.mysql_config import mysql_config


def init_database():
    """初始化数据库和表结构"""
    print("=" * 60)
    print("开始初始化数据库...")
    print("=" * 60)
    
    # 创建连接器
    connector = MySQLConnector()
    
    try:
        # 1. 创建数据库
        print("\n1. 创建数据库...")
        connector.create_database_if_not_exists(mysql_config['database'])
        
        # 2. 读取并执行 SQL 脚本
        print("\n2. 创建表结构...")
        schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # 分割 SQL 语句（以分号分隔）
        statements = [s.strip() for s in sql_script.split(';') if s.strip() and not s.strip().startswith('--')]
        
        with connector.get_connection() as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    if statement:
                        try:
                            cursor.execute(statement)
                            print(f"  ✓ 执行成功: {statement[:50]}...")
                        except Exception as e:
                            # 忽略已存在的表/数据库错误
                            if "already exists" not in str(e).lower() and "Duplicate" not in str(e):
                                print(f"  ⚠ 执行警告: {e}")
                conn.commit()
        
        print("\n" + "=" * 60)
        print("数据库初始化完成！")
        print("=" * 60)

        # 2.1 执行可选迁移脚本（添加新列，向后兼容）
        migrations_file = os.path.join(os.path.dirname(__file__), 'migrations.sql')
        if os.path.exists(migrations_file):
            print("\n2.1 执行迁移脚本（如存在）...")
            with open(migrations_file, 'r', encoding='utf-8') as f:
                mig_script = f.read()
            statements = [s.strip() for s in mig_script.split(';') if s.strip() and not s.strip().startswith('--')]
            with connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    for statement in statements:
                        if statement:
                            try:
                                cursor.execute(statement)
                                print(f"  ✓ 迁移执行成功: {statement[:80]}...")
                            except Exception as e:
                                # 列已存在等错误忽略
                                if "Duplicate" in str(e) or "already exists" in str(e) or "errno: 1060" in str(e):
                                    print(f"  • 跳过（已存在）: {statement[:80]}...")
                                else:
                                    print(f"  ⚠ 迁移警告: {e}")
                    conn.commit()
        
        # 3. 测试连接
        print("\n3. 测试数据库连接...")
        result = connector.execute_query("SELECT DATABASE() as db")
        if result:
            print(f"  ✓ 当前数据库: {result[0]['db']}")
        
        result = connector.execute_query("SHOW TABLES")
        if result:
            print(f"  ✓ 表数量: {len(result)}")
            for table in result:
                table_name = list(table.values())[0]
                print(f"    - {table_name}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    init_database()



















