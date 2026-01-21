#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页内容表数据库迁移脚本

功能：
1. 创建 homepage_contents 表（如果不存在）
2. 验证表结构
3. 可选：初始化默认数据

使用方法：
  python scripts/db/migrate_homepage_contents.py                    # 只创建表
  python scripts/db/migrate_homepage_contents.py --init-data       # 创建表并初始化数据
"""

import argparse
import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection


# 创建 homepage_contents 表的SQL
CREATE_HOMEPAGE_CONTENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `homepage_contents` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `title` VARCHAR(200) NOT NULL COMMENT '标题（如：AI守护神、八字命理等）',
    `tags` JSON COMMENT '标签列表（JSON数组，如：["科技", "精准"]）',
    `description` TEXT COMMENT '详细描述',
    `image_base64` LONGTEXT COMMENT '图片Base64编码（包含data:image前缀）',
    `sort_order` INT DEFAULT 0 COMMENT '排序字段（数字越小越靠前）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_sort_order` (`sort_order`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_enabled_sort` (`enabled`, `sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='首页内容表';
"""


def table_exists(cursor, table_name: str) -> bool:
    """检查表是否存在"""
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() AND table_name = %s
    """, (table_name,))
    result = cursor.fetchone()
    # 处理字典游标和元组游标
    if isinstance(result, dict):
        return result.get('count', 0) > 0
    else:
        return result[0] > 0 if result else False


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


def verify_table_structure(cursor, table_name: str) -> bool:
    """验证表结构"""
    try:
        cursor.execute(f"DESCRIBE `{table_name}`")
        columns = cursor.fetchall()
        
        # 检查关键字段
        required_columns = ['id', 'title', 'tags', 'description', 'image_base64', 'sort_order', 'enabled']
        column_names = [col['Field'] if isinstance(col, dict) else col[0] for col in columns]
        
        missing_columns = [col for col in required_columns if col not in column_names]
        if missing_columns:
            print(f"  ⚠️  表 {table_name} 缺少以下字段: {missing_columns}")
            return False
        
        print(f"  ✅ 表 {table_name} 结构验证通过（共 {len(columns)} 个字段）")
        return True
    except Exception as e:
        print(f"  ❌ 验证表结构失败: {e}")
        return False


def migrate_database(init_data: bool = False):
    """执行数据库迁移"""
    print("=" * 60)
    print("首页内容表数据库迁移")
    print("=" * 60)
    
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ 无法连接数据库")
            return False
        
        print(f"✅ 数据库连接成功")
        print(f"   数据库: {conn.db.decode() if isinstance(conn.db, bytes) else conn.db}")
        print()
        
        with conn.cursor() as cursor:
            # 创建表
            print("📋 步骤 1: 检查并创建表...")
            table_created = create_table_if_not_exists(cursor, 'homepage_contents', CREATE_HOMEPAGE_CONTENTS_TABLE_SQL)
            
            # 验证表结构
            print()
            print("🔍 步骤 2: 验证表结构...")
            if not verify_table_structure(cursor, 'homepage_contents'):
                print("❌ 表结构验证失败")
                return False
            
            # 提交事务
            conn.commit()
            print()
            print("✅ 数据库迁移完成！")
            
            # 初始化数据（如果需要）
            if init_data:
                print()
                print("📊 步骤 3: 初始化数据...")
                try:
                    # 导入初始化脚本
                    from scripts.db.init_homepage_contents import init_homepage_contents
                    init_homepage_contents()
                except Exception as e:
                    print(f"⚠️  初始化数据失败: {e}")
                    print("   你可以稍后手动运行: python scripts/db/init_homepage_contents.py")
            
            return True
            
    except Exception as e:
        print(f"❌ 数据库迁移失败: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            return_mysql_connection(conn)


def main():
    parser = argparse.ArgumentParser(description='首页内容表数据库迁移脚本')
    parser.add_argument(
        '--init-data',
        action='store_true',
        help='创建表后初始化默认数据'
    )
    
    args = parser.parse_args()
    
    success = migrate_database(init_data=args.init_data)
    
    if success:
        print()
        print("=" * 60)
        print("✅ 迁移成功完成！")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ 迁移失败，请检查错误信息")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
