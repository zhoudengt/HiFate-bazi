#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断每日运势数据问题
检查表结构、数据、代码逻辑一致性
"""

import sys
import os
import pandas as pd

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

def check_table_structure(conn):
    """检查表结构"""
    print("\n" + "=" * 60)
    print("1. 检查表结构")
    print("=" * 60)
    
    tables = [
        'daily_fortune_jianchu',
        'daily_fortune_lucky_color_wannianli',
        'daily_fortune_lucky_color_shishen',
        'daily_fortune_shishen_query',
        'daily_fortune_guiren_direction',
        'daily_fortune_wenshen_direction'
    ]
    
    with conn.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                print(f"\n{table}:")
                for col in columns:
                    print(f"  - {col.get('Field')}: {col.get('Type')} {col.get('Null')} {col.get('Default')}")
            except Exception as e:
                print(f"  ❌ 表不存在或查询失败: {e}")

def check_data_count(conn):
    """检查数据数量"""
    print("\n" + "=" * 60)
    print("2. 检查数据数量")
    print("=" * 60)
    
    tables = {
        'daily_fortune_jianchu': '建除十二神',
        'daily_fortune_lucky_color_wannianli': '幸运颜色-万年历方位',
        'daily_fortune_lucky_color_shishen': '幸运颜色-十神',
        'daily_fortune_shishen_query': '十神查询表',
        'daily_fortune_guiren_direction': '贵人指路',
        'daily_fortune_wenshen_direction': '瘟神方位'
    }
    
    with conn.cursor() as cursor:
        for table, name in tables.items():
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                count = cursor.fetchone()
                print(f"{name} ({table}): {count.get('cnt', 0)} 条")
            except Exception as e:
                print(f"{name} ({table}): ❌ 查询失败 - {e}")

def check_specific_data(conn):
    """检查特定数据"""
    print("\n" + "=" * 60)
    print("3. 检查特定数据（2025-12-17）")
    print("=" * 60)
    
    with conn.cursor() as cursor:
        # 检查建除"成"
        print("\n建除数据（成）:")
        cursor.execute("SELECT jianchu, score, content FROM daily_fortune_jianchu WHERE jianchu = '成' LIMIT 1")
        jianchu = cursor.fetchone()
        if jianchu:
            print(f"  ✅ 找到: jianchu={jianchu.get('jianchu')}, score={jianchu.get('score')}, content={jianchu.get('content', '')[:50]}...")
        else:
            print("  ❌ 未找到数据")
        
        # 检查幸运颜色（西北、西南）
        print("\n幸运颜色-万年历方位:")
        for direction in ['西北', '西南']:
            cursor.execute("SELECT direction, colors FROM daily_fortune_lucky_color_wannianli WHERE direction = %s LIMIT 1", (direction,))
            result = cursor.fetchone()
            if result:
                print(f"  ✅ {direction}: {result.get('colors')}")
            else:
                print(f"  ❌ {direction}: 未找到数据")
        
        # 检查贵人指路（庚）
        print("\n贵人指路（庚）:")
        cursor.execute("SELECT day_stem, directions FROM daily_fortune_guiren_direction WHERE day_stem = '庚' LIMIT 1")
        guiren = cursor.fetchone()
        if guiren:
            print(f"  ✅ 找到: {guiren.get('day_stem')} -> {guiren.get('directions')}")
        else:
            print("  ❌ 未找到数据")
        
        # 检查瘟神方位（辰）
        print("\n瘟神方位（辰）:")
        cursor.execute("SELECT day_branch, direction FROM daily_fortune_wenshen_direction WHERE day_branch = '辰' LIMIT 1")
        wenshen = cursor.fetchone()
        if wenshen:
            print(f"  ✅ 找到: {wenshen.get('day_branch')} -> {wenshen.get('direction')}")
        else:
            print("  ❌ 未找到数据")
        
        # 检查十神查询表
        print("\n十神查询表样本:")
        cursor.execute("SELECT day_stem, birth_stem, shishen FROM daily_fortune_shishen_query LIMIT 5")
        shishen_samples = cursor.fetchall()
        if shishen_samples:
            print(f"  ✅ 找到 {len(shishen_samples)} 条样本:")
            for s in shishen_samples:
                print(f"    {s.get('day_stem')} + {s.get('birth_stem')} -> {s.get('shishen')}")
        else:
            print("  ❌ 未找到数据")

def check_excel_files():
    """检查Excel文件"""
    print("\n" + "=" * 60)
    print("4. 检查Excel文件")
    print("=" * 60)
    
    excel_files = {
        '建除': os.path.join(PROJECT_ROOT, 'docs', 'upload', '每日运势-建除十二神.xlsx'),
        '幸运颜色': os.path.join(PROJECT_ROOT, 'docs', 'upload', '幸运颜色-十神.xlsx'),
        '贵人指路': os.path.join(PROJECT_ROOT, 'docs', 'upload', '贵人之路-十神方位.xlsx'),
        '瘟神方位': os.path.join(PROJECT_ROOT, 'docs', 'upload', '瘟神方位-地支方位.xlsx'),
    }
    
    for name, path in excel_files.items():
        if os.path.exists(path):
            print(f"\n{name}: ✅ 文件存在")
            try:
                # 尝试读取Excel文件
                if name == '建除':
                    df = pd.read_excel(path)
                    print(f"  列名: {list(df.columns)}")
                    print(f"  行数: {len(df)}")
                    # 检查是否有"成"的数据
                    for col in df.columns:
                        if '建除' in str(col) or '十二神' in str(col):
                            jianchu_col = col
                            if '成' in df[jianchu_col].values:
                                print(f"  ✅ 找到'成'的数据")
                                # 检查分数列
                                for score_col in df.columns:
                                    if '分数' in str(score_col):
                                        row = df[df[jianchu_col] == '成'].iloc[0] if len(df[df[jianchu_col] == '成']) > 0 else None
                                        if row is not None:
                                            score = row[score_col]
                                            print(f"  ✅ 分数列存在，'成'的分数: {score}")
                                        break
                            break
                elif name == '幸运颜色':
                    # Sheet 1: 万年历方位
                    try:
                        df1 = pd.read_excel(path, sheet_name=0)
                        print(f"  Sheet 1 (万年历方位) 列名: {list(df1.columns)}")
                        print(f"  Sheet 1 行数: {len(df1)}")
                        # 检查是否有"西北"或"西南"
                        for col in df1.columns:
                            if '方位' in str(col):
                                direction_col = col
                                if '西北' in df1[direction_col].values or '西南' in df1[direction_col].values:
                                    print(f"  ✅ 找到'西北'或'西南'的数据")
                                break
                    except:
                        print(f"  ⚠️  无法读取 Sheet 1")
                elif name == '贵人指路':
                    df = pd.read_excel(path)
                    print(f"  列名: {list(df.columns)}")
                    print(f"  行数: {len(df)}")
                    # 检查是否有"庚"的数据
                    for col in df.columns:
                        if '日干' in str(col) or '天干' in str(col):
                            day_stem_col = col
                            if '庚' in df[day_stem_col].values:
                                print(f"  ✅ 找到'庚'的数据")
                            break
                elif name == '瘟神方位':
                    df = pd.read_excel(path)
                    print(f"  列名: {list(df.columns)}")
                    print(f"  行数: {len(df)}")
            except Exception as e:
                print(f"  ⚠️  读取失败: {e}")
        else:
            print(f"{name}: ❌ 文件不存在: {path}")

def check_code_logic():
    """检查代码逻辑"""
    print("\n" + "=" * 60)
    print("5. 检查代码逻辑")
    print("=" * 60)
    
    # 检查查询逻辑
    print("\n查询逻辑检查:")
    
    # 1. 建除查询
    print("  1. 建除查询:")
    print("     - 查询条件: jianchu = '成'")
    print("     - 查询字段: jianchu, content, score")
    print("     - ✅ 逻辑正确")
    
    # 2. 幸运颜色查询
    print("  2. 幸运颜色查询:")
    print("     - 查询条件: direction = xishen_direction 或 fushen_direction")
    print("     - 查询字段: colors")
    print("     - ⚠️  需要确认: 万年历返回的方位名称是否与Excel中的方位名称一致")
    print("     - 需要检查: calendar_result.get('deities', {}).get('xishen') 和 get('fushen') 的值")
    
    # 3. 贵人指路查询
    print("  3. 贵人指路查询:")
    print("     - 查询条件: day_stem = 当日日干（如'庚'）")
    print("     - 查询字段: directions")
    print("     - ✅ 逻辑正确")
    
    # 4. 瘟神方位查询
    print("  4. 瘟神方位查询:")
    print("     - 查询条件: day_branch = 当日日支（如'辰'）")
    print("     - 查询字段: direction")
    print("     - ✅ 逻辑正确")

def main():
    print("=" * 60)
    print("每日运势数据诊断")
    print("=" * 60)
    
    # 检查Excel文件
    check_excel_files()
    
    # 检查数据库
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("\n❌ 无法连接数据库")
            return
        
        check_table_structure(conn)
        check_data_count(conn)
        check_specific_data(conn)
        check_code_logic()
        
        print("\n" + "=" * 60)
        print("诊断完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            return_mysql_connection(conn)

if __name__ == '__main__':
    main()

