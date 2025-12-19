#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入日元-六十甲子数据到数据库

支持的Excel文件：
- 日元-六十甲子.xlsx

使用方法：
  python scripts/migration/import_rizhu_liujiazi.py --dry-run  # 预览
  python scripts/migration/import_rizhu_liujiazi.py            # 正式导入
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
EXCEL_FILE = os.path.join(PROJECT_ROOT, 'docs', 'upload', '日元-六十甲子.xlsx')


def generate_unhex_sql(text: str) -> str:
    """
    生成 UNHEX SQL 语句（确保中文编码正确）
    
    Args:
        text: 要编码的文本（Unicode 字符串）
        
    Returns:
        UNHEX SQL 语句字符串
    """
    hex_encoding = text.encode('utf-8').hex().upper()
    return f"UNHEX('{hex_encoding}')"


def import_rizhu_liujiazi(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入日元-六十甲子数据"""
    
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ 文件不存在: {EXCEL_FILE}")
        return 0, 0
    
    print(f"\n📖 读取文件: {EXCEL_FILE}")
    
    try:
        # 读取Excel文件
        df = pd.read_excel(EXCEL_FILE, header=0)
    except Exception as e:
        print(f"❌ 读取Excel文件失败: {e}")
        return 0, 0
    
    # 检查列名
    print(f"   列名: {list(df.columns)}")
    print(f"   总行数: {len(df)}")
    
    # 识别列：ID、日柱、对应解析
    id_col = None
    rizhu_col = None
    analysis_col = None
    
    for col in df.columns:
        col_str = str(col).strip()
        if 'ID' in col_str.upper() or col_str.upper() == 'ID':
            id_col = col
        elif '日柱' in col_str:
            rizhu_col = col
        elif '对应解析' in col_str or '解析' in col_str:
            analysis_col = col
    
    # 如果列名识别失败，尝试使用位置（第一列、第二列、第三列）
    if not id_col or not rizhu_col or not analysis_col:
        if len(df.columns) >= 3:
            id_col = df.columns[0]
            rizhu_col = df.columns[1]
            analysis_col = df.columns[2]
            print(f"⚠️  使用位置识别列：ID={id_col}, 日柱={rizhu_col}, 对应解析={analysis_col}")
        else:
            print(f"❌ 无法识别列名，请检查Excel文件结构")
            print(f"   可用列: {list(df.columns)}")
            print(f"   前5行数据:")
            print(df.head(5))
            return 0, 0
    
    inserted = 0
    updated = 0
    errors = []
    
    print(f"\n📊 开始导入数据...")
    
    try:
        with conn.cursor() as cursor:
            for idx, row in df.iterrows():
                try:
                    # 获取数据
                    record_id = int(row[id_col]) if pd.notna(row[id_col]) else None
                    rizhu = str(row[rizhu_col]).strip() if pd.notna(row[rizhu_col]) else None
                    analysis = str(row[analysis_col]).strip() if pd.notna(row[analysis_col]) else None
                    
                    # 验证数据
                    if not record_id or not rizhu or not analysis:
                        errors.append(f"第{idx+2}行数据不完整: ID={record_id}, 日柱={rizhu}, 解析={analysis}")
                        continue
                    
                    if dry_run:
                        print(f"  [预览] ID={record_id}, 日柱={rizhu}, 解析长度={len(analysis)}")
                        continue
                    
                    # 检查是否存在
                    cursor.execute(
                        "SELECT id FROM rizhu_liujiazi WHERE id = %s",
                        (record_id,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 更新（使用UNHEX确保中文编码正确）
                        cursor.execute("""
                            UPDATE rizhu_liujiazi SET
                                rizhu = %s,
                                analysis = %s,
                                enabled = TRUE
                            WHERE id = %s
                        """, (
                            rizhu,
                            analysis,
                            record_id
                        ))
                        updated += 1
                        print(f"  ✓ 更新: ID={record_id}, 日柱={rizhu}")
                    else:
                        # 插入（使用UNHEX确保中文编码正确）
                        cursor.execute("""
                            INSERT INTO rizhu_liujiazi (id, rizhu, analysis, enabled)
                            VALUES (%s, %s, %s, TRUE)
                        """, (
                            record_id,
                            rizhu,
                            analysis
                        ))
                        inserted += 1
                        print(f"  ✓ 插入: ID={record_id}, 日柱={rizhu}")
                        
                except Exception as e:
                    error_msg = f"第{idx+2}行处理失败: {e}"
                    errors.append(error_msg)
                    print(f"  ❌ {error_msg}")
                    continue
        
        if not dry_run:
            conn.commit()
            print(f"\n✅ 导入完成: 新增 {inserted} 条, 更新 {updated} 条")
        else:
            print(f"\n✅ 预览完成: 将新增 {len(df)} 条记录")
        
        if errors:
            print(f"\n⚠️  错误记录 ({len(errors)} 条):")
            for error in errors[:10]:  # 只显示前10个错误
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... 还有 {len(errors) - 10} 个错误")
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    
    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description='导入日元-六十甲子数据')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不修改数据库')
    args = parser.parse_args()
    
    print("=" * 60)
    print("导入日元-六十甲子数据")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️  预览模式：不会修改数据库\n")
    
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ 无法连接数据库")
            return
        
        inserted, updated = import_rizhu_liujiazi(conn, dry_run=args.dry_run)
        
        if not args.dry_run:
            print(f"\n📊 导入统计:")
            print(f"   新增: {inserted} 条")
            print(f"   更新: {updated} 条")
            print(f"   总计: {inserted + updated} 条")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            return_mysql_connection(conn)


if __name__ == '__main__':
    main()

