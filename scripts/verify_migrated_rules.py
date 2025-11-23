#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证迁移后的规则
1. 检查数据库中的规则
2. 测试规则匹配
3. 对比FormulaRuleService和RuleService的匹配结果
"""

import json
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def check_database_rules():
    """检查数据库中的迁移规则"""
    try:
        from server.db.mysql_connector import get_db_connection
        
        db = get_db_connection()
        
        # 查询迁移的规则
        sql = """
            SELECT rule_code, rule_name, rule_type, conditions, content, enabled
            FROM bazi_rules
            WHERE rule_code LIKE 'FORMULA_%'
            ORDER BY rule_type, rule_code
            LIMIT 20
        """
        
        rules = db.execute_query(sql)
        
        print("=" * 60)
        print("数据库中的迁移规则（前20条）")
        print("=" * 60)
        
        for rule in rules:
            print(f"\n规则代码: {rule['rule_code']}")
            print(f"规则名称: {rule['rule_name']}")
            print(f"规则类型: {rule['rule_type']}")
            print(f"是否启用: {rule['enabled']}")
            
            # 解析条件
            conditions = rule['conditions']
            if isinstance(conditions, str):
                conditions = json.loads(conditions)
            print(f"条件: {json.dumps(conditions, ensure_ascii=False, indent=2)}")
            
            # 解析内容
            content = rule['content']
            if isinstance(content, str):
                content = json.loads(content)
            print(f"内容: {content.get('text', '')[:50]}...")
        
        # 统计
        count_sql = """
            SELECT rule_type, COUNT(*) as count
            FROM bazi_rules
            WHERE rule_code LIKE 'FORMULA_%'
            GROUP BY rule_type
        """
        stats = db.execute_query(count_sql)
        
        print("\n" + "=" * 60)
        print("规则统计")
        print("=" * 60)
        for stat in stats:
            print(f"{stat['rule_type']}: {stat['count']} 条")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule_matching():
    """测试规则匹配"""
    try:
        from server.services.rule_service import RuleService
        from server.services.bazi_service import BaziService
        
        # 测试用例：1990-05-15 14:30 男
        print("\n" + "=" * 60)
        print("测试规则匹配")
        print("=" * 60)
        
        solar_date = "1990-05-15"
        solar_time = "14:30"
        gender = "male"
        
        # 计算八字
        bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
        bazi_data = bazi_result.get('bazi', {})
        
        # 构建规则匹配数据
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': bazi_data.get('element_counts', {}),
            'relationships': bazi_data.get('relationships', {})
        }
        
        # 匹配规则（只匹配迁移的规则）
        matched_rules = RuleService.match_rules(rule_data, rule_types=['wealth', 'marriage'], use_cache=False)
        
        # 筛选迁移的规则
        migrated_rules = [r for r in matched_rules if r.get('rule_id', '').startswith('FORMULA_')]
        
        print(f"\n匹配到的迁移规则: {len(migrated_rules)} 条")
        for rule in migrated_rules[:10]:  # 只显示前10条
            print(f"\n规则ID: {rule.get('rule_id')}")
            print(f"规则类型: {rule.get('rule_type')}")
            print(f"规则名称: {rule.get('rule_name', '')[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试规则匹配失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_with_formula_service():
    """对比FormulaRuleService和RuleService的匹配结果"""
    try:
        from server.services.formula_rule_service import FormulaRuleService
        from server.services.rule_service import RuleService
        from server.services.bazi_service import BaziService
        
        print("\n" + "=" * 60)
        print("对比FormulaRuleService和RuleService的匹配结果")
        print("=" * 60)
        
        # 测试用例
        solar_date = "1990-05-15"
        solar_time = "14:30"
        gender = "male"
        
        # 计算八字
        bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
        bazi_data = bazi_result.get('bazi', {})
        
        # FormulaRuleService匹配
        formula_result = FormulaRuleService.match_rules(bazi_data, rule_types=['wealth'])
        formula_matched = formula_result.get('matched_rules', {}).get('wealth', [])
        
        # RuleService匹配
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': bazi_data.get('element_counts', {}),
            'relationships': bazi_data.get('relationships', {})
        }
        rule_matched = RuleService.match_rules(rule_data, rule_types=['wealth'], use_cache=False)
        rule_migrated = [r for r in rule_matched if r.get('rule_id', '').startswith('FORMULA_')]
        
        print(f"\nFormulaRuleService匹配: {len(formula_matched)} 条财富规则")
        print(f"RuleService匹配（迁移规则）: {len(rule_migrated)} 条财富规则")
        
        # 对比规则ID
        formula_ids = set([str(rid) for rid in formula_matched])
        rule_ids = set([r.get('rule_id', '').replace('FORMULA_', '') for r in rule_migrated])
        
        print(f"\nFormulaRuleService规则ID: {sorted(formula_ids)[:10]}...")
        print(f"RuleService规则ID: {sorted(rule_ids)[:10]}...")
        
        # 计算交集
        common = formula_ids & rule_ids
        only_formula = formula_ids - rule_ids
        only_rule = rule_ids - formula_ids
        
        print(f"\n共同匹配: {len(common)} 条")
        print(f"仅FormulaRuleService匹配: {len(only_formula)} 条")
        print(f"仅RuleService匹配: {len(only_rule)} 条")
        
        if only_formula:
            print(f"\n仅FormulaRuleService匹配的规则ID: {sorted(only_formula)[:10]}")
        if only_rule:
            print(f"\n仅RuleService匹配的规则ID: {sorted(only_rule)[:10]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 对比失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("验证迁移后的规则")
    print("=" * 60)
    
    # 1. 检查数据库
    check_db = check_database_rules()
    
    if check_db:
        # 2. 测试规则匹配
        test_match = test_rule_matching()
        
        # 3. 对比两个服务
        compare = compare_with_formula_service()
        
        print("\n" + "=" * 60)
        print("验证完成")
        print("=" * 60)
        print(f"数据库检查: {'✓' if check_db else '✗'}")
        print(f"规则匹配测试: {'✓' if test_match else '✗'}")
        print(f"服务对比: {'✓' if compare else '✗'}")
    else:
        print("\n⚠️  数据库检查失败，跳过后续测试")

