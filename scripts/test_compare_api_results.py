#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试对比生产环境和本地环境的接口返回数量
"""

import sys
import os
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class APITester:
    """API 测试类"""
    
    def __init__(self, base_url: str, env_name: str):
        self.base_url = base_url.rstrip('/')
        self.env_name = env_name
        self.timeout = 30
    
    def test_formula_analysis(self, solar_date: str, solar_time: str, gender: str) -> Dict:
        """测试公式分析接口"""
        url = f"{self.base_url}/api/v1/bazi/formula-analysis"
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        
        try:
            start_time = datetime.now()
            response = requests.post(url, json=data, timeout=self.timeout)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            response.raise_for_status()
            result = response.json()
            
            # 提取统计信息
            statistics = result.get('data', {}).get('statistics', {})
            matched_rules = result.get('data', {}).get('matched_rules', {})
            
            # 统计各类型规则数量
            rule_counts = {}
            for rule_type, rule_ids in matched_rules.items():
                rule_counts[rule_type] = len(rule_ids) if isinstance(rule_ids, list) else 0
            
            return {
                'success': result.get('success', False),
                'statistics': statistics,
                'rule_counts': rule_counts,
                'total_matched': statistics.get('total_matched', 0),
                'response_time': elapsed,
                'raw_response': result
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'response_time': 0
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response_time': 0
            }


def compare_results(prod_result: Dict, local_result: Dict, test_case: Dict):
    """对比结果"""
    print("\n" + "="*80)
    print("📊 对比结果")
    print("="*80)
    
    print(f"\n测试用例: {test_case['solar_date']} {test_case['solar_time']} {test_case['gender']}")
    
    if not prod_result.get('success'):
        print(f"❌ 生产环境请求失败: {prod_result.get('error', 'Unknown error')}")
        return
    
    if not local_result.get('success'):
        print(f"⚠️  本地环境请求失败: {local_result.get('error', 'Unknown error')}")
        print("   仅显示生产环境结果")
        return
    
    prod_stats = prod_result.get('statistics', {})
    local_stats = local_result.get('statistics', {})
    
    # 对比统计字段
    fields = [
        'total_matched', 'wealth_count', 'marriage_count', 'career_count',
        'children_count', 'character_count', 'summary_count', 'health_count',
        'peach_blossom_count', 'shishen_count', 'parents_count'
    ]
    
    print(f"\n{'字段':<25} {'生产环境':<15} {'本地环境':<15} {'差异':<15} {'状态':<10}")
    print("-" * 80)
    
    differences = []
    matches = []
    
    for field in fields:
        prod_val = prod_stats.get(field, 0)
        local_val = local_stats.get(field, 0)
        diff = local_val - prod_val
        
        if diff != 0:
            differences.append((field, prod_val, local_val, diff))
            status = "⚠️  不一致"
            print(f"{field:<25} {prod_val:<15} {local_val:<15} {diff:+d}{'':<10} {status}")
        else:
            matches.append(field)
            status = "✅ 一致"
            print(f"{field:<25} {prod_val:<15} {local_val:<15} {'0':<15} {status}")
    
    # 响应时间对比
    prod_time = prod_result.get('response_time', 0)
    local_time = local_result.get('response_time', 0)
    print(f"\n{'响应时间':<25} {prod_time:.3f}s{'':<10} {local_time:.3f}s{'':<10} {abs(prod_time - local_time):.3f}s")
    
    # 总结
    print(f"\n{'='*80}")
    if differences:
        print(f"⚠️  发现 {len(differences)} 个差异字段，{len(matches)} 个一致字段")
        print(f"\n主要差异:")
        for field, prod_val, local_val, diff in differences:
            if abs(diff) >= 5:  # 差异大于等于5的标记为重要
                print(f"  🔴 {field}: 生产 {prod_val} vs 本地 {local_val} (差异 {diff:+d})")
            else:
                print(f"  🟡 {field}: 生产 {prod_val} vs 本地 {local_val} (差异 {diff:+d})")
    else:
        print(f"✅ 所有字段完全一致！")
    
    return {
        'differences': differences,
        'matches': matches,
        'prod_time': prod_time,
        'local_time': local_time
    }


def test_multiple_cases():
    """测试多个用例"""
    print("="*80)
    print("🧪 接口返回数量对比测试")
    print("="*80)
    
    # 测试用例
    test_cases = [
        {
            'solar_date': '1987-01-07',
            'solar_time': '09:00',
            'gender': 'male',
            'description': '原始测试用例'
        },
        {
            'solar_date': '1990-05-15',
            'solar_time': '14:30',
            'gender': 'female',
            'description': '女性测试用例'
        },
        {
            'solar_date': '1995-12-25',
            'solar_time': '00:00',
            'gender': 'male',
            'description': '子时测试用例'
        }
    ]
    
    # 初始化测试器
    prod_tester = APITester('http://8.210.52.217:8001', '生产环境')
    local_tester = APITester('http://localhost:8001', '本地环境')
    
    all_results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试用例 {i}/{len(test_cases)}: {test_case['description']}")
        print(f"{'='*80}")
        
        # 测试生产环境
        print(f"\n📡 测试生产环境...")
        prod_result = prod_tester.test_formula_analysis(
            test_case['solar_date'],
            test_case['solar_time'],
            test_case['gender']
        )
        
        if prod_result.get('success'):
            print(f"✅ 生产环境: 总匹配 {prod_result.get('total_matched', 0)} 条规则, 耗时 {prod_result.get('response_time', 0):.3f}s")
        else:
            print(f"❌ 生产环境失败: {prod_result.get('error', 'Unknown error')}")
        
        # 测试本地环境
        print(f"\n📡 测试本地环境...")
        local_result = local_tester.test_formula_analysis(
            test_case['solar_date'],
            test_case['solar_time'],
            test_case['gender']
        )
        
        if local_result.get('success'):
            print(f"✅ 本地环境: 总匹配 {local_result.get('total_matched', 0)} 条规则, 耗时 {local_result.get('response_time', 0):.3f}s")
        else:
            print(f"⚠️  本地环境失败: {local_result.get('error', 'Unknown error')}")
            print("   本地服务可能未运行，跳过对比")
            continue
        
        # 对比结果
        comparison = compare_results(prod_result, local_result, test_case)
        if comparison:
            all_results.append({
                'test_case': test_case,
                'comparison': comparison
            })
    
    # 生成总结报告
    print(f"\n{'='*80}")
    print("📋 测试总结")
    print(f"{'='*80}")
    
    if all_results:
        total_differences = sum(len(r['comparison']['differences']) for r in all_results)
        total_matches = sum(len(r['comparison']['matches']) for r in all_results)
        
        print(f"\n测试用例数: {len(all_results)}")
        print(f"总差异字段数: {total_differences}")
        print(f"总一致字段数: {total_matches}")
        
        if total_differences > 0:
            print(f"\n⚠️  发现差异，建议检查:")
            print(f"  1. 生产环境数据库规则数量")
            print(f"  2. 规则 enabled 状态")
            print(f"  3. 缓存是否影响")
            print(f"  4. 代码版本是否一致")
        else:
            print(f"\n✅ 所有测试用例完全一致！")
    else:
        print(f"\n⚠️  没有可对比的结果（本地服务可能未运行）")
    
    print(f"\n💡 详细诊断步骤请参考: docs/问题诊断-生产环境规则匹配差异.md")


def main():
    """主函数"""
    try:
        test_multiple_cases()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

