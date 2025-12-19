#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查生产环境规则引擎是否正确加载规则
"""

import requests
import json

def check_production_rule_engine():
    """检查生产环境规则引擎"""
    # 测试 API
    url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    print("="*80)
    print("检查生产环境规则引擎")
    print("="*80)
    
    try:
        response = requests.post(url, json=test_case, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        rule_details = result.get('data', {}).get('rule_details', {})
        
        print(f"\n生产环境返回 {len(rule_details)} 条规则")
        print(f"\n检查规则格式:")
        
        formula_count = 0
        non_formula_count = 0
        
        for rule_id, details in rule_details.items():
            rule_code = details.get('rule_code', 'N/A')
            if rule_code.startswith('FORMULA_'):
                formula_count += 1
            else:
                non_formula_count += 1
                print(f"  ⚠️  rule_id={rule_id}, rule_code={rule_code} (不是FORMULA_格式)")
        
        print(f"\n统计:")
        print(f"  FORMULA_ 格式: {formula_count} 条")
        print(f"  非FORMULA_格式: {non_formula_count} 条")
        
        if non_formula_count > 0:
            print(f"\n🔴 问题: 生产环境返回的规则不是FORMULA_格式")
            print(f"   这说明规则可能不是从数据库加载的，或者规则转换有问题")
            print(f"\n💡 建议:")
            print(f"   1. 检查生产环境的规则引擎是否正确加载了数据库规则")
            print(f"   2. 检查 RuleService.match_rules 返回的规则格式")
            print(f"   3. 可能需要重启服务以重新加载规则引擎")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_production_rule_engine()

