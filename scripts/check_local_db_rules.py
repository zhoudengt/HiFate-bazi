#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查本地数据库规则数量
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
import pymysql.cursors


def main():
    """主函数"""
    print("="*60)
    print("🔍 检查本地数据库规则")
    print("="*60)
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 1. 总规则数
        cursor.execute("SELECT COUNT(*) as count FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%'")
        total = cursor.fetchone()['count']
        
        # 2. 启用规则数
        cursor.execute("SELECT COUNT(*) as count FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%' AND enabled = 1")
        enabled = cursor.fetchone()['count']
        
        # 3. 按类型统计
        cursor.execute("""
            SELECT 
                rule_type,
                COUNT(*) as total,
                SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count,
                SUM(CASE WHEN enabled = 0 THEN 1 ELSE 0 END) as disabled_count
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%'
            GROUP BY rule_type
            ORDER BY rule_type
        """)
        type_stats = cursor.fetchall()
        
        print(f"\n📊 规则统计:")
        print(f"  总规则数: {total}")
        print(f"  启用规则数: {enabled}")
        print(f"  禁用规则数: {total - enabled}")
        
        print(f"\n📋 按类型统计:")
        print(f"{'类型':<20} {'总数':<10} {'启用':<10} {'禁用':<10}")
        print("-" * 50)
        for stat in type_stats:
            print(f"{stat['rule_type']:<20} {stat['total']:<10} {stat['enabled_count']:<10} {stat['disabled_count']:<10}")
        
        cursor.close()
        return_mysql_connection(conn)
        
        print(f"\n💡 下一步:")
        print(f"  1. 手动 SSH 到生产环境检查:")
        print(f"     ssh root@8.210.52.217")
        print(f"  2. 运行以下 SQL 查询:")
        print(f"     docker exec hifate-mysql-master mysql -uroot -p${MYSQL_PASSWORD} hifate_bazi -e \\")
        print(f"       \"SELECT rule_type, COUNT(*) as total, SUM(enabled) as enabled_count \\")
        print(f"        FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%' GROUP BY rule_type;\"")
        print(f"  3. 对比本地和生产环境的规则数量")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

