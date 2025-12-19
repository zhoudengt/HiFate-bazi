#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面诊断：对比数据库、逻辑代码、前端展示
"""

import sys
import os
import json
import requests
from typing import Dict, List, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 禁用虚拟环境检测（脚本执行时不需要）
os.environ['SKIP_VENV_CHECK'] = '1'

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
import pymysql.cursors


def check_local_database() -> Dict:
    """检查本地数据库规则"""
    print("\n" + "="*80)
    print("📊 步骤 1: 检查本地数据库规则")
    print("="*80)
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 1. 总规则数
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%' 
              AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
        """)
        total = cursor.fetchone()['total']
        
        # 2. 启用规则数
        cursor.execute("""
            SELECT COUNT(*) as enabled_count
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%' 
              AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
              AND enabled = 1
        """)
        enabled = cursor.fetchone()['enabled_count']
        
        # 3. 按类型统计
        cursor.execute("""
            SELECT 
                rule_type,
                COUNT(*) as total,
                SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%' 
              AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
            GROUP BY rule_type
            ORDER BY rule_type
        """)
        type_stats = cursor.fetchall()
        
        # 4. 测试特定八字匹配的规则（1987-01-07 09:00 男）
        # 临时禁用虚拟环境检测
        import sys
        original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        try:
            from server.services.bazi_service import BaziService
            from server.services.rule_service import RuleService
        finally:
            sys.stderr.close()
            sys.stderr = original_stderr
        
        bazi_result = BaziService.calculate_bazi_full(
            solar_date="1987-01-07",
            solar_time="09:00",
            gender="male"
        )
        bazi_data = bazi_result.get('bazi', {})
        
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': bazi_data.get('element_counts', {}),
            'relationships': bazi_data.get('relationships', {})
        }
        
        rule_types = ['wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents']
        matched_rules = RuleService.match_rules(rule_data, rule_types=rule_types, use_cache=False)
        formula_rules = [r for r in matched_rules if r.get('rule_id', '').startswith('FORMULA_')]
        
        matched_by_type = {}
        for rule in formula_rules:
            rule_type = rule.get('rule_type', '')
            if rule_type not in matched_by_type:
                matched_by_type[rule_type] = 0
            matched_by_type[rule_type] += 1
        
        result = {
            'total': total,
            'enabled': enabled,
            'type_stats': {stat['rule_type']: {'total': stat['total'], 'enabled': stat['enabled_count']} for stat in type_stats},
            'matched_count': len(formula_rules),
            'matched_by_type': matched_by_type
        }
        
        print(f"\n✅ 本地数据库统计:")
        print(f"  总规则数: {total}")
        print(f"  启用规则数: {enabled}")
        print(f"\n按类型统计:")
        for stat in type_stats:
            print(f"  - {stat['rule_type']}: {stat['enabled_count']} 条启用 (总计 {stat['total']} 条)")
        
        print(f"\n🎯 测试八字 (1987-01-07 09:00 男) 匹配结果:")
        print(f"  总匹配数: {len(formula_rules)} 条")
        for rule_type, count in sorted(matched_by_type.items()):
            print(f"  - {rule_type}: {count} 条")
        
        cursor.close()
        return_mysql_connection(conn)
        
        return result
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def check_production_database() -> Dict:
    """检查生产环境数据库规则（通过 API 间接检查）"""
    print("\n" + "="*80)
    print("📊 步骤 2: 检查生产环境（通过 API）")
    print("="*80)
    
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
        matched_rules = result.get('data', {}).get('matched_rules', {})
        
        # 统计各类型规则数量
        rule_counts = {}
        for rule_type, rule_ids in matched_rules.items():
            rule_counts[rule_type] = len(rule_ids) if isinstance(rule_ids, list) else 0
        
        print(f"\n✅ 生产环境 API 返回:")
        print(f"  总匹配数: {stats.get('total_matched', 0)} 条")
        for rule_type, count in sorted(rule_counts.items()):
            print(f"  - {rule_type}: {count} 条")
        
        return {
            'stats': stats,
            'rule_counts': rule_counts,
            'raw_response': result
        }
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return {}


