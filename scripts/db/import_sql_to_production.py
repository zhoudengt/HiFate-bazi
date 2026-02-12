#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 SQL 文件到生产环境数据库
"""

import sys
import os
import argparse

try:
    import pymysql
except ImportError:
    print("❌ 错误: 缺少 pymysql 模块，请安装: pip install pymysql")
    sys.exit(1)


def import_sql_file(sql_file: str, host: str = None, port: int = None, 
                    user: str = None, password: str = None, database: str = None):
    """
    导入 SQL 文件到数据库
    
    Args:
        sql_file: SQL 文件路径
        host: MySQL 主机（可选，从环境变量读取）
        port: MySQL 端口（可选，从环境变量读取）
        user: MySQL 用户（可选，从环境变量读取）
        password: MySQL 密码（可选，从环境变量读取）
        database: 数据库名（可选，从环境变量读取）
    """
    # 读取 SQL 文件
    print(f"📖 读取 SQL 文件: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 如果没有指定参数，从环境变量读取
    if not host:
        host = os.getenv('MYSQL_HOST', 'localhost')
    if not port:
        port = int(os.getenv('MYSQL_PORT', '3306'))
    if not user:
        user = os.getenv('MYSQL_USER', 'root')
    if not password:
        password = os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD', os.getenv("MYSQL_PASSWORD", "")))
    if not database:
        database = os.getenv('MYSQL_DATABASE', 'hifate_bazi')
    
    # 连接数据库
    print(f"🔌 连接数据库: {host}:{port}/{database}")
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        # 分割 SQL 语句（按分号和换行）
        statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            # 跳过注释和空行
            line = line.strip()
            if not line or line.startswith('--') or line.startswith('/*'):
                continue
            
            current_statement += line + '\n'
            
            # 如果行以分号结尾，说明是一个完整的语句
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        # 执行 SQL 语句
        print(f"📥 执行 {len(statements)} 条 SQL 语句...")
        cursor = conn.cursor()
        
        executed = 0
        for i, statement in enumerate(statements):
            if not statement:
                continue
            try:
                cursor.execute(statement)
                executed += 1
                if (i + 1) % 100 == 0:
                    print(f"  已执行 {i + 1}/{len(statements)} 条语句...")
            except Exception as e:
                # 忽略一些常见的错误（如表已存在等）
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    continue
                print(f"  ⚠️  语句执行失败（跳过）: {str(e)[:100]}")
        
        conn.commit()
        print(f"✅ 导入成功: 执行了 {executed} 条语句")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 导入失败: {e}")
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='导入 SQL 文件到生产环境数据库')
    parser.add_argument('sql_file', help='SQL 文件路径')
    parser.add_argument('--host', help='MySQL 主机')
    parser.add_argument('--port', type=int, help='MySQL 端口')
    parser.add_argument('--user', help='MySQL 用户')
    parser.add_argument('--password', help='MySQL 密码')
    parser.add_argument('--database', help='数据库名')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.sql_file):
        print(f"❌ SQL 文件不存在: {args.sql_file}")
        sys.exit(1)
    
    try:
        import_sql_file(
            args.sql_file,
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            database=args.database
        )
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

