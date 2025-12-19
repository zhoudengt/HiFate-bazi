#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试生产环境并显示结果（不卡住）
"""

import sys
import os
import json
import requests
from typing import Dict

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
import pymysql.cursors


def get_local_rule_count() -> int:
    """获取本地规则总数"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%' 
              AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
              AND enabled = 1
        """)
        result = cursor.fetchone()
        cursor.close()
        return_mysql_connection(conn)
        return result['total'] if result else 0
    except Exception as e:
        print(f"⚠️  获取本地规则数失败: {e}")
        return 0


def test_production_api() -> Dict:
    """测试生产环境 API"""
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    try:
        url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
        response = requests.post(url, json=test_case, timeout=10)
        response.raise_for_status()
        result = response.json()
        stats = result.get('data', {}).get('statistics', {})
        return {'success': True, 'stats': stats}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def main():
    """主函数"""
    print("="*80)
    print("🧪 快速测试生产环境")
    print("="*80)
    
    # 获取本地规则总数
    local_total = get_local_rule_count()
    print(f"\n📊 本地环境规则总数: {local_total} 条")
    
    # 测试生产环境
    print("\n📡 测试生产环境 API...")
    result = test_production_api()
    
    if not result['success']:
        print(f"❌ 测试失败: {result['error']}")
        return
    
    stats = result['stats']
    prod_total = stats.get('total_matched', 0)
    
    print(f"\n✅ 生产环境匹配结果:")
    print(f"  总匹配数: {prod_total} 条")
    print(f"  财富: {stats.get('wealth_count', 0)}")
    print(f"  婚姻: {stats.get('marriage_count', 0)}")
    print(f"  事业: {stats.get('career_count', 0)} ⚠️")
    print(f"  身体: {stats.get('health_count', 0)}")
    print(f"  总评: {stats.get('summary_count', 0)}")
    
    # 判断是否需要修复
    target_min = int(local_total * 0.9)
    
    print(f"\n📊 对比分析:")
    print(f"  本地规则数: {local_total} 条")
    print(f"  生产匹配数: {prod_total} 条")
    print(f"  目标最低: {target_min} 条")
    
    if prod_total >= target_min:
        print(f"\n✅ 匹配数量正常，无需修复")
    else:
        print(f"\n⚠️  匹配数量不足，需要修复")
        print(f"   差异: {target_min - prod_total} 条")
        print(f"\n💡 修复步骤:")
        print(f"   1. 运行: bash scripts/manual_sync_rules_to_production.sh")
        print(f"   2. 或手动执行 SQL 同步（见脚本内容）")


if __name__ == '__main__':
    main()

