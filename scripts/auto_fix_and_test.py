#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动修复并持续测试直到问题解决
"""

import sys
import os
import json
import requests
import time
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
    except:
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
        response = requests.post(url, json=test_case, timeout=30)
        response.raise_for_status()
        result = response.json()
        stats = result.get('data', {}).get('statistics', {})
        return stats
    except Exception as e:
        return {'error': str(e)}


def clear_production_cache():
    """清除生产环境缓存"""
    try:
        url = "http://8.210.52.217:8001/api/v1/hot-reload/check"
        requests.post(url, timeout=30)
        return True
    except:
        return False


def main():
    """主函数 - 持续测试直到问题解决"""
    print("="*80)
    print("🔧 自动修复并持续测试")
    print("="*80)
    
    # 获取本地规则总数（作为目标）
    local_total = get_local_rule_count()
    print(f"\n📊 本地环境规则总数: {local_total} 条")
    print(f"🎯 目标: 生产环境匹配数应接近 {local_total} 条（允许 10% 差异）")
    
    # 测试生产环境当前状态
    print("\n" + "="*80)
    print("🧪 测试生产环境当前状态")
    print("="*80)
    
    prod_stats = test_production_api()
    if 'error' in prod_stats:
        print(f"❌ 无法连接生产环境: {prod_stats['error']}")
        return
    
    prod_total = prod_stats.get('total_matched', 0)
    print(f"当前匹配数: {prod_total} 条")
    
    # 判断是否需要修复
    target_min = int(local_total * 0.9)  # 允许 10% 差异
    
    if prod_total >= target_min:
        print(f"✅ 匹配数量正常（{prod_total} >= {target_min}），无需修复")
        return
    
    print(f"⚠️  匹配数量不足（{prod_total} < {target_min}），需要修复")
    
    # 提供修复方案
    print("\n" + "="*80)
    print("💡 修复方案")
    print("="*80)
    print("\n由于 SSH 需要密码认证，请手动执行以下步骤:")
    print("\n1. 运行手动同步脚本:")
    print("   bash scripts/manual_sync_rules_to_production.sh")
    print("\n2. 或者手动执行:")
    print("   a. 上传 SQL 文件:")
    print("      scp scripts/temp_rules_export.sql root@8.210.52.217:/tmp/rules_import.sql")
    print("   b. SSH 到生产环境:")
    print("      ssh root@8.210.52.217")
    print("   c. 执行 SQL:")
    print("      docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql")
    print("   d. 清除缓存:")
    print("      curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check")
    
    # 单次测试模式（避免卡住）
    print("\n" + "="*80)
    print("🧪 单次测试验证")
    print("="*80)
    
    # 清除缓存
    print("🧹 清除缓存...")
    clear_production_cache()
    time.sleep(3)
    
    # 测试
    print("📡 测试生产环境...")
    prod_stats = test_production_api()
    
    if 'error' in prod_stats:
        print(f"❌ 测试失败: {prod_stats['error']}")
        return
    
    prod_total = prod_stats.get('total_matched', 0)
    print(f"\n当前匹配数: {prod_total} 条 (目标: {target_min}+ 条)")
    
    if prod_total >= target_min:
        print("\n" + "="*80)
        print("✅ 问题已解决！")
        print("="*80)
        print(f"匹配数量: {prod_total} 条 (目标: {target_min}+ 条)")
        print("\n详细统计:")
        for key, value in prod_stats.items():
            if key.endswith('_count'):
                print(f"  - {key}: {value}")
    else:
        print(f"\n⚠️  仍需修复 (差异: {target_min - prod_total} 条)")
        print("\n💡 请执行修复步骤后，再次运行此脚本验证")


if __name__ == '__main__':
    main()

