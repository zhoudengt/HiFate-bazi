#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付相关数据库表迁移脚本
执行所有支付相关的数据库迁移 SQL 文件
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.config.database import get_mysql_connection, return_mysql_connection


def execute_sql_file(file_path: Path, conn):
    """执行 SQL 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割 SQL 语句（以分号分隔，但保留注释）
        statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            current_statement += line + '\n'
            
            if line.endswith(';'):
                statement = current_statement.strip()
                if statement:
                    statements.append(statement)
                current_statement = ""
        
        # 执行所有语句
        with conn.cursor() as cursor:
            for statement in statements:
                if statement.strip():
                    try:
                        cursor.execute(statement)
                        print(f"  ✓ 执行成功: {statement[:80]}...")
                    except Exception as e:
                        # 忽略已存在的表/索引错误
                        error_msg = str(e).lower()
                        if any(keyword in error_msg for keyword in [
                            'already exists', 'duplicate', 'errno: 1050', 'errno: 1061', 'errno: 1062'
                        ]):
                            print(f"  • 跳过（已存在）: {statement[:80]}...")
                        else:
                            print(f"  ⚠ 执行警告: {e}")
                            print(f"    语句: {statement[:100]}...")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"  ✗ 执行失败: {e}")
        if conn:
            conn.rollback()
        return False


def migrate_payment_tables():
    """执行支付相关数据库表迁移"""
    print("=" * 60)
    print("开始迁移支付相关数据库表...")
    print("=" * 60)
    
    # 迁移文件列表（按顺序执行）
    migration_files = [
        "create_payment_transactions_table.sql",
        "create_payment_region_config_table.sql",
        "create_payment_whitelist_table.sql",
        "create_payment_api_call_logs_table.sql",
        "create_fx_rate_history_table.sql",
        "create_conversion_fee_history_table.sql",
    ]
    
    # 获取 migrations 目录
    migrations_dir = project_root / "server" / "db" / "migrations"
    
    if not migrations_dir.exists():
        print(f"❌ 迁移目录不存在: {migrations_dir}")
        return False
    
    conn = None
    success_count = 0
    failed_count = 0
    
    try:
        conn = get_mysql_connection()
        
        for migration_file in migration_files:
            file_path = migrations_dir / migration_file
            
            if not file_path.exists():
                print(f"\n⚠ 迁移文件不存在: {file_path}")
                failed_count += 1
                continue
            
            print(f"\n执行迁移: {migration_file}")
            print("-" * 60)
            
            if execute_sql_file(file_path, conn):
                success_count += 1
                print(f"✓ {migration_file} 迁移成功")
            else:
                failed_count += 1
                print(f"✗ {migration_file} 迁移失败")
        
        print("\n" + "=" * 60)
        print("迁移完成！")
        print("=" * 60)
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        
        # 验证表是否创建成功
        print("\n验证表结构...")
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'payment%'")
            tables = cursor.fetchall()
            print(f"✓ 找到 {len(tables)} 个支付相关表:")
            for table in tables:
                table_name = list(table.values())[0]
                # 获取表记录数
                cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
                count_result = cursor.fetchone()
                count = count_result.get('count', 0) if count_result else 0
                print(f"  - {table_name} ({count} 条记录)")
        
        return failed_count == 0
        
    except Exception as e:
        print(f"\n❌ 迁移过程出错: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            return_mysql_connection(conn)


if __name__ == "__main__":
    try:
        success = migrate_payment_tables()
        if success:
            print("\n✅ 所有迁移成功完成！")
            sys.exit(0)
        else:
            print("\n⚠ 部分迁移失败，请检查日志")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠ 迁移被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 迁移脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
