#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从本地数据库导出 rizhu_liujiazi 数据到 SQL 文件

使用方法：
  python scripts/migration/export_rizhu_liujiazi_from_local.py
"""

import sys
import os
import json

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

def export_to_sql(output_file: str = "scripts/migration/rizhu_liujiazi_export.sql"):
    """导出数据到 SQL 文件"""
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ 无法连接到本地数据库")
            return False
        
        cursor = conn.cursor()
        
        # 查询所有数据
        cursor.execute("""
            SELECT id, rizhu, analysis, enabled
            FROM rizhu_liujiazi
            WHERE enabled = 1
            ORDER BY id
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️  本地数据库中没有数据")
            return False
        
        print(f"📊 找到 {len(rows)} 条记录")
        
        # 生成 SQL 文件
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("-- 日柱六十甲子数据导出\n")
            f.write(f"-- 导出时间: {os.popen('date').read().strip()}\n")
            f.write(f"-- 记录数: {len(rows)}\n\n")
            
            f.write("-- 创建表（如果不存在）\n")
            f.write("""CREATE TABLE IF NOT EXISTS `rizhu_liujiazi` (
    `id` INT PRIMARY KEY,
    `rizhu` VARCHAR(10) NOT NULL UNIQUE,
    `analysis` TEXT NOT NULL,
    `enabled` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_rizhu` (`rizhu`),
    INDEX `idx_rizhu` (`rizhu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

""")
            
            f.write("-- 插入/更新数据\n")
            for row in rows:
                if isinstance(row, dict):
                    record_id = row.get('id')
                    rizhu = row.get('rizhu', '')
                    analysis = row.get('analysis', '')
                    enabled = 1 if row.get('enabled', True) else 0
                else:
                    record_id = row[0]
                    rizhu = row[1] if len(row) > 1 else ''
                    analysis = row[2] if len(row) > 2 else ''
                    enabled = 1 if (row[3] if len(row) > 3 else True) else 0
                
                # 使用 UNHEX 确保编码正确
                rizhu_hex = rizhu.encode('utf-8').hex().upper()
                analysis_hex = analysis.encode('utf-8').hex().upper()
                
                # 注意：这是生成SQL文件，不是执行查询，所以使用字符串拼接是安全的
                # noqa: SQL字符串拼接（用于生成SQL文件，不执行查询）
                sql_line = f"INSERT INTO rizhu_liujiazi (id, rizhu, analysis, enabled) VALUES ({record_id}, UNHEX('{rizhu_hex}'), UNHEX('{analysis_hex}'), {enabled}) ON DUPLICATE KEY UPDATE rizhu=UNHEX('{rizhu_hex}'), analysis=UNHEX('{analysis_hex}'), enabled={enabled};\n"  # noqa: E501
                f.write(sql_line)
        
        print(f"✅ 数据已导出到: {output_file}")
        print(f"📊 共导出 {len(rows)} 条记录")
        return True
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            return_mysql_connection(conn)

if __name__ == '__main__':
    output_file = sys.argv[1] if len(sys.argv) > 1 else "scripts/migration/rizhu_liujiazi_export.sql"
    success = export_to_sql(output_file)
    sys.exit(0 if success else 1)

