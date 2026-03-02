#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性导出每日运势相关表数据为JSON文件
"""

import os
import sys
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 加载 .env（必须在 import database 之前）
_env_path = os.path.join(project_root, '.env')
if os.path.exists(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from shared.config.database import get_mysql_connection, return_mysql_connection

OUTPUT_DIR = os.path.join(project_root, 'server', 'data', 'daily_fortune')


def _sanitize(obj):
    """递归转换bytes为str"""
    if isinstance(obj, bytes):
        return obj.decode('utf-8')
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj]
    return obj


def export_table(table_name: str, query: str, params: tuple = None) -> list:
    """导出单表数据"""
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            raise RuntimeError("无法获取数据库连接")
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            return [_sanitize(r) for r in rows]
    finally:
        if conn:
            return_mysql_connection(conn)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tables = [
        ('jiazi.json', 'daily_fortune_jiazi',
         "SELECT jiazi_day, content FROM daily_fortune_jiazi WHERE COALESCE(enabled, 1) = 1"),
        ('shishen_query.json', 'daily_fortune_shishen_query',
         "SELECT day_stem, birth_stem, shishen FROM daily_fortune_shishen_query WHERE COALESCE(enabled, 1) = 1"),
        ('shishen_meaning.json', 'daily_fortune_shishen_meaning',
         "SELECT shishen, hint, hint_keywords FROM daily_fortune_shishen_meaning WHERE COALESCE(enabled, 1) = 1"),
        ('zodiac.json', 'daily_fortune_zodiac',
         "SELECT day_branch, relation_type, target_branch, target_zodiac, content FROM daily_fortune_zodiac WHERE COALESCE(enabled, 1) = 1 ORDER BY day_branch, FIELD(relation_type, '合', '冲', '刑', '破', '害')"),
        ('jianchu.json', 'daily_fortune_jianchu',
         "SELECT jianchu, content, score FROM daily_fortune_jianchu WHERE COALESCE(enabled, 1) = 1"),
        ('lucky_color_wannianli.json', 'daily_fortune_lucky_color_wannianli',
         "SELECT direction, colors FROM daily_fortune_lucky_color_wannianli WHERE COALESCE(enabled, 1) = 1"),
        ('lucky_color_shishen.json', 'daily_fortune_lucky_color_shishen',
         "SELECT shishen, color FROM daily_fortune_lucky_color_shishen WHERE COALESCE(enabled, 1) = 1"),
        ('guiren_direction.json', 'daily_fortune_guiren_direction',
         "SELECT day_stem, directions FROM daily_fortune_guiren_direction WHERE COALESCE(enabled, 1) = 1"),
        ('wenshen_direction.json', 'daily_fortune_wenshen_direction',
         "SELECT day_branch, direction FROM daily_fortune_wenshen_direction WHERE COALESCE(enabled, 1) = 1"),
    ]

    for filename, table_name, query in tables:
        print(f"导出 {table_name}...")
        rows = export_table(table_name, query)
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"  -> {len(rows)} 条 -> {filepath}")

    print(f"\n完成，数据已导出到 {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
