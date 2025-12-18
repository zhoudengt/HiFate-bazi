#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建每日运势相关表
"""

import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

# 创建表的SQL语句
CREATE_TABLES = [
    """CREATE TABLE IF NOT EXISTS `daily_fortune_lucky_color_wannianli` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `direction` VARCHAR(20) NOT NULL COMMENT '方位（如：西北）',
    `colors` VARCHAR(200) NOT NULL COMMENT '颜色（逗号分隔，如：白色、金色、银色）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_direction` (`direction`),
    INDEX `idx_direction` (`direction`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='幸运颜色-万年历方位表';""",
    
    """CREATE TABLE IF NOT EXISTS `daily_fortune_lucky_color_shishen` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `shishen` VARCHAR(20) NOT NULL COMMENT '十神名称（如：正财）',
    `color` VARCHAR(50) NOT NULL COMMENT '颜色（如：黄色）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_shishen` (`shishen`),
    INDEX `idx_shishen` (`shishen`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='幸运颜色-十神表';""",
    
    """CREATE TABLE IF NOT EXISTS `daily_fortune_guiren_direction` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `day_stem` VARCHAR(5) NOT NULL COMMENT '日干（如：乙）',
    `directions` VARCHAR(200) NOT NULL COMMENT '方位（逗号分隔，如：正北、西南）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_day_stem` (`day_stem`),
    INDEX `idx_day_stem` (`day_stem`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='贵人之路-十神方位表';""",
    
    """CREATE TABLE IF NOT EXISTS `daily_fortune_wenshen_direction` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `day_branch` VARCHAR(5) NOT NULL COMMENT '日支（如：巳）',
    `direction` VARCHAR(20) NOT NULL COMMENT '方位（如：东南）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_day_branch` (`day_branch`),
    INDEX `idx_day_branch` (`day_branch`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='瘟神方位-地支方位表';"""
]

def main():
    print("=" * 60)
    print("创建每日运势相关表")
    print("=" * 60)
    
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ 无法连接数据库")
            return
        
        with conn.cursor() as cursor:
            for sql in CREATE_TABLES:
                try:
                    cursor.execute(sql)
                    # 提取表名
                    table_name = sql.split('`')[1] if '`' in sql else 'unknown'
                    print(f"✓ 创建表: {table_name}")
                except Exception as e:
                    if 'already exists' not in str(e).lower() and 'Duplicate' not in str(e):
                        print(f"⚠️  创建表失败: {e}")
                        print(f"   SQL: {sql[:100]}...")
        
        conn.commit()
        print("\n✅ 所有表创建完成")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            return_mysql_connection(conn)

if __name__ == '__main__':
    main()

