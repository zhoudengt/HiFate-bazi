#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将润色后的【深度解读】更新到本地数据库 rizhu_liujiazi 表。

用法：
  python scripts/migration/apply_rizhu_shendu_polished_to_local.py
  python scripts/migration/apply_rizhu_shendu_polished_to_local.py --dry-run  # 仅打印将执行的条数
"""
import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 加载 .env 以使用 MYSQL_* 等配置
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
except ImportError:
    pass

SQL_FILE = os.path.join(PROJECT_ROOT, 'scripts', 'migration', 'rizhu_shendu_polished_update.sql')


def main():
    parser = argparse.ArgumentParser(description='将润色后的日柱【深度解读】更新到本地数据库')
    parser.add_argument('--dry-run', action='store_true', help='仅检查 SQL 文件与条数，不执行')
    args = parser.parse_args()

    if not os.path.exists(SQL_FILE):
        print(f"❌ SQL 文件不存在: {SQL_FILE}")
        sys.exit(1)

    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('--')]

    updates = [line for line in lines if line.startswith('UPDATE rizhu_liujiazi')]
    print(f"📄 将执行 {len(updates)} 条 UPDATE")
    if args.dry_run:
        return

    from shared.config.database import get_mysql_connection, return_mysql_connection
    conn = get_mysql_connection()
    if not conn:
        print("❌ 无法连接本地数据库。请在项目根目录 .env 中配置 MYSQL_HOST、MYSQL_PASSWORD（或 MYSQL_ROOT_PASSWORD）等。")
        sys.exit(1)

    try:
        with conn.cursor() as cursor:
            for i, sql in enumerate(updates, 1):
                cursor.execute(sql)
            conn.commit()
        print(f"✅ 已更新本地 rizhu_liujiazi 表 {len(updates)} 条记录")
    except Exception as e:
        conn.rollback()
        print(f"❌ 执行失败: {e}")
        sys.exit(1)
    finally:
        return_mysql_connection(conn)


if __name__ == '__main__':
    main()
