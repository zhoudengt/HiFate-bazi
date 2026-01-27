#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证支付相关数据库表
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

def verify_tables():
    """验证所有支付相关表"""
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            # 查询所有支付相关表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'hifate_bazi' 
                AND (table_name LIKE '%payment%' 
                     OR table_name LIKE '%fx%' 
                     OR table_name LIKE '%conversion%')
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            
            print("=" * 60)
            print("支付相关数据库表验证")
            print("=" * 60)
            
            expected_tables = [
                'payment_transactions',
                'payment_region_config',
                'payment_whitelist',
                'payment_api_call_logs',
                'fx_rate_history',
                'conversion_fee_history',
            ]
            
            found_tables = []
            for row in tables:
                table_name = list(row.values())[0]
                found_tables.append(table_name)
                
                # 获取记录数
                cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
                count_result = cursor.fetchone()
                count = list(count_result.values())[0] if count_result else 0
                
                # 获取表结构信息
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()
                column_count = len(columns)
                
                status = "✓" if table_name in expected_tables else "?"
                print(f"{status} {table_name}: {count} 条记录, {column_count} 个字段")
            
            print("\n" + "-" * 60)
            print("验证结果:")
            
            missing = [t for t in expected_tables if t not in found_tables]
            if missing:
                print(f"  ✗ 缺失表: {', '.join(missing)}")
            else:
                print(f"  ✓ 所有表都已创建 ({len(found_tables)}/{len(expected_tables)})")
            
            return len(missing) == 0
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            return_mysql_connection(conn)

if __name__ == "__main__":
    success = verify_tables()
    sys.exit(0 if success else 1)
