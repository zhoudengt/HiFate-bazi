#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过API测试十神命格规则的覆盖情况
"""

import requests
import json

API_URL = "http://localhost:8001/api/v1/bazi/formula-analysis"

test_cases = [
    ('1990-01-15', '12:00', 'male', '测试案例1：普通日期'),
    ('1987-01-07', '09:00', 'male', '测试案例2：另一个日期'),
    ('1985-05-20', '14:30', 'female', '测试案例3：女性'),
    ('1995-11-10', '08:15', 'male', '测试案例4：另一个日期'),
    ('2000-01-01', '00:00', 'male', '测试案例5：特殊日期'),
    ('1980-06-15', '12:00', 'male', '测试案例6：夏季日期'),
    ('1975-12-25', '18:00', 'female', '测试案例7：冬季日期'),
    ('1992-03-20', '10:30', 'male', '测试案例8：春季日期'),
    ('1988-09-10', '15:45', 'female', '测试案例9：秋季日期'),
    ('2005-07-07', '08:00', 'male', '测试案例10：另一个日期'),
    # 添加更多测试案例
    ('1998-04-15', '14:20', 'male', '测试案例11'),
    ('1993-08-22', '09:30', 'female', '测试案例12'),
    ('1989-02-28', '16:45', 'male', '测试案例13'),
    ('2002-10-10', '11:15', 'female', '测试案例14'),
    ('1978-05-05', '20:00', 'male', '测试案例15'),
]

def test_case(solar_date, solar_time, gender, description):
    """测试单个案例"""
    payload = {
        'solar_date': solar_date,
        'solar_time': solar_time,
        'gender': gender,
        'rule_types': ['shishen']
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('success'):
            print(f"❌ {description}: API返回失败 - {result.get('error')}")
            return None
        
        data = result.get('data', {})
        matched_rules = data.get('matched_rules', {})
        rule_details = data.get('rule_details', {})
        statistics = data.get('statistics', {})
        
        shishen_ids = matched_rules.get('shishen', [])
        shishen_count = statistics.get('shishen_count', 0)
        
        # 获取八字信息
        bazi_info = data.get('bazi_info', {})
        bazi_pillars = bazi_info.get('bazi_pillars', {})
        day_pillar = f"{bazi_pillars.get('day', {}).get('stem', '')}{bazi_pillars.get('day', {}).get('branch', '')}"
        
        print(f"\n{description}")
        print(f"  日期: {solar_date} {solar_time}, 性别: {gender}")
        print(f"  日柱: {day_pillar}")
        print(f"  匹配数量: {shishen_count}")
        print(f"  规则ID: {shishen_ids}")
        
        # 检查是否有常格
        has_changge = 99009 in shishen_ids
        if has_changge:
            print(f"  ✅ 包含常格（默认规则）")
        
        # 显示匹配的规则名称
        for rule_id in shishen_ids[:3]:  # 只显示前3个
            detail = rule_details.get(str(rule_id), {})
            result_text = detail.get('结果', '') or detail.get('result', '')
            if result_text:
                first_line = result_text.split('\n')[0][:40]
                print(f"    [{rule_id}] {first_line}...")
        
        if len(shishen_ids) > 3:
            print(f"    ... 还有 {len(shishen_ids) - 3} 个规则")
        
        return {
            'count': shishen_count,
            'ids': shishen_ids,
            'has_changge': has_changge
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ {description}: 请求失败 - {e}")
        return None
    except Exception as e:
        print(f"❌ {description}: 处理失败 - {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("="*80)
    print("十神命格规则覆盖测试（通过API）")
    print("="*80)
    
    results = []
    for solar_date, solar_time, gender, description in test_cases:
        result = test_case(solar_date, solar_time, gender, description)
        if result:
            results.append(result)
    
    # 统计结果
    print(f"\n{'='*80}")
    print("统计结果")
    print(f"{'='*80}")
    
    if results:
        counts = [r['count'] for r in results]
        has_changge_count = sum(1 for r in results if r['has_changge'])
        unique_ids = set()
        for r in results:
            unique_ids.update(r['ids'])
        
        print(f"测试案例总数: {len(results)}")
        print(f"最多匹配数: {max(counts)}")
        print(f"最少匹配数: {min(counts)}")
        print(f"平均匹配数: {sum(counts) / len(counts):.2f}")
        print(f"触发常格默认规则的案例数: {has_changge_count}")
        print(f"匹配到的唯一规则ID总数: {len(unique_ids)}")
        print(f"\n各案例匹配数分布:")
        for i, count in enumerate(counts, 1):
            marker = " (常格)" if results[i-1]['has_changge'] else ""
            print(f"  案例{i}: {count} 个{marker}")
    
    print(f"\n{'='*80}")
    print("测试完成")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()

