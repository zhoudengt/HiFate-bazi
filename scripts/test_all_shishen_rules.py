#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试所有十神命格规则是否能被匹配到
通过测试大量随机日期来找出所有能被匹配的规则
"""

import requests
import json
from datetime import datetime, timedelta
import random

API_URL = "http://localhost:8001/api/v1/bazi/formula-analysis"

def test_random_dates(num_tests=100):
    """测试随机日期，收集所有匹配到的规则ID"""
    print("="*80)
    print(f"测试 {num_tests} 个随机日期")
    print("="*80)
    
    all_matched_ids = set()
    results_summary = []
    
    # 测试随机日期（1980-2010年）
    start_date = datetime(1980, 1, 1)
    end_date = datetime(2010, 12, 31)
    date_range = (end_date - start_date).days
    
    for i in range(num_tests):
        # 随机日期
        random_days = random.randint(0, date_range)
        test_date = start_date + timedelta(days=random_days)
        solar_date = test_date.strftime('%Y-%m-%d')
        
        # 随机时间
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        solar_time = f"{hour:02d}:{minute:02d}"
        
        # 随机性别
        gender = random.choice(['male', 'female'])
        
        payload = {
            'solar_date': solar_date,
            'solar_time': solar_time,
            'gender': gender,
            'rule_types': ['shishen']
        }
        
        try:
            response = requests.post(API_URL, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                data = result.get('data', {})
                matched_rules = data.get('matched_rules', {})
                shishen_ids = matched_rules.get('shishen', [])
                all_matched_ids.update(shishen_ids)
                
                if (i + 1) % 20 == 0:
                    print(f"  已测试 {i + 1}/{num_tests} 个日期，当前匹配到 {len(all_matched_ids)} 个唯一规则ID")
        except Exception as e:
            # 忽略错误，继续测试
            pass
    
    return all_matched_ids

def get_all_rule_ids():
    """获取数据库中所有十神命格规则的ID"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from server.db.mysql_connector import get_db_connection
    db = get_db_connection()
    
    rules = db.execute_query(
        "SELECT rule_code FROM bazi_rules WHERE rule_type = 'shishen' AND enabled = 1"
    )
    
    rule_ids = set()
    for rule in rules:
        rule_code = rule['rule_code']
        # 提取数字ID（与_convert_rule_service_to_formula_format中的逻辑一致）
        if rule_code.startswith('FORMULA_'):
            original_id = rule_code.replace('FORMULA_', '')
            try:
                numeric_id = int(original_id)
            except ValueError:
                parts = original_id.rsplit('_', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    numeric_id = int(parts[1])
                else:
                    continue
            rule_ids.add(numeric_id)
    
    return rule_ids

def main():
    print("="*80)
    print("十神命格规则覆盖度测试")
    print("="*80)
    
    # 1. 获取数据库中所有规则ID
    print("\n1. 获取数据库中所有十神命格规则ID...")
    all_rule_ids = get_all_rule_ids()
    print(f"   数据库中共有 {len(all_rule_ids)} 条十神命格规则")
    print(f"   规则ID范围: {min(all_rule_ids)} ~ {max(all_rule_ids)}")
    
    # 2. 测试随机日期，收集匹配到的规则
    print("\n2. 测试随机日期...")
    matched_rule_ids = test_random_dates(num_tests=200)
    
    # 3. 对比分析
    print("\n" + "="*80)
    print("分析结果")
    print("="*80)
    print(f"数据库中规则总数: {len(all_rule_ids)}")
    print(f"测试中匹配到的规则数: {len(matched_rule_ids)}")
    print(f"覆盖率: {len(matched_rule_ids) / len(all_rule_ids) * 100:.1f}%")
    
    # 找出未匹配到的规则
    unmatched_ids = all_rule_ids - matched_rule_ids
    if unmatched_ids:
        print(f"\n未匹配到的规则ID ({len(unmatched_ids)} 个):")
        for rule_id in sorted(unmatched_ids):
            print(f"  {rule_id}")
    else:
        print("\n✅ 所有规则都被匹配到了！")
    
    # 找出测试中匹配到但不在数据库中的ID（应该是常格99009）
    extra_ids = matched_rule_ids - all_rule_ids
    if extra_ids:
        print(f"\n测试中匹配到但不在数据库中的ID (可能是常格等): {sorted(extra_ids)}")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)

if __name__ == '__main__':
    main()

