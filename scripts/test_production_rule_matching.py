#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试生产环境规则匹配逻辑
"""

import requests
import json

def test_production_api():
    """测试生产环境 API"""
    url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
    
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    print("="*80)
    print("测试生产环境规则匹配")
    print("="*80)
    print(f"\n测试用例: {json.dumps(test_case, ensure_ascii=False, indent=2)}")
    print(f"\n调用 API: {url}")
    
    try:
        response = requests.post(url, json=test_case, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        print(f"\n✅ API 调用成功")
        print(f"\n响应数据:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 分析结果
        matched_rules = result.get('data', {}).get('matched_rules', {})
        rule_details = result.get('data', {}).get('rule_details', {})
        
        print(f"\n📊 匹配结果统计:")
        print(f"  总匹配数: {sum(matched_rules.values())}")
        print(f"  规则详情数: {len(rule_details)}")
        
        print(f"\n按类型统计:")
        for rule_type, count in matched_rules.items():
            print(f"  {rule_type}: {count} 条")
        
        # 检查规则详情
        if rule_details:
            print(f"\n规则详情示例（前3条）:")
            for i, (rule_id, details) in enumerate(list(rule_details.items())[:3], 1):
                print(f"\n  {i}. 规则ID: {rule_id}")
                print(f"     类型: {details.get('类型', 'N/A')}")
                print(f"     rule_code: {details.get('rule_code', 'N/A')}")
                print(f"     条件: {details.get('筛选条件1', 'N/A')}")
        
    except Exception as e:
        print(f"\n❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_production_api()

