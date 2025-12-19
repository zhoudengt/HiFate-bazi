#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持续测试对比直到问题解决
"""

import sys
import os
import json
import requests
import time
from datetime import datetime
from typing import Dict

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_local_api() -> Dict:
    """测试本地 API"""
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    try:
        url = "http://localhost:8001/api/v1/bazi/formula-analysis"
        response = requests.post(url, json=test_case, timeout=10)
        response.raise_for_status()
        result = response.json()
        stats = result.get('data', {}).get('statistics', {})
        return {'success': True, 'stats': stats}
    except:
        return {'success': False}


def test_production_api() -> Dict:
    """测试生产环境 API"""
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
        return {'success': True, 'stats': stats}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def compare_results(local_stats: Dict, prod_stats: Dict) -> Dict:
    """对比结果"""
    if not local_stats or not prod_stats:
        return {'fixed': False}
    
    local_total = local_stats.get('total_matched', 0)
    prod_total = prod_stats.get('total_matched', 0)
    
    # 允许 10% 的差异
    target_min = int(local_total * 0.9)
    
    differences = []
    matches = []
    
    fields = [
        'total_matched', 'wealth_count', 'marriage_count', 'career_count',
        'children_count', 'character_count', 'summary_count', 'health_count',
        'peach_blossom_count', 'shishen_count', 'parents_count'
    ]
    
    for field in fields:
        local_val = local_stats.get(field, 0)
        prod_val = prod_stats.get(field, 0)
        if local_val != prod_val:
            differences.append((field, local_val, prod_val))
        else:
            matches.append(field)
    
    is_fixed = prod_total >= target_min
    
    return {
        'fixed': is_fixed,
        'local_total': local_total,
        'prod_total': prod_total,
        'target_min': target_min,
        'differences': differences,
        'matches': matches
    }


def clear_production_cache():
    """清除生产环境缓存"""
    try:
        url = "http://8.210.52.217:8001/api/v1/hot-reload/check"
        requests.post(url, timeout=30)
        return True
    except:
        return False


def main():
    """主函数 - 持续测试直到问题解决"""
    print("="*80)
    print("🔄 持续测试对比直到问题解决")
    print("="*80)
    
    iteration = 0
    max_iterations = 100  # 最多测试 100 次
    check_interval = 10  # 每 10 秒测试一次
    
    # 获取本地基准（如果本地服务运行）
    print("\n📊 获取本地基准...")
    local_result = test_local_api()
    if local_result['success']:
        local_stats = local_result['stats']
        local_total = local_stats.get('total_matched', 0)
        print(f"✅ 本地环境匹配: {local_total} 条规则")
        target_min = int(local_total * 0.9)
        print(f"🎯 目标: 生产环境应匹配 {target_min}+ 条规则")
    else:
        print("⚠️  本地服务未运行，使用默认目标: 50+ 条")
        local_stats = None
        target_min = 50
    
    print(f"\n开始持续测试（每 {check_interval} 秒一次，最多 {max_iterations} 次）...")
    print("按 Ctrl+C 可随时停止")
    print("")
    
    try:
        while iteration < max_iterations:
            iteration += 1
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            print(f"{'='*80}")
            print(f"测试 #{iteration} ({timestamp})")
            print(f"{'='*80}")
            
            # 每 5 次清除一次缓存
            if iteration % 5 == 0 and iteration > 1:
                print("🧹 清除缓存...")
                clear_production_cache()
                time.sleep(3)
            
            # 测试生产环境
            print("📡 测试生产环境...")
            prod_result = test_production_api()
            
            if not prod_result['success']:
                print(f"❌ 测试失败: {prod_result.get('error', 'Unknown error')}")
                time.sleep(check_interval)
                continue
            
            prod_stats = prod_result['stats']
            prod_total = prod_stats.get('total_matched', 0)
            
            print(f"\n📊 生产环境匹配结果:")
            print(f"  总匹配数: {prod_total} 条 (目标: {target_min}+ 条)")
            
            # 显示关键类型
            key_types = {
                'career_count': '事业',
                'health_count': '身体',
                'summary_count': '总评',
                'wealth_count': '财富'
            }
            
            for key, name in key_types.items():
                count = prod_stats.get(key, 0)
                status = "✅" if count > 0 else "⚠️"
                print(f"  {status} {name}: {count} 条")
            
            # 对比结果（如果有本地基准）
            if local_stats:
                comparison = compare_results(local_stats, prod_stats)
                
                if comparison['fixed']:
                    print(f"\n{'='*80}")
                    print("🎉 问题已解决！")
                    print(f"{'='*80}")
                    print(f"生产环境匹配: {prod_total} 条")
                    print(f"本地环境匹配: {comparison['local_total']} 条")
                    print(f"目标最低: {comparison['target_min']} 条")
                    
                    if comparison['matches']:
                        print(f"\n✅ 一致字段 ({len(comparison['matches'])} 个):")
                        for field in comparison['matches']:
                            print(f"  - {field}")
                    
                    if comparison['differences']:
                        print(f"\n⚠️  仍有差异字段 ({len(comparison['differences'])} 个):")
                        for field, local_val, prod_val in comparison['differences']:
                            if abs(local_val - prod_val) >= 3:
                                print(f"  - {field}: 本地 {local_val} vs 生产 {prod_val} (差异 {local_val - prod_val:+d})")
                    
                    print(f"\n✅ 修复成功！匹配数量已达到目标")
                    break
                else:
                    diff = target_min - prod_total
                    print(f"\n⚠️  仍需修复 (差异: {diff} 条)")
                    
                    if iteration == 1:
                        print(f"\n💡 修复步骤:")
                        print(f"  1. 上传 SQL 文件:")
                        print(f"     scp scripts/temp_rules_export.sql root@8.210.52.217:/tmp/rules_import.sql")
                        print(f"  2. 执行 SQL:")
                        print(f"     ssh root@8.210.52.217 'cd /opt/HiFate-bazi && docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql'")
                        print(f"  3. 清除缓存:")
                        print(f"     curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check")
            else:
                # 没有本地基准，只检查是否达到最低目标
                if prod_total >= target_min:
                    print(f"\n{'='*80}")
                    print("🎉 问题已解决！")
                    print(f"{'='*80}")
                    print(f"生产环境匹配: {prod_total} 条 (目标: {target_min}+ 条)")
                    print(f"\n✅ 修复成功！")
                    break
                else:
                    diff = target_min - prod_total
                    print(f"\n⚠️  仍需修复 (差异: {diff} 条)")
            
            # 等待
            if iteration < max_iterations:
                print(f"\n⏳ 等待 {check_interval} 秒后继续测试...")
                time.sleep(check_interval)
        
        if iteration >= max_iterations:
            print(f"\n{'='*80}")
            print(f"⚠️  已达到最大测试次数 ({max_iterations})")
            print(f"{'='*80}")
            print(f"💡 请手动执行修复步骤后，再次运行此脚本验证")
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  测试已停止（已测试 {iteration} 次）")
        print(f"当前状态: 生产环境匹配 {prod_stats.get('total_matched', 0) if 'prod_stats' in locals() else 0} 条")


if __name__ == '__main__':
    main()

