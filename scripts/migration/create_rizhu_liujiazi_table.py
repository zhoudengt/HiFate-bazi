#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建日元-六十甲子表
"""

import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

# 创建表的SQL语句
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `rizhu_liujiazi` (
    `id` INT PRIMARY KEY COMMENT 'ID（对应Excel中的ID）',
    `rizhu` VARCHAR(10) NOT NULL UNIQUE COMMENT '日柱（如：乙丑）',
    `analysis` TEXT NOT NULL COMMENT '对应解析（包含格式的完整文本）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_rizhu` (`rizhu`),
    INDEX `idx_rizhu` (`rizhu`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='日元-六十甲子表';
"""


def main():
    print("=" * 60)
    print("创建日元-六十甲子表")
    print("=" * 60)
    
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ 无法连接数据库")
            return
        
        with conn.cursor() as cursor:
            print("\n📝 执行创建表SQL...")
            cursor.execute(CREATE_TABLE_SQL)
            conn.commit()
            print("✅ 表创建成功")
            
            # 验证表是否存在
            cursor.execute("SHOW TABLES LIKE 'rizhu_liujiazi'")
            if cursor.fetchone():
                print("✅ 表验证成功：rizhu_liujiazi")
            else:
                print("❌ 表验证失败：rizhu_liujiazi 不存在")
                
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            return_mysql_connection(conn)


if __name__ == '__main__':
    main()

