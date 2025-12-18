#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出幸运颜色数据为 SQL 脚本
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

def export_lucky_colors(output_file: str, db_name: str = "hifate_bazi"):
    """导出幸运颜色数据"""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            # 导出万年历方位数据
            cursor.execute("SELECT direction, colors, enabled FROM daily_fortune_lucky_color_wannianli")
            wannianli_data = cursor.fetchall()
            
            # 导出十神数据
            cursor.execute("SELECT shishen, color, enabled FROM daily_fortune_lucky_color_shishen")
            shishen_data = cursor.fetchall()
            
            # 生成 SQL 文件
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("-- 幸运颜色数据同步脚本\n")
                f.write(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"USE {db_name};\n\n")
                
                # 万年历方位数据
                f.write("-- 幸运颜色-万年历方位数据\n")
                for row in wannianli_data:
                    direction = str(row['direction']).replace("'", "''")
                    colors = str(row['colors']).replace("'", "''")
                    enabled = 1 if row.get('enabled', True) else 0
                    f.write(f"INSERT INTO daily_fortune_lucky_color_wannianli (direction, colors, enabled) VALUES ('{direction}', '{colors}', {enabled}) ON DUPLICATE KEY UPDATE colors = '{colors}', enabled = {enabled};\n")
                
                # 十神数据
                f.write("\n-- 幸运颜色-十神数据\n")
                for row in shishen_data:
                    shishen = str(row['shishen']).replace("'", "''")
                    color = str(row['color']).replace("'", "''")
                    enabled = 1 if row.get('enabled', True) else 0
                    f.write(f"INSERT INTO daily_fortune_lucky_color_shishen (shishen, color, enabled) VALUES ('{shishen}', '{color}', {enabled}) ON DUPLICATE KEY UPDATE color = '{color}', enabled = {enabled};\n")
            
            print(f"✅ 数据导出成功: {output_file}")
            print(f"   万年历方位: {len(wannianli_data)} 条")
            print(f"   十神: {len(shishen_data)} 条")
            print(output_file)  # 输出文件路径供 bash 脚本使用
            return output_file
    finally:
        return_mysql_connection(conn)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="导出幸运颜色数据")
    parser.add_argument("--output", default="/tmp/lucky_colors.sql", help="输出文件路径")
    parser.add_argument("--database", default="hifate_bazi", help="数据库名")
    args = parser.parse_args()
    
    export_lucky_colors(args.output, args.database)

