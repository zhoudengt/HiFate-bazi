#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立导出脚本 - 不依赖 shared.config，可直接在生产服务器运行
用法: MYSQL_HOST=127.0.0.1 MYSQL_PASSWORD=xxx python3 scripts/export_daily_fortune_data_standalone.py
"""

import os
import sys
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print("需要安装 pymysql: pip install pymysql")
    sys.exit(1)

OUTPUT_DIR = os.path.join(project_root, 'server', 'data', 'daily_fortune')

MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', os.environ.get('PROD_MYSQL_PASSWORD', '')),
    'database': os.environ.get('MYSQL_DATABASE', 'hifate_bazi'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
}


def _sanitize(obj):
    if isinstance(obj, bytes):
        return obj.decode('utf-8')
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj]
    return obj


def export_table(query, params=None):
    conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            return [_sanitize(dict(r)) for r in rows]
    finally:
        conn.close()


def main():
    if not MYSQL_CONFIG['password']:
        print("请设置 MYSQL_PASSWORD 或 PROD_MYSQL_PASSWORD")
        sys.exit(1)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tables = [
        ('jiazi.json', "SELECT jiazi_day, content FROM daily_fortune_jiazi WHERE COALESCE(enabled, 1) = 1"),
        ('shishen_query.json', "SELECT day_stem, birth_stem, shishen FROM daily_fortune_shishen_query WHERE COALESCE(enabled, 1) = 1"),
        ('shishen_meaning.json', "SELECT shishen, hint, hint_keywords FROM daily_fortune_shishen_meaning WHERE COALESCE(enabled, 1) = 1"),
        ('zodiac.json', "SELECT day_branch, relation_type, target_branch, target_zodiac, content FROM daily_fortune_zodiac WHERE COALESCE(enabled, 1) = 1 ORDER BY day_branch, FIELD(relation_type, '合', '冲', '刑', '破', '害')"),
        ('jianchu.json', "SELECT jianchu, content, score FROM daily_fortune_jianchu WHERE COALESCE(enabled, 1) = 1"),
        ('lucky_color_wannianli.json', "SELECT direction, colors FROM daily_fortune_lucky_color_wannianli WHERE COALESCE(enabled, 1) = 1"),
        ('lucky_color_shishen.json', "SELECT shishen, color FROM daily_fortune_lucky_color_shishen WHERE COALESCE(enabled, 1) = 1"),
        ('guiren_direction.json', "SELECT day_stem, directions FROM daily_fortune_guiren_direction WHERE COALESCE(enabled, 1) = 1"),
        ('wenshen_direction.json', "SELECT day_branch, direction FROM daily_fortune_wenshen_direction WHERE COALESCE(enabled, 1) = 1"),
    ]

    for filename, query in tables:
        print("导出 %s..." % filename)
        rows = export_table(query)
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print("  -> %d 条 -> %s" % (len(rows), filepath))

    print("\n完成，数据已导出到 %s" % OUTPUT_DIR)


if __name__ == '__main__':
    main()
