#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试十神命格规则的覆盖情况
- 测试不同八字能匹配到多少个十神命格规则
- 找出最多和最少匹配数
- 验证常格默认规则是否生效
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.services.bazi_service import BaziService
from server.services.rule_service import RuleService
from server.utils.data_validator import validate_bazi_data
from server.api.v1.formula_analysis import _convert_rule_service_to_formula_format

def test_shishen_matching(solar_date, solar_time, gender, description):
    """测试指定八字的十神命格匹配情况"""
    print(f"\n{'='*80}")
    print(f"测试案例: {description}")
    print(f"  日期: {solar_date} {solar_time}, 性别: {gender}")
    print(f"{'='*80}")
    
    # 1. 计算八字
    bazi_result = BaziService.calculate_bazi_full(
        solar_date=solar_date,
        solar_time=solar_time,
        gender=gender
    )
    
    if not bazi_result or not isinstance(bazi_result, dict):
        print("❌ 八字计算失败")
        return None
    
    bazi_data = bazi_result.get('bazi', {})
    if not bazi_data:
        print("❌ 八字数据为空")
        return None
    
    # 显示八字信息
    pillars = bazi_data.get('bazi_pillars', {})
    day_pillar = f"{pillars.get('day', {}).get('stem', '')}{pillars.get('day', {}).get('branch', '')}"
    print(f"  日柱: {day_pillar}")
    
    # 2. 构建规则匹配数据（验证类型）
    rule_data = {
        'basic_info': bazi_data.get('basic_info', {}),
        'bazi_pillars': bazi_data.get('bazi_pillars', {}),
        'details': bazi_data.get('details', {}),
        'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
        'elements': bazi_data.get('elements', {}),
        'element_counts': bazi_data.get('element_counts', {}),
        'relationships': bazi_data.get('relationships', {})
    }
    rule_data = validate_bazi_data(rule_data)
    
    # 3. 匹配规则
    matched_rules_raw = RuleService.match_rules(rule_data, rule_types=['shishen'], use_cache=True)
    
    # 4. 转换为前端格式（这里会添加常格默认规则）
    result = _convert_rule_service_to_formula_format(matched_rules_raw, rule_types=['shishen'])
    
    matched_shishen_ids = result['matched_rules'].get('shishen', [])
    rule_details = result['rule_details']
    
    print(f"  匹配到的十神命格数量: {len(matched_shishen_ids)}")
    print(f"  匹配到的规则ID: {matched_shishen_ids}")
    
    # 显示匹配到的规则详情
    for rule_id in matched_shishen_ids:
        detail = rule_details.get(rule_id, {})
        rule_name = detail.get('结果', '')[:50] if detail.get('结果') else 'N/A'
        if '常格' in rule_name:
            print(f"    [{rule_id}] 常格 (默认规则)")
        else:
            print(f"    [{rule_id}] {rule_name[:50]}...")
    
    return {
        'count': len(matched_shishen_ids),
        'ids': matched_shishen_ids,
        'has_changge': 99009 in matched_shishen_ids
    }


def main():
    """主测试函数"""
    print("="*80)
    print("十神命格规则覆盖测试")
    print("="*80)
    
    test_cases = [
        # 测试一些常见的日期
        ('1990-01-15', '12:00', 'male', '测试案例1：普通日期'),
        ('1987-01-07', '09:00', 'male', '测试案例2：另一个日期'),
        ('1985-05-20', '14:30', 'female', '测试案例3：女性'),
        ('1995-11-10', '08:15', 'male', '测试案例4：另一个日期'),
        
        # 测试一些特殊的日期组合（可能匹配多个规则）
        ('2000-01-01', '00:00', 'male', '测试案例5：特殊日期'),
        ('1980-06-15', '12:00', 'male', '测试案例6：夏季日期'),
        ('1975-12-25', '18:00', 'female', '测试案例7：冬季日期'),
        
        # 测试更多随机日期
        ('1992-03-20', '10:30', 'male', '测试案例8：春季日期'),
        ('1988-09-10', '15:45', 'female', '测试案例9：秋季日期'),
        ('2005-07-07', '08:00', 'male', '测试案例10：另一个日期'),
    ]
    
    results = []
    for solar_date, solar_time, gender, description in test_cases:
        try:
            result = test_shishen_matching(solar_date, solar_time, gender, description)
            if result:
                results.append(result)
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 统计结果
    print(f"\n{'='*80}")
    print("统计结果")
    print(f"{'='*80}")
    
    if results:
        counts = [r['count'] for r in results]
        has_changge_count = sum(1 for r in results if r['has_changge'])
        
        print(f"测试案例总数: {len(results)}")
        print(f"最多匹配数: {max(counts)}")
        print(f"最少匹配数: {min(counts)}")
        print(f"平均匹配数: {sum(counts) / len(counts):.2f}")
        print(f"触发常格默认规则的案例数: {has_changge_count}")
        print(f"\n各案例匹配数分布:")
        for i, count in enumerate(counts, 1):
            print(f"  案例{i}: {count} 个")
    
    print(f"\n{'='*80}")
    print("测试完成")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()

