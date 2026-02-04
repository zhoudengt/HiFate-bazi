#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境表检查和更新脚本

功能：
1. 检查 rizhu_liujiazi 表是否存在，不存在则创建
2. 检查 daily_fortune_zodiac 表是否存在，不存在则创建
3. 如果表存在，可以选择更新数据

使用方法：
  python scripts/db/check_and_update_tables_production.py                    # 只检查表，不更新数据
  python scripts/db/check_and_update_tables_production.py --update-data    # 检查表并更新数据
"""

import argparse
import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from shared.config.database import get_mysql_connection, return_mysql_connection

# 创建 rizhu_liujiazi 表的SQL
CREATE_RIZHU_LIUJIAZI_TABLE_SQL = """
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

# 创建 daily_fortune_zodiac 表的SQL
CREATE_DAILY_FORTUNE_ZODIAC_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `daily_fortune_zodiac` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `day_branch` VARCHAR(5) NOT NULL COMMENT '日支（如：辰）',
    `relation_type` VARCHAR(10) NOT NULL COMMENT '关系类型（合/冲/刑/破/害）',
    `target_branch` VARCHAR(5) NOT NULL COMMENT '目标地支（如：戌）',
    `target_zodiac` VARCHAR(10) NOT NULL COMMENT '目标生肖（如：狗）',
    `content` TEXT NOT NULL COMMENT '内容',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_day_branch_relation` (`day_branch`, `relation_type`, `target_branch`),
    INDEX `idx_day_branch` (`day_branch`),
    INDEX `idx_relation_type` (`relation_type`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='生肖刑冲破害表';
"""


def table_exists(cursor, table_name: str) -> bool:
    """检查表是否存在"""
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    result = cursor.fetchone()
    # 处理字典游标和元组游标
    if isinstance(result, dict):
        return result is not None
    else:
        return result is not None and len(result) > 0


def create_table_if_not_exists(cursor, table_name: str, create_sql: str) -> bool:
    """如果表不存在则创建"""
    if table_exists(cursor, table_name):
        print(f"  ✅ 表 {table_name} 已存在")
        return False
    else:
        print(f"  📝 表 {table_name} 不存在，正在创建...")
        try:
            cursor.execute(create_sql)
            print(f"  ✅ 表 {table_name} 创建成功")
            return True
        except Exception as e:
            print(f"  ❌ 创建表 {table_name} 失败: {e}")
            raise


def check_and_create_tables(update_data: bool = False):
    """检查并创建表"""
    print("=" * 60)
    print("生产环境表检查和更新")
    print("=" * 60)
    
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ 无法连接数据库")
            return False
        
        with conn.cursor() as cursor:
            print("\n📋 检查表状态...")
            
            # 检查 rizhu_liujiazi 表
            print("\n1. 检查 rizhu_liujiazi 表...")
            created_rizhu = create_table_if_not_exists(cursor, 'rizhu_liujiazi', CREATE_RIZHU_LIUJIAZI_TABLE_SQL)
            
            # 检查 daily_fortune_zodiac 表
            print("\n2. 检查 daily_fortune_zodiac 表...")
            created_zodiac = create_table_if_not_exists(cursor, 'daily_fortune_zodiac', CREATE_DAILY_FORTUNE_ZODIAC_TABLE_SQL)
            
            # 提交事务
            conn.commit()
            
            # 如果表已存在且需要更新数据
            if update_data:
                print("\n📊 更新数据...")
                
                # 更新 rizhu_liujiazi 数据
                if not created_rizhu:
                    print("\n  更新 rizhu_liujiazi 数据...")
                    try:
                        import subprocess
                        result = subprocess.run(
                            [sys.executable, os.path.join(PROJECT_ROOT, 'scripts', 'migration', 'import_rizhu_liujiazi.py')],
                            cwd=PROJECT_ROOT,
                            capture_output=True,
                            text=True
                        )
                        if result.returncode == 0:
                            print("  ✅ rizhu_liujiazi 数据更新成功")
                        else:
                            print(f"  ⚠️  rizhu_liujiazi 数据更新失败: {result.stderr}")
                    except Exception as e:
                        print(f"  ⚠️  更新 rizhu_liujiazi 数据时出错: {e}")
                
                # 更新 daily_fortune_zodiac 数据
                if not created_zodiac:
                    print("\n  更新 daily_fortune_zodiac 数据...")
                    try:
                        import subprocess
                        result = subprocess.run(
                            [sys.executable, os.path.join(PROJECT_ROOT, 'scripts', 'migration', 'import_daily_fortune_zodiac.py')],
                            cwd=PROJECT_ROOT,
                            capture_output=True,
                            text=True
                        )
                        if result.returncode == 0:
                            print("  ✅ daily_fortune_zodiac 数据更新成功")
                        else:
                            print(f"  ⚠️  daily_fortune_zodiac 数据更新失败: {result.stderr}")
                    except Exception as e:
                        print(f"  ⚠️  更新 daily_fortune_zodiac 数据时出错: {e}")
            
            # 最终验证
            print("\n🔍 最终验证...")
            cursor.execute("SHOW TABLES LIKE 'rizhu_liujiazi'")
            rizhu_result = cursor.fetchone()
            if rizhu_result:
                cursor.execute("SELECT COUNT(*) as count FROM rizhu_liujiazi")
                count_result = cursor.fetchone()
                if isinstance(count_result, dict):
                    rizhu_count = count_result.get('count', 0)
                else:
                    rizhu_count = count_result[0] if count_result else 0
                print(f"  ✅ rizhu_liujiazi 表存在，数据条数: {rizhu_count}")
            else:
                print("  ❌ rizhu_liujiazi 表不存在")
            
            cursor.execute("SHOW TABLES LIKE 'daily_fortune_zodiac'")
            zodiac_result = cursor.fetchone()
            if zodiac_result:
                cursor.execute("SELECT COUNT(*) as count FROM daily_fortune_zodiac")
                count_result = cursor.fetchone()
                if isinstance(count_result, dict):
                    zodiac_count = count_result.get('count', 0)
                else:
                    zodiac_count = count_result[0] if count_result else 0
                print(f"  ✅ daily_fortune_zodiac 表存在，数据条数: {zodiac_count}")
            else:
                print("  ❌ daily_fortune_zodiac 表不存在")
            
            print("\n" + "=" * 60)
            print("✅ 表检查和更新完成")
            print("=" * 60)
            return True
            
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            return_mysql_connection(conn)


def main():
    parser = argparse.ArgumentParser(description='生产环境表检查和更新')
    parser.add_argument('--update-data', action='store_true', help='如果表存在，更新数据')
    args = parser.parse_args()
    
    success = check_and_create_tables(update_data=args.update_data)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

