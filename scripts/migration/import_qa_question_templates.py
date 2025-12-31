#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 AI问答.xlsx 问题模板到数据库

使用方法：
  python scripts/migration/import_qa_question_templates.py --dry-run  # 预览
  python scripts/migration/import_qa_question_templates.py            # 正式导入
"""

import sys
import os
import json
import argparse
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 尝试导入 pandas
try:
    import pandas as pd
except ImportError:
    print("❌ 需要安装 pandas: pip install pandas openpyxl")
    sys.exit(1)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

# Excel 文件路径
EXCEL_FILE = os.path.expanduser('~/Desktop/AI问答.xlsx')

# 分类映射
CATEGORY_MAP = {
    '想看事业财富？': 'career_wealth',
    '想看一下婚姻': 'marriage',
    '想看健康？': 'health',
    '想看子女': 'children',
    '想看2026年流年运势': 'liunian',
    '年运报告': 'yearly_report',
}

# 初始问题分类
INITIAL_CATEGORY = 'initial'


def parse_excel_file(excel_path: str) -> Dict[str, Any]:
    """
    解析 Excel 文件
    
    Returns:
        {
            'system_prompt': str,  # 系统提示词（第一列）
            'initial_question': str,  # 初始问题（第二列）
            'categories': {
                'career_wealth': [问题列表],
                'marriage': [问题列表],
                ...
            }
        }
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel 文件不存在: {excel_path}")
    
    print(f"📖 读取 Excel 文件: {excel_path}")
    
    # 读取 Excel 文件
    df = pd.read_excel(excel_path, header=None)
    
    # 清理数据：去除空行，填充 NaN
    df = df.dropna(how='all')
    df = df.fillna('')
    
    result = {
        'system_prompt': '',
        'initial_question': '',
        'categories': {}
    }
    
    current_category = None
    
    for idx, row in df.iterrows():
        # 第一列：系统提示词（只在第一行）
        if idx == 0 and pd.notna(row[0]) and row[0]:
            result['system_prompt'] = str(row[0]).strip()
        
        # 第二列：初始问题（只在第一行）
        if idx == 0 and pd.notna(row[1]) and row[1]:
            result['initial_question'] = str(row[1]).strip()
        
        # 第三列：分类标签
        if pd.notna(row[2]) and row[2]:
            category_text = str(row[2]).strip()
            if category_text in CATEGORY_MAP:
                current_category = CATEGORY_MAP[category_text]
                if current_category not in result['categories']:
                    result['categories'][current_category] = []
        
        # 第四列：具体问题
        if pd.notna(row[3]) and row[3]:
            question_text = str(row[3]).strip()
            if question_text:
                if current_category:
                    result['categories'][current_category].append(question_text)
                else:
                    # 如果没有分类，可能是初始问题的后续问题
                    if 'initial' not in result['categories']:
                        result['categories']['initial'] = []
                    result['categories']['initial'].append(question_text)
    
    # 添加初始问题到 initial 分类
    if result['initial_question']:
        if 'initial' not in result['categories']:
            result['categories']['initial'] = []
        result['categories']['initial'].insert(0, result['initial_question'])
    
    return result


def import_question_templates(data: Dict[str, Any], dry_run: bool = False) -> Tuple[int, int]:
    """
    导入问题模板到数据库
    
    Returns:
        (inserted, updated)
    """
    inserted = 0
    updated = 0
    
    if dry_run:
        print("\n=== DRY RUN 模式，不会修改数据库 ===\n")
    
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 导入初始问题
            if 'initial' in data['categories']:
                for question_text in data['categories']['initial']:
                    if dry_run:
                        print(f"将导入: [{INITIAL_CATEGORY}] {question_text[:50]}...")
                        continue
                    
                    # 检查是否存在
                    cursor.execute(
                        "SELECT id FROM qa_question_templates WHERE category = %s AND question_text = %s",
                        (INITIAL_CATEGORY, question_text)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        cursor.execute(
                            "UPDATE qa_question_templates SET enabled = 1, updated_at = NOW() WHERE id = %s",
                            (existing[0],)
                        )
                        updated += 1
                    else:
                        cursor.execute(
                            "INSERT INTO qa_question_templates (category, question_text, question_type, priority, enabled) VALUES (%s, %s, %s, %s, %s)",
                            (INITIAL_CATEGORY, question_text, 'user_selectable', 100, 1)
                        )
                        inserted += 1
            
            # 2. 导入各分类问题
            for category, questions in data['categories'].items():
                if category == 'initial':
                    continue
                
                for priority, question_text in enumerate(questions, start=1):
                    if dry_run:
                        print(f"将导入: [{category}] {question_text[:50]}...")
                        continue
                    
                    # 检查是否存在
                    cursor.execute(
                        "SELECT id FROM qa_question_templates WHERE category = %s AND question_text = %s",
                        (category, question_text)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        cursor.execute(
                            "UPDATE qa_question_templates SET priority = %s, enabled = 1, updated_at = NOW() WHERE id = %s",
                            (priority, existing[0])
                        )
                        updated += 1
                    else:
                        cursor.execute(
                            "INSERT INTO qa_question_templates (category, question_text, question_type, priority, enabled) VALUES (%s, %s, %s, %s, %s)",
                            (category, question_text, 'user_selectable', priority, 1)
                        )
                        inserted += 1
            
            if not dry_run:
                conn.commit()
    finally:
        return_mysql_connection(conn)
    
    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description='导入 AI问答.xlsx 问题模板到数据库')
    parser.add_argument('--excel', default=EXCEL_FILE, help='Excel 文件路径')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不修改数据库')
    args = parser.parse_args()
    
    try:
        # 1. 解析 Excel 文件
        print("=" * 60)
        print("开始导入问题模板")
        print("=" * 60)
        
        data = parse_excel_file(args.excel)
        
        print(f"\n📊 解析结果：")
        print(f"  系统提示词: {data['system_prompt'][:50]}...")
        print(f"  初始问题: {data['initial_question']}")
        print(f"  分类数量: {len(data['categories'])}")
        for category, questions in data['categories'].items():
            print(f"    - {category}: {len(questions)} 个问题")
        
        # 2. 导入到数据库
        print(f"\n📥 开始导入数据库...")
        inserted, updated = import_question_templates(data, args.dry_run)
        
        print(f"\n✅ 导入完成！")
        print(f"  新增: {inserted} 条")
        print(f"  更新: {updated} 条")
        
        if not args.dry_run:
            print(f"\n⚠️  注意：系统提示词需要手动配置到 Coze Bot 中")
            print(f"  提示词内容: {data['system_prompt']}")
        
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

