#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入每日运势Excel数据到数据库

支持的Excel文件：
- 每日运势-六十甲子.xlsx
- 每日运势-十神象义表.xlsx (Sheet 1: 查询表, Sheet 2: 十神象义表)
- 每日运势-生肖刑冲破害.xlsx
- 每日运势-建除十二神.xlsx

使用方法：
  python scripts/migration/import_daily_fortune_data.py --dry-run  # 预览
  python scripts/migration/import_daily_fortune_data.py            # 正式导入
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
    'jiazi': os.path.join(PROJECT_ROOT, 'docs', 'upload', '每日运势-六十甲子.xlsx'),
    'shishen': os.path.join(PROJECT_ROOT, 'docs', 'upload', '每日运势-十神象义表.xlsx'),
    'zodiac': os.path.join(PROJECT_ROOT, 'docs', 'upload', '每日运势-生肖刑冲破害.xlsx'),
    'jianchu': os.path.join(PROJECT_ROOT, 'docs', 'upload', '每日运势-建除十二神.xlsx'),
}

# 关系类型顺序（用于排序）
RELATION_ORDER = {'合': 1, '冲': 2, '刑': 3, '破': 4, '害': 5}


def import_jiazi_data(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入六十甲子运势数据"""
    xlsx_path = EXCEL_FILES['jiazi']
    
    if not os.path.exists(xlsx_path):
        print(f"⚠️  文件不存在: {xlsx_path}")
        return 0, 0
    
    print(f"\n📖 读取文件: {xlsx_path}")
    df = pd.read_excel(xlsx_path)
    
    # 精确识别列名：六十甲子日、每日运势显示内容
    jiazi_col = None
    content_col = None
    
    for col in df.columns:
        col_str = str(col)
        # 优先匹配"六十甲子日"或包含"甲子"的列
        if '六十甲子日' in col_str or ('甲子' in col_str and '日' in col_str and '运势' not in col_str):
            jiazi_col = col
        # 匹配包含"每日运势显示内容"或"运势显示内容"的列
        elif '每日运势显示内容' in col_str or ('运势' in col_str and '显示' in col_str and '内容' in col_str):
            content_col = col
    
    # 如果精确匹配失败，尝试使用列位置（排除ID列）
    if not jiazi_col or not content_col:
        # 找到ID列的位置
        id_col_idx = None
        for i, col in enumerate(df.columns):
            if 'ID' in str(col) or str(col) == 'ID':
                id_col_idx = i
                break
        
        # 使用ID列后的列
        if id_col_idx is not None:
            remaining_cols = [c for i, c in enumerate(df.columns) if i != id_col_idx]
            if len(remaining_cols) >= 2:
                jiazi_col = remaining_cols[0] if not jiazi_col else jiazi_col
                content_col = remaining_cols[1] if not content_col else content_col
        else:
            # 如果没有ID列，使用前两列
            if len(df.columns) >= 2:
                jiazi_col = df.columns[0] if not jiazi_col else jiazi_col
                content_col = df.columns[1] if not content_col else content_col
    
    if not content_col:
        print(f"❌ 无法识别列名，请检查Excel文件结构")
        print(f"   可用列: {list(df.columns)}")
        return 0, 0
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cursor:
        for _, row in df.iterrows():
            jiazi_day = str(row[jiazi_col]).strip()
            content = str(row[content_col]).strip() if pd.notna(row[content_col]) else ''
            
            if not jiazi_day or not content:
                continue
            
            if dry_run:
                print(f"  将导入: {jiazi_day} -> {content[:50]}...")
                inserted += 1
                continue
            
            # 检查是否存在
            cursor.execute(
                "SELECT id FROM daily_fortune_jiazi WHERE jiazi_day = %s",
                (jiazi_day,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute(
                    "UPDATE daily_fortune_jiazi SET content = %s, enabled = TRUE WHERE jiazi_day = %s",
                    (content, jiazi_day)
                )
                updated += 1
            else:
                # 插入
                cursor.execute(
                    "INSERT INTO daily_fortune_jiazi (jiazi_day, content) VALUES (%s, %s)",
                    (jiazi_day, content)
                )
                inserted += 1
    
    return inserted, updated


def import_shishen_query_data(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入十神查询表数据（Sheet 1）- 矩阵表格格式"""
    xlsx_path = EXCEL_FILES['shishen']
    
    if not os.path.exists(xlsx_path):
        print(f"⚠️  文件不存在: {xlsx_path}")
        return 0, 0
    
    print(f"\n📖 读取文件: {xlsx_path} (Sheet 1: 查询表)")
    # 读取时不使用header，因为第一行可能是空的
    df = pd.read_excel(xlsx_path, sheet_name=0, header=None)
    
    # 矩阵表格结构：
    # - 第一行：通常是空的
    # - 第二行：第一列可能是"日干"，后面是天干（甲、乙、丙...）
    # - 第三行开始：第一列是命主日干（甲、乙、丙...），后面的列是对应的十神
    
    # 找到"日干"行的位置（通常是第二行，索引1）
    day_stem_row_idx = None
    for idx, row in df.iterrows():
        row_values = [str(cell) for cell in row if pd.notna(cell)]
        if any('日干' in str(cell) for cell in row if pd.notna(cell)):
            day_stem_row_idx = idx
            break
    
    if day_stem_row_idx is None:
        # 如果找不到"日干"，假设第二行是日干行（索引1）
        day_stem_row_idx = 1
    
    # 获取当日日干列表（从第3列开始，索引2+，跳过第一列的NaN和第二列的"日干"）
    day_stems = []
    day_stem_row = df.iloc[day_stem_row_idx]
    for col_idx in range(2, len(day_stem_row)):  # 从索引2开始（第3列）
        cell_value = str(day_stem_row.iloc[col_idx]).strip()
        if cell_value and cell_value != 'nan' and cell_value not in ['日干', '']:
            day_stems.append(cell_value)
    
    if not day_stems:
        print(f"❌ 无法识别当日日干列表")
        print(f"   日干行索引: {day_stem_row_idx}")
        print(f"   日干行数据: {day_stem_row.tolist()}")
        return 0, 0
    
    print(f"   识别到 {len(day_stems)} 个当日日干: {day_stems}")
    
    inserted = 0
    updated = 0
    
    # 天干列表（用于验证）
    valid_stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    
    with conn.cursor() as cursor:
        # 从日干行的下一行开始读取数据（索引 day_stem_row_idx + 1）
        for row_idx in range(day_stem_row_idx + 1, len(df)):
            row = df.iloc[row_idx]
            # 第二列（索引1）是命主日干
            birth_stem = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ''
            
            # 验证命主日干是否有效
            if not birth_stem or birth_stem not in valid_stems:
                continue
            
            # 遍历当日日干列，获取对应的十神（从第3列开始，索引2+）
            for day_stem_idx, day_stem in enumerate(day_stems):
                col_idx = day_stem_idx + 2  # 从索引2开始（第3列）
                if col_idx >= len(row):
                    break
                
                shishen = str(row.iloc[col_idx]).strip() if pd.notna(row.iloc[col_idx]) else ''
                
                if not shishen or shishen == 'nan' or shishen == '':
                    continue
                
                if dry_run:
                    print(f"  将导入: {day_stem} + {birth_stem} -> {shishen}")
                    inserted += 1
                    continue
                
                # 检查是否存在
                cursor.execute(
                    "SELECT id FROM daily_fortune_shishen_query WHERE day_stem = %s AND birth_stem = %s",
                    (day_stem, birth_stem)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # 更新
                    cursor.execute(
                        "UPDATE daily_fortune_shishen_query SET shishen = %s, enabled = TRUE WHERE day_stem = %s AND birth_stem = %s",
                        (shishen, day_stem, birth_stem)
                    )
                    updated += 1
                else:
                    # 插入
                    cursor.execute(
                        "INSERT INTO daily_fortune_shishen_query (day_stem, birth_stem, shishen) VALUES (%s, %s, %s)",
                        (day_stem, birth_stem, shishen)
                    )
                    inserted += 1
    
    return inserted, updated


def import_shishen_meaning_data(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入十神象义表数据（Sheet 2）"""
    xlsx_path = EXCEL_FILES['shishen']
    
    if not os.path.exists(xlsx_path):
        print(f"⚠️  文件不存在: {xlsx_path}")
        return 0, 0
    
    print(f"\n📖 读取文件: {xlsx_path} (Sheet 2: 十神象义表)")
    
    # 尝试读取第二个Sheet
    try:
        df = pd.read_excel(xlsx_path, sheet_name=1)
    except:
        # 如果只有一个Sheet，尝试读取名为"十神象义表"的Sheet
        try:
            df = pd.read_excel(xlsx_path, sheet_name='十神象义表')
        except:
            print(f"⚠️  无法读取Sheet 2，尝试读取所有Sheet")
            xls = pd.ExcelFile(xlsx_path)
            if len(xls.sheet_names) > 1:
                df = pd.read_excel(xlsx_path, sheet_name=xls.sheet_names[1])
            else:
                print(f"❌ 文件只有一个Sheet，无法导入十神象义表")
                return 0, 0
    
    # 假设列名为：十神、十神提示、十神象义提示词（根据实际Excel调整）
    shishen_col = None
    hint_col = None
    hint_keywords_col = None
    
    for col in df.columns:
        col_str = str(col)
        if '十神' in col_str and '提示' not in col_str and '象义' not in col_str:
            shishen_col = col
        elif '十神提示' in col_str or ('提示' in col_str and '象义' not in col_str):
            hint_col = col
        elif '象义' in col_str or '提示词' in col_str:
            hint_keywords_col = col
    
    if not shishen_col or not hint_col or not hint_keywords_col:
        # 尝试使用前3列
        if len(df.columns) >= 3:
            shishen_col = df.columns[0]
            hint_col = df.columns[1]
            hint_keywords_col = df.columns[2]
        else:
            print(f"❌ 无法识别列名，请检查Excel文件结构")
            print(f"   可用列: {list(df.columns)}")
            return 0, 0
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cursor:
        for _, row in df.iterrows():
            shishen = str(row[shishen_col]).strip()
            hint = str(row[hint_col]).strip() if pd.notna(row[hint_col]) else ''
            hint_keywords = str(row[hint_keywords_col]).strip() if pd.notna(row[hint_keywords_col]) else ''
            
            if not shishen:
                continue
            
            if dry_run:
                print(f"  将导入: {shishen} -> {hint[:30]}... | {hint_keywords[:30]}...")
                inserted += 1
                continue
            
            # 检查是否存在
            cursor.execute(
                "SELECT id FROM daily_fortune_shishen_meaning WHERE shishen = %s",
                (shishen,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute(
                    "UPDATE daily_fortune_shishen_meaning SET hint = %s, hint_keywords = %s, enabled = TRUE WHERE shishen = %s",
                    (hint, hint_keywords, shishen)
                )
                updated += 1
            else:
                # 插入
                cursor.execute(
                    "INSERT INTO daily_fortune_shishen_meaning (shishen, hint, hint_keywords) VALUES (%s, %s, %s)",
                    (shishen, hint, hint_keywords)
                )
                inserted += 1
    
    return inserted, updated


def import_zodiac_data(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入生肖刑冲破害数据 - 矩阵表格格式（按行查询）"""
    xlsx_path = EXCEL_FILES['zodiac']
    
    if not os.path.exists(xlsx_path):
        print(f"⚠️  文件不存在: {xlsx_path}")
        return 0, 0
    
    print(f"\n📖 读取文件: {xlsx_path}")
    # 读取时不使用header，因为第一行可能是空的
    df = pd.read_excel(xlsx_path, header=None)
    
    # 矩阵表格结构（根据图片）：
    # - 第一行：空 | 空 | 子 | 丑 | 寅 | 卯 | 辰 | ...
    # - 第二行开始：第一列是日支（如"辰"），后续列是不同关系类型的内容
    # 例如"辰"行：辰 | 空 | ... | 破牛(丑) | 害兔(卯) | 刑龙(辰) | ... | 合鸡(酉) | 冲狗(戌)
    
    inserted = 0
    updated = 0
    
    # 地支列表（用于验证）
    valid_branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    from src.data.stems_branches import BRANCH_ZODIAC
    
    import re
    
    with conn.cursor() as cursor:
        # 从第二行开始读取数据（索引1+，因为索引0是第一行）
        for row_idx in range(1, len(df)):
            row = df.iloc[row_idx]
            
            # 第二列（索引1）是日支（如"辰"）
            day_branch_raw = row.iloc[1] if len(row) > 1 else None
            if pd.isna(day_branch_raw):
                continue
            
            day_branch = str(day_branch_raw).strip()
            if not day_branch or day_branch == 'nan' or day_branch not in valid_branches:
                continue
            
            # 遍历该行的所有列（从第3列开始，索引2+），提取所有非空内容
            for col_idx in range(2, len(row)):
                content_raw = row.iloc[col_idx]
                if pd.isna(content_raw):
                    continue
                
                content = str(content_raw).strip()
                if not content or content == 'nan' or content == '':
                    continue
                
                # ⚠️ 重要：一个单元格可能包含多个关系类型，需要分割处理
                # 例如："冲 虎 (寅)：变动较大 刑 虎 (寅)：行事勿取巧 刑 蛇 (巳)：行事勿取巧"
                # 需要分割成多个记录：冲虎(寅)、刑虎(寅)、刑蛇(巳)
                
                # 使用正则表达式分割内容，按关系类型分割
                # 匹配模式：关系类型 + 可选空格 + 生肖 + 可选空格 + (地支) + 可选空格 + 冒号 + 内容
                pattern = r'([合冲刑破害])\s*(\w+)\s*\((\w+)\)\s*[：:]?\s*([^合冲刑破害]*)'
                matches = re.finditer(pattern, content)
                
                for match in matches:
                    relation_type = match.group(1)
                    target_zodiac = match.group(2)
                    target_branch = match.group(3)
                    content_part = match.group(4).strip()
                    
                    # 清理内容：移除可能残留的"生肖(地支):"格式
                    while True:
                        pattern_clean = rf'{re.escape(target_zodiac)}\s*\(\s*{re.escape(target_branch)}\s*\)\s*[：:]?\s*'
                        new_content = re.sub(pattern_clean, '', content_part, count=1).strip()
                        if new_content == content_part:
                            break
                        content_part = new_content
                    
                    # 确保只保留第一行内容，处理多行情况
                    content_part = content_part.split('\n')[0].strip()
                    
                    if not content_part:
                        continue
                    
                    if dry_run:
                        print(f"  将导入: {day_branch} {relation_type} {target_zodiac}({target_branch}) -> {content_part[:50]}...")
                        inserted += 1
                        continue
                    
                    # 检查是否存在
                    cursor.execute(
                        "SELECT id FROM daily_fortune_zodiac WHERE day_branch = %s AND relation_type = %s AND target_branch = %s",
                        (day_branch, relation_type, target_branch)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 更新
                        cursor.execute(
                            "UPDATE daily_fortune_zodiac SET target_zodiac = %s, content = %s, enabled = TRUE WHERE day_branch = %s AND relation_type = %s AND target_branch = %s",
                            (target_zodiac, content_part, day_branch, relation_type, target_branch)
                        )
                        updated += 1
                    else:
                        # 插入
                        cursor.execute(
                            "INSERT INTO daily_fortune_zodiac (day_branch, relation_type, target_branch, target_zodiac, content) VALUES (%s, %s, %s, %s, %s)",
                            (day_branch, relation_type, target_branch, target_zodiac, content_part)
                        )
                        inserted += 1
    
    return inserted, updated


def import_jianchu_data(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入建除十二神数据"""
    xlsx_path = EXCEL_FILES['jianchu']
    
    if not os.path.exists(xlsx_path):
        print(f"⚠️  文件不存在: {xlsx_path}")
        return 0, 0
    
    print(f"\n📖 读取文件: {xlsx_path}")
    df = pd.read_excel(xlsx_path)
    
    # 假设列名为：建除十二神、能量小结显示内容、分数（根据实际Excel调整）
    jianchu_col = None
    content_col = None
    score_col = None
    
    for col in df.columns:
        col_str = str(col)
        if '建除' in col_str or '十二神' in col_str:
            jianchu_col = col
        if '能量' in col_str or '小结' in col_str or '内容' in col_str or '显示' in col_str:
            content_col = col
        if '分数' in col_str or '评分' in col_str or 'score' in col_str.lower():
            score_col = col
    
    if not jianchu_col or not content_col:
        # 尝试使用第一列和第二列
        jianchu_col = df.columns[0]
        content_col = df.columns[1] if len(df.columns) > 1 else None
        # 第三列可能是分数
        if len(df.columns) > 2:
            score_col = df.columns[2]
    
    if not content_col:
        print(f"❌ 无法识别列名，请检查Excel文件结构")
        print(f"   可用列: {list(df.columns)}")
        return 0, 0
    
    inserted = 0
    updated = 0
    
    with conn.cursor() as cursor:
        for _, row in df.iterrows():
            jianchu = str(row[jianchu_col]).strip()
            content = str(row[content_col]).strip() if pd.notna(row[content_col]) else ''
            
            if not jianchu or not content:
                continue
            
            # 解析分数
            score = None
            if score_col and pd.notna(row[score_col]):
                try:
                    score_value = str(row[score_col]).strip()
                    if score_value and score_value != 'nan':
                        score = int(float(score_value))
                except (ValueError, TypeError):
                    pass
            
            if dry_run:
                score_str = f", 分数: {score}" if score is not None else ""
                print(f"  将导入: {jianchu} -> {content[:50]}...{score_str}")
                inserted += 1
                continue
            
            # 检查是否存在
            cursor.execute(
                "SELECT id FROM daily_fortune_jianchu WHERE jianchu = %s",
                (jianchu,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                if score is not None:
                    cursor.execute(
                        "UPDATE daily_fortune_jianchu SET content = %s, score = %s, enabled = TRUE WHERE jianchu = %s",
                        (content, score, jianchu)
                    )
                else:
                    cursor.execute(
                        "UPDATE daily_fortune_jianchu SET content = %s, enabled = TRUE WHERE jianchu = %s",
                        (content, jianchu)
                    )
                updated += 1
            else:
                # 插入
                if score is not None:
                    cursor.execute(
                        "INSERT INTO daily_fortune_jianchu (jianchu, content, score) VALUES (%s, %s, %s)",
                        (jianchu, content, score)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO daily_fortune_jianchu (jianchu, content) VALUES (%s, %s)",
                        (jianchu, content)
                    )
                inserted += 1
    
    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description='导入每日运势Excel数据到数据库')
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
        
        # 导入六十甲子数据
        print("\n" + "=" * 60)
        print("1. 导入六十甲子运势数据")
        print("=" * 60)
        inserted, updated = import_jiazi_data(conn, args.dry_run)
        total_inserted += inserted
        total_updated += updated
        print(f"✅ 完成: 新增 {inserted} 条，更新 {updated} 条")
        
        # 导入十神查询表数据
        print("\n" + "=" * 60)
        print("2. 导入十神查询表数据")
        print("=" * 60)
        inserted, updated = import_shishen_query_data(conn, args.dry_run)
        total_inserted += inserted
        total_updated += updated
        print(f"✅ 完成: 新增 {inserted} 条，更新 {updated} 条")
        
        # 导入十神象义表数据
        print("\n" + "=" * 60)
        print("3. 导入十神象义表数据")
        print("=" * 60)
        inserted, updated = import_shishen_meaning_data(conn, args.dry_run)
        total_inserted += inserted
        total_updated += updated
        print(f"✅ 完成: 新增 {inserted} 条，更新 {updated} 条")
        
        # 导入生肖刑冲破害数据
        print("\n" + "=" * 60)
        print("4. 导入生肖刑冲破害数据")
        print("=" * 60)
        inserted, updated = import_zodiac_data(conn, args.dry_run)
        total_inserted += inserted
        total_updated += updated
        print(f"✅ 完成: 新增 {inserted} 条，更新 {updated} 条")
        
        # 导入建除十二神数据
        print("\n" + "=" * 60)
        print("5. 导入建除十二神数据")
        print("=" * 60)
        inserted, updated = import_jianchu_data(conn, args.dry_run)
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

