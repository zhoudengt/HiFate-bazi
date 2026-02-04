#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步 service_configs 和 llm_input_formats 表数据到生产环境
"""

import sys
import os
import argparse
from typing import Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.config.database import get_mysql_connection, return_mysql_connection


def get_production_config() -> Dict[str, Any]:
    """获取生产环境数据库配置"""
    # 从环境变量或配置文件读取
    return {
        'host': os.getenv('PROD_MYSQL_HOST', '123.57.216.15'),
        'port': int(os.getenv('PROD_MYSQL_PORT', '3306')),
        'user': os.getenv('PROD_MYSQL_USER', 'root'),
        'password': os.getenv('PROD_MYSQL_PASSWORD', 'HiFate_Prod_2024!'),
        'database': os.getenv('PROD_MYSQL_DATABASE', 'hifate_bazi'),
        'charset': 'utf8mb4'
    }


def export_table_data(table_name: str, local_conn) -> str:
    """导出表数据为 SQL INSERT 语句"""
    with local_conn.cursor() as cursor:
        # 获取表结构
        cursor.execute(f"SHOW CREATE TABLE {table_name}")
        create_table = cursor.fetchone()
        if not create_table:
            raise ValueError(f"表 {table_name} 不存在")
        
        # 获取所有数据
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        if not rows:
            return f"-- 表 {table_name} 无数据\n"
        
        # 生成 SQL
        sql_lines = [f"-- 同步表 {table_name} 的数据", f"-- 共 {len(rows)} 条记录", ""]
        
        for row in rows:
            values = []
            for col in columns:
                value = row[col]
                if value is None:
                    values.append('NULL')
                elif isinstance(value, (dict, list)):
                    # JSON 类型
                    import json
                    values.append(f"'{json.dumps(value, ensure_ascii=False).replace(chr(39), chr(39)+chr(39))}'")
                elif isinstance(value, str):
                    # 字符串类型，转义单引号
                    values.append(f"'{value.replace(chr(39), chr(39)+chr(39))}'")
                elif isinstance(value, bool):
                    values.append('1' if value else '0')
                else:
                    values.append(str(value))
            
            sql_lines.append(
                f"INSERT INTO {table_name} ({', '.join(columns)}) "
                f"VALUES ({', '.join(values)}) "
                f"ON DUPLICATE KEY UPDATE "
                f"{', '.join([f'{col}=VALUES({col})' for col in columns if col != 'id'])};"
            )
        
        return '\n'.join(sql_lines) + '\n\n'


def sync_to_production(table_names: list, dry_run: bool = False):
    """同步表数据到生产环境"""
    print("=" * 60)
    print("同步配置表数据到生产环境")
    print("=" * 60)
    print(f"表: {', '.join(table_names)}")
    print(f"模式: {'预览模式（不执行）' if dry_run else '执行模式'}")
    print()
    
    # 连接本地数据库
    print("📥 连接本地数据库...")
    local_conn = get_mysql_connection()
    
    try:
        # 导出数据
        sql_content = []
        sql_content.append("-- ============================================")
        sql_content.append("-- 同步配置表数据到生产环境")
        sql_content.append(f"-- 生成时间: {__import__('datetime').datetime.now()}")
        sql_content.append("-- ============================================\n")
        sql_content.append("USE hifate_bazi;\n")
        
        for table_name in table_names:
            print(f"📤 导出表 {table_name} 的数据...")
            table_sql = export_table_data(table_name, local_conn)
            sql_content.append(table_sql)
            print(f"   ✅ 导出完成")
        
        sql_script = '\n'.join(sql_content)
        
        # 保存 SQL 文件
        sql_file = os.path.join(project_root, 'scripts', 'db', 'sync_config_tables_temp.sql')
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(sql_script)
        print(f"\n✅ SQL 脚本已保存: {sql_file}")
        
        if dry_run:
            print("\n" + "=" * 60)
            print("预览 SQL 脚本（前 100 行）:")
            print("=" * 60)
            print('\n'.join(sql_script.split('\n')[:100]))
            print("\n... (省略)")
            print("\n如需执行同步，请移除 --dry-run 参数")
            return
        
        # 连接生产数据库
        print("\n📤 连接生产数据库...")
        prod_config = get_production_config()
        import pymysql
        prod_conn = pymysql.connect(**prod_config)
        
        try:
            print("🔄 执行 SQL 脚本...")
            with prod_conn.cursor() as cursor:
                # 执行 SQL（逐条执行以便查看进度）
                statements = [s.strip() for s in sql_script.split(';') if s.strip() and not s.strip().startswith('--')]
                executed = 0
                for stmt in statements:
                    if stmt:
                        try:
                            cursor.execute(stmt)
                            executed += 1
                        except Exception as e:
                            print(f"  ⚠️  执行失败: {stmt[:50]}...")
                            print(f"     错误: {e}")
                prod_conn.commit()
                print(f"✅ 成功执行 {executed} 条 SQL 语句")
            
            # 验证数据
            print("\n🔍 验证同步结果...")
            with prod_conn.cursor() as cursor:
                for table_name in table_names:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
                    count = cursor.fetchone()['cnt']
                    print(f"  ✅ {table_name}: {count} 条记录")
            
            print("\n✅ 数据同步完成！")
            
        finally:
            prod_conn.close()
        
    finally:
        return_mysql_connection(local_conn)


def main():
    parser = argparse.ArgumentParser(description='同步配置表数据到生产环境')
    parser.add_argument('--tables', nargs='+', 
                       default=['service_configs', 'llm_input_formats'],
                       help='要同步的表名（默认: service_configs llm_input_formats）')
    parser.add_argument('--dry-run', action='store_true',
                       help='预览模式，不执行实际同步')
    
    args = parser.parse_args()
    
    sync_to_production(args.tables, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
