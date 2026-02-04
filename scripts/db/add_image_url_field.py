#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加 image_url 字段到 homepage_contents 表

使用方法:
    python3 scripts/db/add_image_url_field.py
"""

import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from shared.config.database import get_mysql_connection, return_mysql_connection


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    """检查字段是否存在"""
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM information_schema.columns 
        WHERE table_schema = DATABASE() 
        AND table_name = %s 
        AND column_name = %s
    """, (table_name, column_name))
    result = cursor.fetchone()
    if isinstance(result, dict):
        return result.get('count', 0) > 0
    else:
        return result[0] > 0 if result else False


def table_exists(cursor, table_name: str) -> bool:
    """检查表是否存在"""
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() AND table_name = %s
    """, (table_name,))
    result = cursor.fetchone()
    if isinstance(result, dict):
        return result.get('count', 0) > 0
    else:
        return result[0] > 0 if result else False


def add_image_url_field():
    """添加 image_url 字段"""
    print("=" * 60)
    print("添加 image_url 字段到 homepage_contents 表")
    print("=" * 60)
    
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ 无法连接数据库")
            return False
        
        db_name = conn.db.decode() if isinstance(conn.db, bytes) else conn.db
        print(f"✅ 数据库连接成功")
        print(f"   数据库: {db_name}")
        print(f"   主机: {conn.host}:{conn.port}")
        print()
        
        with conn.cursor() as cursor:
            # 检查表是否存在
            if not table_exists(cursor, 'homepage_contents'):
                print("❌ 表 homepage_contents 不存在")
                print("   请先运行: python3 scripts/db/migrate_homepage_contents.py")
                return False
            
            print("✅ 表 homepage_contents 存在")
            
            # 检查字段是否已存在
            if column_exists(cursor, 'homepage_contents', 'image_url'):
                print("✅ 字段 image_url 已存在，无需添加")
                
                # 显示当前字段信息
                cursor.execute("DESCRIBE `homepage_contents`")
                columns = cursor.fetchall()
                print("\n当前表结构:")
                print("-" * 60)
                for col in columns:
                    field = col.get('Field', '')
                    type_ = col.get('Type', '')
                    null = col.get('Null', '')
                    if field in ['image_url', 'image_base64']:
                        print(f"  {field:<20} {type_:<20} {null}")
                return True
            
            print("📝 添加字段 image_url...")
            
            # 添加字段
            sql = """
                ALTER TABLE `homepage_contents` 
                ADD COLUMN `image_url` VARCHAR(500) NULL 
                COMMENT '图片OSS地址（如：https://destiny-ducket.oss-cn-hongkong.aliyuncs.com/xxx.jpeg）' 
                AFTER `description`
            """
            
            cursor.execute(sql)
            conn.commit()
            
            print("✅ 字段 image_url 添加成功")
            
            # 验证字段
            if column_exists(cursor, 'homepage_contents', 'image_url'):
                print("✅ 字段验证通过")
                
                # 显示更新后的字段信息
                cursor.execute("DESCRIBE `homepage_contents`")
                columns = cursor.fetchall()
                print("\n更新后的表结构（图片相关字段）:")
                print("-" * 60)
                for col in columns:
                    field = col.get('Field', '')
                    type_ = col.get('Type', '')
                    null = col.get('Null', '')
                    key = col.get('Key', '')
                    default = col.get('Default', '')
                    extra = col.get('Extra', '')
                    comment = col.get('Comment', '')
                    if field in ['image_url', 'image_base64']:
                        print(f"  {field:<20} {type_:<20} {null:<6} {key:<8} {default or 'NULL':<15} {extra:<10} {comment}")
                
                return True
            else:
                print("❌ 字段验证失败")
                return False
            
    except Exception as e:
        error_msg = str(e)
        if 'Duplicate column name' in error_msg or '1060' in error_msg:
            print("✅ 字段 image_url 已存在（可能由其他进程添加）")
            return True
        else:
            print(f"❌ 添加字段失败: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.rollback()
            return False
    finally:
        if conn:
            return_mysql_connection(conn)


if __name__ == '__main__':
    success = add_image_url_field()
    
    if success:
        print()
        print("=" * 60)
        print("✅ 迁移成功完成！")
        print("=" * 60)
        print("\n下一步:")
        print("1. 代码已更新为使用 image_url 字段")
        print("2. 新数据将使用 image_url 存储OSS地址")
        print("3. image_base64 字段保留用于过渡（可选删除）")
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ 迁移失败，请检查错误信息")
        print("=" * 60)
        sys.exit(1)
