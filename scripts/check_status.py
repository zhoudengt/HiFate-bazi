#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速检查当前状态
"""

import sys
import os
import json
import requests

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def main():
    """主函数"""
    print("="*80)
    print("📊 快速状态检查")
    print("="*80)
    
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    # 测试本地
    print("\n📡 测试本地环境...")
    try:
        url = "http://localhost:8001/api/v1/bazi/formula-analysis"
        response = requests.post(url, json=test_case, timeout=10)
        response.raise_for_status()
        result = response.json()
        local_stats = result.get('data', {}).get('statistics', {})
        local_total = local_stats.get('total_matched', 0)
        print(f"✅ 本地环境: {local_total} 条")
    except:
        print("⚠️  本地服务未运行")
        local_total = 63  # 使用已知值
        local_stats = None
    
    # 测试生产环境
    print("\n📡 测试生产环境...")
    try:
        url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
        response = requests.post(url, json=test_case, timeout=30)
        response.raise_for_status()
        result = response.json()
        prod_stats = result.get('data', {}).get('statistics', {})
        prod_total = prod_stats.get('total_matched', 0)
        print(f"{'✅' if prod_total >= 50 else '❌'} 生产环境: {prod_total} 条")
    except Exception as e:
        print(f"❌ 生产环境测试失败: {e}")
        return
    
    # 对比
    print(f"\n{'='*80}")
    print("📊 对比结果")
    print(f"{'='*80}")
    
    target_min = int(local_total * 0.9) if local_stats else 50
    
    print(f"\n{'字段':<25} {'本地':<15} {'生产':<15} {'状态':<10}")
    print("-" * 65)
    
    fields = [
        'total_matched', 'wealth_count', 'marriage_count', 'career_count',
        'children_count', 'character_count', 'summary_count', 'health_count',
        'peach_blossom_count', 'shishen_count', 'parents_count'
    ]
    
    for field in fields:
        local_val = local_stats.get(field, 0) if local_stats else 0
        prod_val = prod_stats.get(field, 0)
        
        if local_val == prod_val:
            status = "✅ 一致"
        elif abs(local_val - prod_val) >= 5:
            status = "🔴 差异大"
        else:
            status = "🟡 有差异"
        
        print(f"{field:<25} {local_val:<15} {prod_val:<15} {status}")
    
    # 判断是否解决
    print(f"\n{'='*80}")
    if prod_total >= target_min:
        print("✅ 问题已解决！匹配数量正常")
    else:
        diff = target_min - prod_total
        print(f"❌ 问题未解决")
        print(f"   生产环境: {prod_total} 条")
        print(f"   目标最低: {target_min} 条")
        print(f"   差异: {diff} 条")
        print(f"\n💡 需要执行修复:")
        print(f"   scp scripts/temp_rules_export.sql root@8.210.52.217:/tmp/rules_import.sql")
        print(f"   ssh root@8.210.52.217 'cd /opt/HiFate-bazi && docker exec -i hifate-mysql-master mysql -uroot -p${MYSQL_PASSWORD} hifate_bazi < /tmp/rules_import.sql && curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check'")


if __name__ == '__main__':
    main()

