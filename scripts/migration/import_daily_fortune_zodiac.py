#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入每日运势-生肖刑冲破害数据到数据库

Excel文件：docs/upload/每日运势-生肖刑冲破害.xlsx
目标表：daily_fortune_zodiac

使用方法：
  python scripts/migration/import_daily_fortune_zodiac.py --dry-run  # 预览
  python scripts/migration/import_daily_fortune_zodiac.py            # 正式导入
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
EXCEL_FILE = os.path.join(PROJECT_ROOT, 'docs', 'upload', '每日运势-生肖刑冲破害.xlsx')


def parse_cell_content(cell_value: str) -> List[Dict[str, str]]:
    """
    解析单元格内容，提取关系信息
    
    单元格格式示例：
    - "合 牛 (丑)： 今日易遇可靠伙伴..."
    - "刑 兔 (卯)： 今日需注意沟通方式..."
    - "合 蛇 (巳)：得人指点，利学习新技能 刑 蛇 (巳)：行事勿取巧，踏实行事"
    - "刑 虎 (寅)：远离是非，莫管闲事。\n刑 猴 (申)：远离是非，莫管闲事。"
    
    返回: [{"relation_type": "合", "target_zodiac": "牛", "target_branch": "丑", "content": "..."}, ...]
    """
    if not cell_value or pd.isna(cell_value):
        return []
    
    cell_str = str(cell_value).strip()
    if not cell_str:
        return []
    
    results = []
    valid_relation_types = ['合', '冲', '刑', '破', '害']
    
    import re
    # 先找到所有关系类型的开始位置
    # 匹配模式：关系类型 + 目标生肖 + (目标地支) + （可选冒号）
    pattern = r'([合冲刑破害])\s+([^\(\s]+)\s*\(([^\)]+)\)\s*[：:]?\s*'
    
    matches = list(re.finditer(pattern, cell_str))
    if not matches:
        return []
    
    # 按位置分割每条记录
    for i, match in enumerate(matches):
        relation_type = match.group(1)
        target_zodiac = match.group(2).strip()
        target_branch = match.group(3).strip()
        
        # 内容从匹配结束位置开始，到下一个关系类型或字符串结束
        content_start = match.end()
        if i + 1 < len(matches):
            content_end = matches[i + 1].start()
            content = cell_str[content_start:content_end].strip()
        else:
            content = cell_str[content_start:].strip()
        
        # 清理内容：去除末尾的换行符和多余空格
        content = re.sub(r'\s+', ' ', content).strip()
        
        if relation_type in valid_relation_types and target_zodiac and target_branch and content:
            results.append({
                'relation_type': relation_type,
                'target_zodiac': target_zodiac,
                'target_branch': target_branch,
                'content': content
            })
    
    return results


def import_zodiac_data(conn, dry_run: bool = False) -> Tuple[int, int]:
    """导入生肖刑冲破害数据"""
    
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ 文件不存在: {EXCEL_FILE}")
        return 0, 0
    
    print(f"\n📖 读取文件: {EXCEL_FILE}")
    
    try:
        # 第一行是数据，没有表头
        df = pd.read_excel(EXCEL_FILE, header=None)
    except Exception as e:
        print(f"❌ 读取Excel文件失败: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0
    
    inserted = 0
    updated = 0
    skipped = 0
    
    with conn.cursor() as cursor:
        for idx, row in df.iterrows():
            # 第2列（索引1）是日支
            day_branch = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) and len(row) > 1 else ''
            
            if not day_branch:
                continue
            
            # 从第3列开始（索引2及以后），每个单元格可能包含关系信息
            for col_idx in range(2, len(row)):
                cell_value = row.iloc[col_idx] if pd.notna(row.iloc[col_idx]) else ''
                
                if not cell_value:
                    continue
                
                # 解析单元格内容
                relations = parse_cell_content(cell_value)
                
                for rel in relations:
                    relation_type = rel['relation_type']
                    target_zodiac = rel['target_zodiac']
                    target_branch = rel['target_branch']
                    content = rel['content']
                    
                    if not day_branch or not relation_type or not target_branch or not content:
                        skipped += 1
                        if dry_run:
                            print(f"  ⚠️  跳过（数据不完整）: {day_branch} {relation_type} {target_zodiac} ({target_branch})")
                        continue
                    
                    if dry_run:
                        print(f"  将导入: {day_branch} {relation_type} {target_zodiac} ({target_branch}) - {content[:50]}...")
                        inserted += 1
                        continue
                    
                    # 检查是否存在（使用唯一键：day_branch, relation_type, target_branch）
                    cursor.execute(
                        "SELECT id FROM daily_fortune_zodiac WHERE day_branch = %s AND relation_type = %s AND target_branch = %s",
                        (day_branch, relation_type, target_branch)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 更新
                        cursor.execute(
                            """UPDATE daily_fortune_zodiac 
                               SET target_zodiac = %s, content = %s, enabled = TRUE, updated_at = CURRENT_TIMESTAMP
                               WHERE day_branch = %s AND relation_type = %s AND target_branch = %s""",
                            (target_zodiac, content, day_branch, relation_type, target_branch)
                        )
                        updated += 1
                    else:
                        # 插入
                        cursor.execute(
                            """INSERT INTO daily_fortune_zodiac 
                               (day_branch, relation_type, target_branch, target_zodiac, content, enabled) 
                               VALUES (%s, %s, %s, %s, %s, TRUE)""",
                            (day_branch, relation_type, target_branch, target_zodiac, content)
                        )
                        inserted += 1
    
    if skipped > 0:
        print(f"  ⚠️  跳过了 {skipped} 条无效数据")
    
    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description='导入每日运势-生肖刑冲破害数据到数据库')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不修改数据库')
    args = parser.parse_args()
    
    if args.dry_run:
        print("=" * 60)
        print("=== DRY RUN 模式，不会修改数据库 ===")
        print("=" * 60)
    
    # 获取数据库连接
    conn = get_mysql_connection()
    
    try:
        # 导入生肖刑冲破害数据
        print("\n" + "=" * 60)
        print("导入每日运势-生肖刑冲破害数据")
        print("=" * 60)
        inserted, updated = import_zodiac_data(conn, args.dry_run)
        
        if not args.dry_run:
            conn.commit()
            print("\n" + "=" * 60)
            print("✅ 数据导入完成！")
            print("=" * 60)
            print(f"总计: 新增 {inserted} 条，更新 {updated} 条")
            
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
            print(f"预计: 新增 {inserted} 条，更新 {updated} 条")
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

