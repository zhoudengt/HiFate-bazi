#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出每日运势相关数据为 SQL 脚本
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.config.database import get_mysql_connection, return_mysql_connection

def export_daily_fortune_data(output_file: str, db_name: str = "hifate_bazi"):
    """导出每日运势相关数据"""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("-- 每日运势数据同步脚本\n")
                f.write(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"USE {db_name};\n\n")
                
                # 1. 建除十二神数据
                f.write("-- 建除十二神数据\n")
                cursor.execute("SELECT jianchu, content, score, enabled FROM daily_fortune_jianchu")
                jianchu_data = cursor.fetchall()
                for row in jianchu_data:
                    jianchu = str(row['jianchu']).replace("'", "''")
                    content = str(row.get('content', '')).replace("'", "''")
                    score = row.get('score')
                    enabled = 1 if row.get('enabled', True) else 0
                    score_str = f"{score}" if score is not None else "NULL"
                    f.write(f"INSERT INTO daily_fortune_jianchu (jianchu, content, score, enabled) VALUES ('{jianchu}', '{content}', {score_str}, {enabled}) ON DUPLICATE KEY UPDATE content = '{content}', score = {score_str}, enabled = {enabled};\n")
                print(f"  建除十二神: {len(jianchu_data)} 条")
                
                # 2. 幸运颜色-万年历方位数据
                f.write("\n-- 幸运颜色-万年历方位数据\n")
                cursor.execute("SELECT direction, colors, enabled FROM daily_fortune_lucky_color_wannianli")
                wannianli_data = cursor.fetchall()
                for row in wannianli_data:
                    direction = str(row['direction']).replace("'", "''")
                    colors = str(row['colors']).replace("'", "''")
                    enabled = 1 if row.get('enabled', True) else 0
                    f.write(f"INSERT INTO daily_fortune_lucky_color_wannianli (direction, colors, enabled) VALUES ('{direction}', '{colors}', {enabled}) ON DUPLICATE KEY UPDATE colors = '{colors}', enabled = {enabled};\n")
                print(f"  幸运颜色-万年历方位: {len(wannianli_data)} 条")
                
                # 3. 幸运颜色-十神数据
                f.write("\n-- 幸运颜色-十神数据\n")
                cursor.execute("SELECT shishen, color, enabled FROM daily_fortune_lucky_color_shishen")
                shishen_data = cursor.fetchall()
                for row in shishen_data:
                    shishen = str(row['shishen']).replace("'", "''")
                    color = str(row['color']).replace("'", "''")
                    enabled = 1 if row.get('enabled', True) else 0
                    f.write(f"INSERT INTO daily_fortune_lucky_color_shishen (shishen, color, enabled) VALUES ('{shishen}', '{color}', {enabled}) ON DUPLICATE KEY UPDATE color = '{color}', enabled = {enabled};\n")
                print(f"  幸运颜色-十神: {len(shishen_data)} 条")
                
                # 4. 六十甲子数据
                f.write("\n-- 六十甲子数据\n")
                cursor.execute("SELECT jiazi_day, content, enabled FROM daily_fortune_jiazi")
                jiazi_data = cursor.fetchall()
                for row in jiazi_data:
                    jiazi_day = str(row['jiazi_day']).replace("'", "''")
                    content = str(row.get('content', '')).replace("'", "''")
                    enabled = 1 if row.get('enabled', True) else 0
                    f.write(f"INSERT INTO daily_fortune_jiazi (jiazi_day, content, enabled) VALUES ('{jiazi_day}', '{content}', {enabled}) ON DUPLICATE KEY UPDATE content = '{content}', enabled = {enabled};\n")
                print(f"  六十甲子: {len(jiazi_data)} 条")
                
                # 5. 十神查询数据
                f.write("\n-- 十神查询数据\n")
                cursor.execute("SELECT day_stem, birth_stem, shishen, enabled FROM daily_fortune_shishen_query")
                shishen_query_data = cursor.fetchall()
                for row in shishen_query_data:
                    day_stem = str(row['day_stem']).replace("'", "''")
                    birth_stem = str(row['birth_stem']).replace("'", "''")
                    shishen = str(row['shishen']).replace("'", "''")
                    enabled = 1 if row.get('enabled', True) else 0
                    f.write(f"INSERT INTO daily_fortune_shishen_query (day_stem, birth_stem, shishen, enabled) VALUES ('{day_stem}', '{birth_stem}', '{shishen}', {enabled}) ON DUPLICATE KEY UPDATE shishen = '{shishen}', enabled = {enabled};\n")
                print(f"  十神查询: {len(shishen_query_data)} 条")
                
                # 6. 十神象义数据
                f.write("\n-- 十神象义数据\n")
                cursor.execute("SELECT shishen, hint, hint_keywords, enabled FROM daily_fortune_shishen_meaning")
                shishen_meaning_data = cursor.fetchall()
                for row in shishen_meaning_data:
                    shishen = str(row['shishen']).replace("'", "''")
                    hint = str(row.get('hint', '')).replace("'", "''")
                    hint_keywords = str(row.get('hint_keywords', '')).replace("'", "''")
                    enabled = 1 if row.get('enabled', True) else 0
                    f.write(f"INSERT INTO daily_fortune_shishen_meaning (shishen, hint, hint_keywords, enabled) VALUES ('{shishen}', '{hint}', '{hint_keywords}', {enabled}) ON DUPLICATE KEY UPDATE hint = '{hint}', hint_keywords = '{hint_keywords}', enabled = {enabled};\n")
                print(f"  十神象义: {len(shishen_meaning_data)} 条")
                
                # 7. 生肖刑冲破害数据
                f.write("\n-- 生肖刑冲破害数据\n")
                cursor.execute("SELECT day_branch, relation_type, target_branch, target_zodiac, content, enabled FROM daily_fortune_zodiac")
                zodiac_data = cursor.fetchall()
                for row in zodiac_data:
                    day_branch = str(row['day_branch']).replace("'", "''")
                    relation_type = str(row['relation_type']).replace("'", "''")
                    target_branch = str(row['target_branch']).replace("'", "''")
                    target_zodiac = str(row['target_zodiac']).replace("'", "''")
                    content = str(row.get('content', '')).replace("'", "''")
                    enabled = 1 if row.get('enabled', True) else 0
                    f.write(f"INSERT INTO daily_fortune_zodiac (day_branch, relation_type, target_branch, target_zodiac, content, enabled) VALUES ('{day_branch}', '{relation_type}', '{target_branch}', '{target_zodiac}', '{content}', {enabled}) ON DUPLICATE KEY UPDATE content = '{content}', enabled = {enabled};\n")
                print(f"  生肖刑冲破害: {len(zodiac_data)} 条")
            
            print(f"\n✅ 数据导出成功: {output_file}")
            print(output_file)  # 输出文件路径供 bash 脚本使用
            return output_file
    finally:
        return_mysql_connection(conn)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="导出每日运势数据")
    parser.add_argument("--output", default="/tmp/daily_fortune_data.sql", help="输出文件路径")
    parser.add_argument("--database", default="hifate_bazi", help="数据库名")
    args = parser.parse_args()
    
    export_daily_fortune_data(args.output, args.database)

