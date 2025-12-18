#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入每日运势新增Excel数据到数据库

支持的Excel文件：
- 幸运颜色-十神.xlsx (Sheet 1: 幸运颜色-万年历方位, Sheet 2: 幸运颜色-十神)
- 贵人之路-十神方位.xlsx
- 瘟神方位-地支方位.xlsx

使用方法：
  python scripts/migration/import_daily_fortune_excel_data.py --dry-run  # 预览
  python scripts/migration/import_daily_fortune_excel_data.py            # 正式导入
"""

import argparse
import os
import sys
from typing import Dict, List, Any, Optional, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 尝试导入 pandas
try:
    import pandas as pd
except ImportError:
    print("❌ 需要安装 pandas: pip install pandas openpyxl")
    sys.exit(1)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

# Excel文件路径
EXCEL_FILES = {
    'lucky_color': os.path.join(PROJECT_ROOT, 'docs', 'upload', '幸运颜色-十神.xlsx'),
    'guiren': os.path.join(PROJECT_ROOT, 'docs', 'upload', '贵人之路-十神方位.xlsx'),
    'wenshen': os.path.join(PROJECT_ROOT, 'docs', 'upload', '瘟神方位-地支方位.xlsx'),
}


def import_lucky_color_wannianli(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入幸运颜色-万年历方位数据（Sheet 1）"""
    xlsx_path = EXCEL_FILES['lucky_color']
    
    if not os.path.exists(xlsx_path):
        print(f"⚠️  文件不存在: {xlsx_path}")
        return 0, 0
    
    print(f"\n📖 读取文件: {xlsx_path} (Sheet: 幸运颜色-万年历方位)")
    
    try:
        # 尝试跳过前3行，使用第4行作为表头
        df = pd.read_excel(xlsx_path, sheet_name=0, skiprows=3)
    except Exception as e:
        print(f"⚠️  跳过前3行读取失败，尝试默认读取: {e}")
        try:
            df = pd.read_excel(xlsx_path, sheet_name=0)
        except Exception as e2:
            print(f"❌ 读取Sheet失败: {e2}")
            # 尝试使用sheet名称
            try:
                df = pd.read_excel(xlsx_path, sheet_name='幸运颜色-万年历方位')
            except:
                print(f"❌ 无法读取Sheet，请检查Excel文件")
                return 0, 0
    
    # 识别列名：方位、颜色
    direction_col = None
    colors_col = None
    
    for col in df.columns:
        col_str = str(col)
        if '方位' in col_str or '对应方位' in col_str:
            direction_col = col
        if '颜色' in col_str or '幸运颜色' in col_str:
            colors_col = col
    
    # 如果列名是Unnamed，尝试通过数据内容识别
    if not direction_col or not colors_col:
        # 检查第二列（索引1）是否包含"方位"
        if len(df.columns) >= 2:
            # 检查第二列的值是否包含方位名称
            sample_values = df.iloc[:5, 1].astype(str).tolist()
            if any('方位' in str(v) or v in ['正北', '正南', '正东', '正西', '东北', '西北', '东南', '西南', '中宫'] for v in sample_values):
                direction_col = df.columns[1]
                colors_col = df.columns[2] if len(df.columns) > 2 else df.columns[1]
            else:
                # 使用第二列和第三列
                direction_col = df.columns[1]
                colors_col = df.columns[2] if len(df.columns) > 2 else None
        else:
            print(f"❌ 无法识别列名，请检查Excel文件结构")
            print(f"   可用列: {list(df.columns)}")
            print(f"   前5行数据:")
            print(df.head(5))
            return 0, 0
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cursor:
        for _, row in df.iterrows():
            direction = str(row[direction_col]).strip() if pd.notna(row[direction_col]) else ''
            colors_raw = row[colors_col] if pd.notna(row[colors_col]) else ''
            
            if not direction or not colors_raw:
                continue
            
            # 处理颜色（可能是逗号分隔的字符串）
            colors_str = str(colors_raw).strip()
            # 清理颜色字符串，去除多余空格
            colors_list = [c.strip() for c in colors_str.split('、') if c.strip()]
            if not colors_list:
                colors_list = [c.strip() for c in colors_str.split(',') if c.strip()]
            colors = '、'.join(colors_list) if colors_list else colors_str
            
            if dry_run:
                print(f"  将导入: {direction} -> {colors}")
                inserted += 1
                continue
            
            # 检查是否存在
            cursor.execute(
                "SELECT id FROM daily_fortune_lucky_color_wannianli WHERE direction = %s",
                (direction,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute(
                    "UPDATE daily_fortune_lucky_color_wannianli SET colors = %s, enabled = TRUE WHERE direction = %s",
                    (colors, direction)
                )
                updated += 1
            else:
                # 插入
                cursor.execute(
                    "INSERT INTO daily_fortune_lucky_color_wannianli (direction, colors) VALUES (%s, %s)",
                    (direction, colors)
                )
                inserted += 1
    
    return inserted, updated


def import_lucky_color_shishen(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入幸运颜色-十神数据（Sheet 2）"""
    xlsx_path = EXCEL_FILES['lucky_color']
    
    if not os.path.exists(xlsx_path):
        print(f"⚠️  文件不存在: {xlsx_path}")
        return 0, 0
    
    print(f"\n📖 读取文件: {xlsx_path} (Sheet: 幸运颜色-十神)")
    
    try:
        # 尝试跳过前2行，使用第3行作为表头
        df = pd.read_excel(xlsx_path, sheet_name=1, skiprows=2)
    except Exception as e:
        print(f"⚠️  跳过前2行读取失败，尝试默认读取: {e}")
        try:
            # 尝试读取Sheet 2
            df = pd.read_excel(xlsx_path, sheet_name=1)
        except Exception as e2:
            print(f"❌ 读取Sheet失败: {e2}")
            # 尝试使用sheet名称
            try:
                df = pd.read_excel(xlsx_path, sheet_name='幸运颜色-十神')
            except:
                print(f"❌ 无法读取Sheet，请检查Excel文件")
                return 0, 0
    
    # 识别列名：十神、颜色
    shishen_col = None
    color_col = None
    
    for col in df.columns:
        col_str = str(col)
        if '十神' in col_str or '十神名称' in col_str:
            shishen_col = col
        if '颜色' in col_str or '幸运颜色' in col_str:
            color_col = col
    
    # 如果列名是Unnamed，尝试通过数据内容识别
    if not shishen_col or not color_col:
        # 检查第二列（索引1）是否包含十神名称
        if len(df.columns) >= 3:
            # 检查第二列的值是否包含十神名称
            sample_values = df.iloc[:5, 1].astype(str).tolist()
            if any(v in ['比肩', '劫财', '食神', '伤官', '正财', '偏财', '正官', '七杀', '正印', '偏印'] for v in sample_values):
                shishen_col = df.columns[1]
                color_col = df.columns[3] if len(df.columns) > 3 else df.columns[2]
            else:
                # 使用第二列和第三列
                shishen_col = df.columns[1]
                color_col = df.columns[3] if len(df.columns) > 3 else None
        else:
            print(f"❌ 无法识别列名，请检查Excel文件结构")
            print(f"   可用列: {list(df.columns)}")
            print(f"   前5行数据:")
            print(df.head(5))
            return 0, 0
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cursor:
        for _, row in df.iterrows():
            shishen = str(row[shishen_col]).strip() if pd.notna(row[shishen_col]) else ''
            color = str(row[color_col]).strip() if pd.notna(row[color_col]) else ''
            
            if not shishen or not color:
                continue
            
            if dry_run:
                print(f"  将导入: {shishen} -> {color}")
                inserted += 1
                continue
            
            # 检查是否存在
            cursor.execute(
                "SELECT id FROM daily_fortune_lucky_color_shishen WHERE shishen = %s",
                (shishen,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute(
                    "UPDATE daily_fortune_lucky_color_shishen SET color = %s, enabled = TRUE WHERE shishen = %s",
                    (color, shishen)
                )
                updated += 1
            else:
                # 插入
                cursor.execute(
                    "INSERT INTO daily_fortune_lucky_color_shishen (shishen, color) VALUES (%s, %s)",
                    (shishen, color)
                )
                inserted += 1
    
    return inserted, updated


def import_guiren_direction(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入贵人之路-十神方位数据"""
    xlsx_path = EXCEL_FILES['guiren']
    
    if not os.path.exists(xlsx_path):
        print(f"⚠️  文件不存在: {xlsx_path}")
        return 0, 0
    
    print(f"\n📖 读取文件: {xlsx_path}")
    df = pd.read_excel(xlsx_path)
    
    # 识别列名：日干、方位
    day_stem_col = None
    directions_col = None
    
    for col in df.columns:
        col_str = str(col)
        if '日干' in col_str or '天干' in col_str:
            day_stem_col = col
        if '方位' in col_str or '对应方位' in col_str:
            directions_col = col
    
    if not day_stem_col or not directions_col:
        # 尝试使用前两列
        if len(df.columns) >= 2:
            day_stem_col = df.columns[0]
            directions_col = df.columns[1]
        else:
            print(f"❌ 无法识别列名，请检查Excel文件结构")
            print(f"   可用列: {list(df.columns)}")
            return 0, 0
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cursor:
        for _, row in df.iterrows():
            day_stem = str(row[day_stem_col]).strip() if pd.notna(row[day_stem_col]) else ''
            directions_raw = row[directions_col] if pd.notna(row[directions_col]) else ''
            
            if not day_stem or not directions_raw:
                continue
            
            # 处理方位（可能是逗号分隔的字符串）
            directions_str = str(directions_raw).strip()
            # 清理方位字符串，去除多余空格
            directions_list = [d.strip() for d in directions_str.split('、') if d.strip()]
            if not directions_list:
                directions_list = [d.strip() for d in directions_str.split(',') if d.strip()]
            directions = '、'.join(directions_list) if directions_list else directions_str
            
            if dry_run:
                print(f"  将导入: {day_stem} -> {directions}")
                inserted += 1
                continue
            
            # 检查是否存在
            cursor.execute(
                "SELECT id FROM daily_fortune_guiren_direction WHERE day_stem = %s",
                (day_stem,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute(
                    "UPDATE daily_fortune_guiren_direction SET directions = %s, enabled = TRUE WHERE day_stem = %s",
                    (directions, day_stem)
                )
                updated += 1
            else:
                # 插入
                cursor.execute(
                    "INSERT INTO daily_fortune_guiren_direction (day_stem, directions) VALUES (%s, %s)",
                    (day_stem, directions)
                )
                inserted += 1
    
    return inserted, updated


def import_wenshen_direction(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入瘟神方位-地支方位数据"""
    xlsx_path = EXCEL_FILES['wenshen']
    
    if not os.path.exists(xlsx_path):
        print(f"⚠️  文件不存在: {xlsx_path}")
        return 0, 0
    
    print(f"\n📖 读取文件: {xlsx_path}")
    df = pd.read_excel(xlsx_path)
    
    # 识别列名：日支、方位
    day_branch_col = None
    direction_col = None
    
    for col in df.columns:
        col_str = str(col)
        if '日支' in col_str or '地支' in col_str or '地支名称' in col_str:
            day_branch_col = col
        if '方位' in col_str or '对应方位' in col_str:
            direction_col = col
    
    if not day_branch_col or not direction_col:
        # 尝试使用前两列
        if len(df.columns) >= 2:
            day_branch_col = df.columns[0]
            direction_col = df.columns[1]
        else:
            print(f"❌ 无法识别列名，请检查Excel文件结构")
            print(f"   可用列: {list(df.columns)}")
            return 0, 0
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cursor:
        for _, row in df.iterrows():
            day_branch = str(row[day_branch_col]).strip() if pd.notna(row[day_branch_col]) else ''
            direction = str(row[direction_col]).strip() if pd.notna(row[direction_col]) else ''
            
            if not day_branch or not direction:
                continue
            
            if dry_run:
                print(f"  将导入: {day_branch} -> {direction}")
                inserted += 1
                continue
            
            # 检查是否存在
            cursor.execute(
                "SELECT id FROM daily_fortune_wenshen_direction WHERE day_branch = %s",
                (day_branch,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute(
                    "UPDATE daily_fortune_wenshen_direction SET direction = %s, enabled = TRUE WHERE day_branch = %s",
                    (direction, day_branch)
                )
                updated += 1
            else:
                # 插入
                cursor.execute(
                    "INSERT INTO daily_fortune_wenshen_direction (day_branch, direction) VALUES (%s, %s)",
                    (day_branch, direction)
                )
                inserted += 1
    
    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description='导入每日运势新增Excel数据到数据库')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不修改数据库')
    args = parser.parse_args()
    
    if args.dry_run:
        print("=" * 60)
        print("=== DRY RUN 模式，不会修改数据库 ===")
        print("=" * 60)
    
    # 获取数据库连接
    conn = get_mysql_connection()
    
    try:
        total_inserted = 0
        total_updated = 0
        
        # 导入幸运颜色-万年历方位数据
        print("\n" + "=" * 60)
        print("1. 导入幸运颜色-万年历方位数据")
        print("=" * 60)
        inserted, updated = import_lucky_color_wannianli(conn, args.dry_run)
        total_inserted += inserted
        total_updated += updated
        print(f"✅ 完成: 新增 {inserted} 条，更新 {updated} 条")
        
        # 导入幸运颜色-十神数据
        print("\n" + "=" * 60)
        print("2. 导入幸运颜色-十神数据")
        print("=" * 60)
        inserted, updated = import_lucky_color_shishen(conn, args.dry_run)
        total_inserted += inserted
        total_updated += updated
        print(f"✅ 完成: 新增 {inserted} 条，更新 {updated} 条")
        
        # 导入贵人之路-十神方位数据
        print("\n" + "=" * 60)
        print("3. 导入贵人之路-十神方位数据")
        print("=" * 60)
        inserted, updated = import_guiren_direction(conn, args.dry_run)
        total_inserted += inserted
        total_updated += updated
        print(f"✅ 完成: 新增 {inserted} 条，更新 {updated} 条")
        
        # 导入瘟神方位-地支方位数据
        print("\n" + "=" * 60)
        print("4. 导入瘟神方位-地支方位数据")
        print("=" * 60)
        inserted, updated = import_wenshen_direction(conn, args.dry_run)
        total_inserted += inserted
        total_updated += updated
        print(f"✅ 完成: 新增 {inserted} 条，更新 {updated} 条")
        
        if not args.dry_run:
            conn.commit()
            print("\n" + "=" * 60)
            print("✅ 所有数据导入完成！")
            print("=" * 60)
            print(f"总计: 新增 {total_inserted} 条，更新 {total_updated} 条")
            
            # 清理每日运势缓存
            try:
                from server.services.daily_fortune_calendar_service import DailyFortuneCalendarService
                DailyFortuneCalendarService.invalidate_cache_for_date()
                print("\n✅ 已清理每日运势缓存")
            except Exception as e:
                print(f"\n⚠️  清理缓存失败（不影响数据导入）: {e}")
        else:
            print("\n" + "=" * 60)
            print("📋 预览完成（未修改数据库）")
            print("=" * 60)
            print(f"预计: 新增 {total_inserted} 条，更新 {total_updated} 条")
            print("\n💡 提示: 运行时不加 --dry-run 参数将正式导入数据")
    
    except Exception as e:
        if not args.dry_run:
            conn.rollback()
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        return_mysql_connection(conn)


if __name__ == '__main__':
    main()

