#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过 API 检查生产环境数据库规则（间接方式）
通过测试多个八字来推断规则数量
"""

import sys
import os
import json
import requests
from typing import Dict, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_multiple_cases():
    """测试多个用例来推断规则数量"""
    print("="*80)
    print("🔍 通过 API 测试推断生产环境规则数量")
    print("="*80)
    
    # 测试多个不同的八字
    test_cases = [
        {'solar_date': '1987-01-07', 'solar_time': '09:00', 'gender': 'male', 'desc': '原始用例'},
        {'solar_date': '1990-05-15', 'solar_time': '14:30', 'gender': 'female', 'desc': '女性用例'},
        {'solar_date': '1995-12-25', 'solar_time': '00:00', 'gender': 'male', 'desc': '子时用例'},
        {'solar_date': '1980-06-20', 'solar_time': '12:00', 'gender': 'male', 'desc': '午时用例'},
        {'solar_date': '2000-01-01', 'solar_time': '08:00', 'gender': 'female', 'desc': '千禧年用例'},
    ]
    
    url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
    
    all_stats = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}/{len(test_cases)}: {test_case['desc']}")
        try:
            response = requests.post(url, json=test_case, timeout=30)
            response.raise_for_status()
            result = response.json()
            stats = result.get('data', {}).get('statistics', {})
            all_stats.append(stats)
            
            total = stats.get('total_matched', 0)
            print(f"  ✅ 总匹配数: {total} 条")
            
            # 显示关键类型
            key_types = ['career_count', 'health_count', 'summary_count']
            for key in key_types:
                count = stats.get(key, 0)
                if count > 0:
                    print(f"     {key}: {count}")
                elif 'career' in key:
                    print(f"     ⚠️  {key}: {count} (应该 > 0)")
                    
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
    
    # 分析结果
    print(f"\n{'='*80}")
    print("📊 分析结果")
    print(f"{'='*80}")
    
    if all_stats:
        totals = [s.get('total_matched', 0) for s in all_stats]
        avg_total = sum(totals) / len(totals)
        max_total = max(totals)
        min_total = min(totals)
        
        print(f"\n统计信息:")
        print(f"  平均匹配数: {avg_total:.1f} 条")
        print(f"  最大匹配数: {max_total} 条")
        print(f"  最小匹配数: {min_total} 条")
        
        # 检查关键类型
        career_counts = [s.get('career_count', 0) for s in all_stats]
        health_counts = [s.get('health_count', 0) for s in all_stats]
        summary_counts = [s.get('summary_count', 0) for s in all_stats]
        
        print(f"\n关键类型分析:")
        print(f"  事业规则: 平均 {sum(career_counts)/len(career_counts):.1f} 条 (最大 {max(career_counts)}, 最小 {min(career_counts)})")
        if max(career_counts) == 0:
            print(f"    ⚠️  所有用例都匹配 0 条事业规则，说明数据库可能缺少事业类型规则")
        
        print(f"  身体规则: 平均 {sum(health_counts)/len(health_counts):.1f} 条 (最大 {max(health_counts)}, 最小 {min(health_counts)})")
        if max(health_counts) < 10:
            print(f"    ⚠️  身体规则数量明显不足（本地应该有 20+ 条）")
        
        print(f"  总评规则: 平均 {sum(summary_counts)/len(summary_counts):.1f} 条 (最大 {max(summary_counts)}, 最小 {min(summary_counts)})")
        if max(summary_counts) < 5:
            print(f"    ⚠️  总评规则数量明显不足（本地应该有 8+ 条）")
        
        # 结论
        print(f"\n💡 结论:")
        if avg_total < 30:
            print(f"  🔴 生产环境规则数量严重不足（平均 {avg_total:.1f} 条，本地应该有 50+ 条）")
            print(f"  ✅ 需要同步规则到生产环境")
        elif avg_total < 50:
            print(f"  🟡 生产环境规则数量不足（平均 {avg_total:.1f} 条，本地应该有 50+ 条）")
            print(f"  ✅ 建议同步规则到生产环境")
        else:
            print(f"  ✅ 生产环境规则数量正常（平均 {avg_total:.1f} 条）")


def main():
    """主函数"""
    try:
        test_multiple_cases()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