def compare_database_and_logic() -> Dict:
    """对比数据库和逻辑代码"""
    print("\n" + "="*80)
    print("🔍 步骤 3: 对比数据库和逻辑代码")
    print("="*80)
    
    # 检查关键代码文件
    key_files = [
        'server/api/v1/formula_analysis.py',
        'server/services/rule_service.py',
        'server/engines/rule_engine.py'
    ]
    
    print("\n📝 检查关键代码文件:")
    for file_path in key_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - 文件不存在")
    
    # 检查规则匹配逻辑
    print("\n🔍 检查规则匹配逻辑:")
    
    # 1. 检查是否使用 RuleService
    formula_analysis_path = os.path.join(project_root, 'server/api/v1/formula_analysis.py')
    if os.path.exists(formula_analysis_path):
        with open(formula_analysis_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'RuleService.match_rules' in content:
                print("  ✅ 使用 RuleService.match_rules")
            else:
                print("  ❌ 未使用 RuleService.match_rules")
            
            if 'FORMULA_' in content:
                print("  ✅ 筛选 FORMULA_ 前缀规则")
            else:
                print("  ⚠️  未筛选 FORMULA_ 前缀规则")
    
    # 2. 检查规则类型过滤
    rule_service_path = os.path.join(project_root, 'server/services/rule_service.py')
    if os.path.exists(rule_service_path):
        with open(rule_service_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'enabled = 1' in content or 'enabled = True' in content:
                print("  ✅ 过滤 enabled 规则")
            else:
                print("  ⚠️  未明确过滤 enabled 规则")
    
    return {}


def check_frontend_display() -> Dict:
    """检查前端展示逻辑"""
    print("\n" + "="*80)
    print("🖥️  步骤 4: 检查前端展示逻辑")
    print("="*80)
    
    # 检查前端文件
    frontend_file = os.path.join(project_root, 'local_frontend/formula-analysis.html')
    
    if os.path.exists(frontend_file):
        print(f"\n✅ 前端文件存在: {frontend_file}")
        
        with open(frontend_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查统计字段
            stats_fields = [
                'total_matched', 'wealth_count', 'marriage_count', 'career_count',
                'children_count', 'character_count', 'summary_count', 'health_count',
                'peach_blossom_count', 'shishen_count', 'parents_count'
            ]
            
            print("\n📊 检查统计字段:")
            for field in stats_fields:
                if field in content:
                    print(f"  ✅ {field}")
                else:
                    print(f"  ❌ {field} - 未找到")
            
            # 检查 API 调用
            if '/api/v1/bazi/formula-analysis' in content:
                print("\n✅ API 调用路径正确")
            else:
                print("\n❌ API 调用路径可能错误")
            
            # 检查数据解析
            if 'statistics' in content:
                print("✅ 使用 statistics 字段")
            else:
                print("❌ 未使用 statistics 字段")
    else:
        print(f"\n❌ 前端文件不存在: {frontend_file}")
    
    return {}


def generate_comparison_report(local_data: Dict, prod_data: Dict) -> Dict:
    """生成对比报告"""
    print("\n" + "="*80)
    print("📋 步骤 5: 生成对比报告")
    print("="*80)
    
    if not local_data or not prod_data:
        print("❌ 数据不完整，无法生成报告")
        return {}
    
    local_matched = local_data.get('matched_by_type', {})
    prod_matched = prod_data.get('rule_counts', {})
    
    print(f"\n{'规则类型':<20} {'本地匹配':<15} {'生产匹配':<15} {'差异':<15} {'状态':<10}")
    print("-" * 75)
    
    all_types = set(list(local_matched.keys()) + list(prod_matched.keys()))
    differences = []
    
    for rule_type in sorted(all_types):
        local_count = local_matched.get(rule_type, 0)
        prod_count = prod_matched.get(rule_type, 0)
        diff = local_count - prod_count
        
        if diff != 0:
            differences.append((rule_type, local_count, prod_count, diff))
            status = "⚠️  不一致"
            print(f"{rule_type:<20} {local_count:<15} {prod_count:<15} {diff:+d}{'':<10} {status}")
        else:
            status = "✅ 一致"
            print(f"{rule_type:<20} {local_count:<15} {prod_count:<15} {'0':<15} {status}")
    
    # 总结
    print(f"\n{'='*80}")
    if differences:
        print(f"⚠️  发现 {len(differences)} 个差异")
        print(f"\n主要问题:")
        for rule_type, local_count, prod_count, diff in differences:
            if abs(diff) >= 5:
                print(f"  🔴 {rule_type}: 本地 {local_count} vs 生产 {prod_count} (差异 {diff:+d})")
    else:
        print("✅ 所有类型完全一致")
    
    return {
        'differences': differences,
        'local_total': local_data.get('matched_count', 0),
        'prod_total': prod_data.get('stats', {}).get('total_matched', 0)
    }


def suggest_fixes(report: Dict):
    """建议修复方案"""
    print("\n" + "="*80)
    print("💡 修复建议")
    print("="*80)
    
    if not report or not report.get('differences'):
        print("✅ 无需修复")
        return
    
    differences = report['differences']
    local_total = report.get('local_total', 0)
    prod_total = report.get('prod_total', 0)
    
    if prod_total < local_total * 0.5:
        print("\n🔴 严重问题: 生产环境匹配数量严重不足")
        print("\n修复方案:")
        print("  1. 检查生产环境数据库规则数量")
        print("  2. 同步规则到生产环境")
        print("  3. 清除缓存")
        print("  4. 验证修复结果")
        
        # 检查 SQL 文件是否存在
        sql_file = os.path.join(project_root, 'scripts/temp_rules_export.sql')
        if os.path.exists(sql_file):
            print(f"\n✅ SQL 文件已准备: {sql_file}")
            print("\n执行修复:")
            print("  bash scripts/manual_sync_rules_to_production.sh")
        else:
            print(f"\n⚠️  SQL 文件不存在，需要先导出:")
            print("  python3 scripts/fix_production_rules.py")
    
    # 检查特定类型的问题
    for rule_type, local_count, prod_count, diff in differences:
        if rule_type == 'career' and prod_count == 0:
            print(f"\n⚠️  事业规则完全缺失 (生产环境 0 条)")
            print("   可能原因: 数据库中没有事业类型规则或规则未启用")
        elif rule_type == 'health' and diff >= 10:
            print(f"\n⚠️  身体规则严重不足 (差异 {diff} 条)")
            print("   可能原因: 数据库规则数量不足或规则未启用")
        elif rule_type == 'summary' and diff >= 5:
            print(f"\n⚠️  总评规则不足 (差异 {diff} 条)")
            print("   可能原因: 数据库规则数量不足或规则未启用")


def main():
    """主函数"""
    print("="*80)
    print("🔍 全面诊断：数据库、逻辑代码、前端展示")
    print("="*80)
    
    # 步骤 1: 检查本地数据库
    local_data = check_local_database()
    
    # 步骤 2: 检查生产环境
    prod_data = check_production_database()
    
    # 步骤 3: 对比数据库和逻辑
    compare_database_and_logic()
    
    # 步骤 4: 检查前端展示
    check_frontend_display()
    
    # 步骤 5: 生成对比报告
    report = generate_comparison_report(local_data, prod_data)
    
    # 步骤 6: 建议修复方案
    suggest_fixes(report)
    
    print("\n" + "="*80)
    print("✅ 诊断完成")
    print("="*80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  诊断被中断")
    except Exception as e:
        print(f"\n❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()

