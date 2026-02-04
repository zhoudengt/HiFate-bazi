#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断日元-六十甲子数据问题
"""

import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from shared.config.database import get_mysql_connection, return_mysql_connection
from server.services.rizhu_liujiazi_service import RizhuLiujiaziService


def diagnose():
    """诊断数据问题"""
    print("=" * 60)
    print("诊断日元-六十甲子数据问题")
    print("=" * 60)
    
    # 1. 检查表是否存在
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ 无法连接数据库")
            return
        
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'rizhu_liujiazi'")
            if not cursor.fetchone():
                print("❌ 表 rizhu_liujiazi 不存在")
                print("   请先运行: python3 scripts/migration/create_rizhu_liujiazi_table.py")
                return
            else:
                print("✅ 表 rizhu_liujiazi 存在")
        
        # 2. 检查总记录数
        total_count = RizhuLiujiaziService.get_total_count()
        print(f"\n📊 数据库统计:")
        print(f"   总记录数: {total_count}")
        
        if total_count == 0:
            print("\n⚠️  表中没有数据！")
            print("   请运行数据导入脚本: python3 scripts/migration/import_rizhu_liujiazi.py")
            return
        
        # 3. 检查启用状态的记录数
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM rizhu_liujiazi WHERE enabled = 1")
            enabled_result = cursor.fetchone()
            enabled_count = enabled_result.get('count', 0) if isinstance(enabled_result, dict) else (enabled_result[0] if isinstance(enabled_result, tuple) else 0)
            print(f"   启用状态记录数: {enabled_count}")
        
        # 4. 测试查询"庚辰"
        print(f"\n🔍 测试查询:")
        test_rizhu = "庚辰"
        result = RizhuLiujiaziService.get_rizhu_analysis(test_rizhu)
        if result:
            print(f"   ✅ 查询'{test_rizhu}'成功: id={result.get('id')}, rizhu={result.get('rizhu')}")
            print(f"   解析内容长度: {len(result.get('analysis', ''))} 字符")
        else:
            print(f"   ❌ 查询'{test_rizhu}'失败")
            
            # 检查是否有这个日柱（不管enabled状态）
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, rizhu, enabled FROM rizhu_liujiazi WHERE rizhu = %s", (test_rizhu,))
                row = cursor.fetchone()
                if row:
                    enabled_val = row.get('enabled') if isinstance(row, dict) else row[3] if isinstance(row, tuple) and len(row) > 3 else None
                    print(f"   ⚠️  数据库中存在该日柱，但enabled状态: {enabled_val}")
                else:
                    print(f"   ⚠️  数据库中不存在该日柱")
        
        # 5. 列出所有日柱
        print(f"\n📋 所有日柱列表（前20个）:")
        all_rizhu = RizhuLiujiaziService.get_all_rizhu_list()
        for i, item in enumerate(all_rizhu[:20], 1):
            print(f"   {i}. ID={item.get('id')}, 日柱={item.get('rizhu')}, 启用={item.get('enabled')}")
        
        if len(all_rizhu) > 20:
            print(f"   ... 还有 {len(all_rizhu) - 20} 个日柱")
            
    except Exception as e:
        print(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            return_mysql_connection(conn)


if __name__ == '__main__':
    diagnose()

