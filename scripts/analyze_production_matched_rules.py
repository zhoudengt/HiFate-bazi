#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析生产环境匹配到的规则，找出为什么其他规则没有匹配
"""

import requests
import json

def analyze_production_rules():
    """分析生产环境匹配的规则"""
    url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
    
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    print("="*80)
    print("分析生产环境匹配的规则")
    print("="*80)
    
    try:
        response = requests.post(url, json=test_case, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        matched_rules = result.get('data', {}).get('matched_rules', {})
        rule_details = result.get('data', {}).get('rule_details', {})
        
        print(f"\n生产环境匹配到 {len(rule_details)} 条规则")
        print(f"\n按类型统计:")
        for rule_type, count in sorted(matched_rules.items()):
            print(f"  {rule_type}: {count} 条")
        
        print(f"\n匹配的规则详情:")
        for i, (rule_id, details) in enumerate(rule_details.items(), 1):
            print(f"\n  {i}. rule_id: {rule_id}")
            print(f"     rule_code: {details.get('rule_code', 'N/A')}")
            print(f"     类型: {details.get('类型', 'N/A')}")
            print(f"     筛选条件1: {details.get('筛选条件1', 'N/A')}")
            print(f"     筛选条件2: {details.get('筛选条件2', 'N/A')}")
        
        # 检查是否有 career 类型的规则
        career_rules = [r for r in rule_details.values() if r.get('类型') == '事业']
        print(f"\n事业类型规则: {len(career_rules)} 条")
        if not career_rules:
            print("  ⚠️  没有匹配到事业类型规则，这可能是问题所在")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    analyze_production_rules()

