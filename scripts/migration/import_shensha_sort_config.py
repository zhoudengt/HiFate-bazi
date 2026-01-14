#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神煞排序配置导入脚本

从Excel文件导入神煞排序配置到数据库

使用方法：
    python3 scripts/migration/import_shensha_sort_config.py --file /path/to/excel.xlsx
    
    或使用默认路径：
    python3 scripts/migration/import_shensha_sort_config.py
"""

import sys
import os
import argparse
import logging

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def import_from_excel(file_path: str, dry_run: bool = False) -> int:
    """
    从Excel文件导入神煞排序配置
    
    Args:
        file_path: Excel文件路径
        dry_run: 是否只预览不实际导入
        
    Returns:
        int: 导入的记录数
    """
    import pandas as pd
    
    # 读取Excel文件
    logger.info(f"读取Excel文件: {file_path}")
    df = pd.read_excel(file_path)
    
    # 验证列名
    required_columns = ['ID 排序', '神煞名称', '白话文解析', '古诀']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Excel文件缺少必要的列: {missing_columns}")
    
    # 数据预处理
    records = []
    for _, row in df.iterrows():
        record = {
            'sort_order': int(row['ID 排序']),
            'name': str(row['神煞名称']).strip(),
            'plain_text_desc': str(row['白话文解析']).strip() if pd.notna(row['白话文解析']) else None,
            'ancient_desc': str(row['古诀']).strip() if pd.notna(row['古诀']) else None
        }
        records.append(record)
    
    logger.info(f"共读取 {len(records)} 条记录")
    
    if dry_run:
        logger.info("预览模式，显示前10条记录：")
        for i, record in enumerate(records[:10]):
            logger.info(f"  {i+1}. 排序:{record['sort_order']}, 名称:{record['name']}")
        return len(records)
    
    # 导入到数据库
    from server.db.mysql_connector import get_db_connection
    
    db = get_db_connection()
    
    # 使用 INSERT ... ON DUPLICATE KEY UPDATE 实现 upsert
    insert_sql = """
        INSERT INTO shensha_sort_config (sort_order, name, plain_text_desc, ancient_desc, enabled)
        VALUES (%s, %s, %s, %s, TRUE)
        ON DUPLICATE KEY UPDATE
            sort_order = VALUES(sort_order),
            plain_text_desc = VALUES(plain_text_desc),
            ancient_desc = VALUES(ancient_desc),
            enabled = TRUE,
            updated_at = CURRENT_TIMESTAMP
    """
    
    success_count = 0
    error_count = 0
    
    for record in records:
        try:
            db.execute_update(insert_sql, (
                record['sort_order'],
                record['name'],
                record['plain_text_desc'],
                record['ancient_desc']
            ))
            success_count += 1
        except Exception as e:
            logger.error(f"导入失败: {record['name']}, 错误: {e}")
            error_count += 1
    
    logger.info(f"导入完成: 成功 {success_count} 条, 失败 {error_count} 条")
    
    # 刷新缓存
    try:
        from server.services.shensha_sort_service import refresh_shensha_sort_cache
        refresh_shensha_sort_cache()
        logger.info("缓存已刷新")
    except Exception as e:
        logger.warning(f"刷新缓存失败（不影响导入结果）: {e}")
    
    return success_count


def main():
    parser = argparse.ArgumentParser(description='导入神煞排序配置')
    parser.add_argument(
        '--file', '-f',
        required=True,
        help='Excel文件路径（必填）'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='预览模式，不实际导入'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        logger.error(f"文件不存在: {args.file}")
        sys.exit(1)
    
    try:
        count = import_from_excel(args.file, args.dry_run)
        logger.info(f"处理完成，共 {count} 条记录")
    except Exception as e:
        logger.error(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
