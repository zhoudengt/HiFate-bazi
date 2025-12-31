#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试优化效果 - 不依赖HTTP服务，直接测试代码逻辑

测试内容：
1. 规则匹配完整性（验证超时规则不再丢失）
2. BaziDataOrchestrator功能验证
3. 数据完整性验证
"""

import sys
import os
import asyncio
import time
from typing import Dict, Any, List

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

print("="*60)
print("优化验证测试 - 直接测试代码逻辑")
print("="*60)
print(f"项目根目录: {PROJECT_ROOT}")

# 测试结果
test_results = {
    "rule_matching": [],
    "orchestrator": [],
    "data_consistency": []
}

# 测试用例
TEST_CASE = {
    "solar_date": "1990-01-15",
    "solar_time": "12:00",
    "gender": "male"
}

print(f"\n测试用例: {TEST_CASE}")

# 测试1：验证规则匹配完整性
print("\n" + "="*60)
print("测试1：规则匹配完整性验证")
print("="*60)

try:
    from server.services.rule_service import RuleService
    from server.services.bazi_service import BaziService
    from server.utils.data_validator import validate_bazi_data
    
    print("\n1. 计算八字数据...")
    start_time = time.time()
    bazi_result = BaziService.calculate_bazi_full(
        TEST_CASE["solar_date"],
        TEST_CASE["solar_time"],
        TEST_CASE["gender"]
    )
    calc_time = (time.time() - start_time) * 1000
    print(f"   ✅ 八字计算完成，耗时: {calc_time:.0f}ms")
    
    if not bazi_result:
        print("   ❌ 八字计算失败")
        sys.exit(1)
    
    # 提取八字数据
    bazi_data = bazi_result.get('bazi', bazi_result)
    bazi_data = validate_bazi_data(bazi_data)
    
    print("\n2. 构建规则匹配数据...")
    rule_data = {
        'basic_info': bazi_data.get('basic_info', {}),
        'bazi_pillars': bazi_data.get('bazi_pillars', {}),
        'details': bazi_data.get('details', {}),
        'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
        'elements': bazi_data.get('elements', {}),
        'element_counts': bazi_data.get('element_counts', {}),
        'relationships': bazi_data.get('relationships', {})
    }
    print("   ✅ 规则匹配数据构建完成")
    
    print("\n3. 匹配所有规则类型...")
    start_time = time.time()
    matched_rules = RuleService.match_rules(
        rule_data,
        rule_types=None,  # 匹配所有类型
        use_cache=True
    )
    match_time = (time.time() - start_time) * 1000
    print(f"   ✅ 规则匹配完成，耗时: {match_time:.0f}ms")
    print(f"   📊 匹配到的规则数量: {len(matched_rules)}")
    
    # 按规则类型统计
    rule_type_count = {}
    for rule in matched_rules:
        rule_type = rule.get('rule_type', 'unknown')
        rule_type_count[rule_type] = rule_type_count.get(rule_type, 0) + 1
    
    print(f"   📊 规则类型分布: {rule_type_count}")
    
    # 验证完整性（至少应该有30个规则，修复后应该更多）
    expected_min = 30
    is_complete = len(matched_rules) >= expected_min
    
    if is_complete:
        print(f"\n   ✅ 规则匹配完整性验证通过: {len(matched_rules)} 个规则（期望至少{expected_min}个）")
    else:
        print(f"\n   ⚠️  规则匹配数量: {len(matched_rules)} 个（期望至少{expected_min}个）")
    
    test_results["rule_matching"].append({
        "success": is_complete,
        "matched_count": len(matched_rules),
        "expected_min": expected_min,
        "rule_type_count": rule_type_count,
        "match_time_ms": match_time
    })
    
except Exception as e:
    import traceback
    print(f"\n   ❌ 规则匹配测试失败: {e}")
    print(traceback.format_exc())
    test_results["rule_matching"].append({
        "success": False,
        "error": str(e)
    })

# 测试2：验证BaziDataOrchestrator功能
print("\n" + "="*60)
print("测试2：BaziDataOrchestrator功能验证")
print("="*60)

async def test_orchestrator():
    try:
        from server.services.bazi_data_orchestrator import BaziDataOrchestrator
        
        modules = {
            'bazi': True,
            'wangshuai': True,
            'detail': True
        }
        
        print("\n1. 第一次调用（缓存未命中）...")
        start_time = time.time()
        unified_data_1 = await BaziDataOrchestrator.fetch_data(
            TEST_CASE["solar_date"],
            TEST_CASE["solar_time"],
            TEST_CASE["gender"],
            modules,
            use_cache=True,
            parallel=True
        )
        time_1 = (time.time() - start_time) * 1000
        print(f"   ✅ 完成，耗时: {time_1:.0f}ms")
        
        # 验证数据完整性
        bazi_1 = unified_data_1.get('bazi', {})
        wangshuai_1 = unified_data_1.get('wangshuai', {})
        detail_1 = unified_data_1.get('detail', {})
        
        has_bazi = bool(bazi_1)
        has_wangshuai = bool(wangshuai_1)
        has_detail = bool(detail_1)
        
        print(f"   📊 数据完整性: bazi={has_bazi}, wangshuai={has_wangshuai}, detail={has_detail}")
        
        print("\n2. 第二次调用（缓存命中）...")
        start_time = time.time()
        unified_data_2 = await BaziDataOrchestrator.fetch_data(
            TEST_CASE["solar_date"],
            TEST_CASE["solar_time"],
            TEST_CASE["gender"],
            modules,
            use_cache=True,
            parallel=True
        )
        time_2 = (time.time() - start_time) * 1000
        print(f"   ✅ 完成，耗时: {time_2:.0f}ms")
        
        # 验证数据一致性
        bazi_2 = unified_data_2.get('bazi', {})
        wangshuai_2 = unified_data_2.get('wangshuai', {})
        detail_2 = unified_data_2.get('detail', {})
        
        is_consistent = (
            bazi_1 == bazi_2 and
            wangshuai_1 == wangshuai_2 and
            detail_1 == detail_2
        )
        
        print(f"   📊 数据一致性: {'✅ 通过' if is_consistent else '❌ 失败'}")
        
        # 计算缓存效果
        cache_improvement = ((time_1 - time_2) / time_1 * 100) if time_1 > 0 else 0
        print(f"   📊 缓存效果: 性能提升 {cache_improvement:.1f}%")
        
        test_results["orchestrator"].append({
            "success": is_consistent and has_bazi and has_wangshuai and has_detail,
            "first_call_time_ms": time_1,
            "second_call_time_ms": time_2,
            "cache_improvement_percent": cache_improvement,
            "is_consistent": is_consistent,
            "has_bazi": has_bazi,
            "has_wangshuai": has_wangshuai,
            "has_detail": has_detail
        })
        
        if test_results["orchestrator"][-1]["success"]:
            print(f"\n   ✅ BaziDataOrchestrator功能验证通过")
        else:
            print(f"\n   ❌ BaziDataOrchestrator功能验证失败")
        
    except Exception as e:
        import traceback
        print(f"\n   ❌ BaziDataOrchestrator测试失败: {e}")
        print(traceback.format_exc())
        test_results["orchestrator"].append({
            "success": False,
            "error": str(e)
        })

# 测试3：验证并行计算安全性
print("\n" + "="*60)
print("测试3：并行计算安全性验证")
print("="*60)

async def test_parallel_safety():
    try:
        from server.services.bazi_data_orchestrator import BaziDataOrchestrator
        
        modules = {
            'bazi': True,
            'wangshuai': True,
            'detail': True
        }
        
        print("\n1. 执行10次并行调用...")
        tasks = []
        for i in range(10):
            task = BaziDataOrchestrator.fetch_data(
                TEST_CASE["solar_date"],
                TEST_CASE["solar_time"],
                TEST_CASE["gender"],
                modules,
                use_cache=True,
                parallel=True
            )
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.time() - start_time) * 1000
        print(f"   ✅ 完成，总耗时: {total_time:.0f}ms，平均: {total_time/10:.0f}ms")
        
        # 验证所有结果都成功
        print("\n2. 验证所有结果都成功...")
        success_count = 0
        error_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                if error_count <= 3:
                    print(f"   ❌ 调用 {i+1}: 失败 - {result}")
            else:
                success_count += 1
        
        print(f"   📊 成功: {success_count}, 失败: {error_count}")
        
        # 验证数据一致性
        print("\n3. 验证数据一致性...")
        if success_count > 0:
            first_result = None
            for result in results:
                if not isinstance(result, Exception):
                    first_result = result
                    break
            
            if first_result:
                is_consistent = True
                inconsistent_count = 0
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        continue
                    if result != first_result:
                        is_consistent = False
                        inconsistent_count += 1
                
                if is_consistent:
                    print(f"   ✅ 所有调用数据一致")
                else:
                    print(f"   ❌ 有 {inconsistent_count} 个调用数据不一致")
            else:
                is_consistent = False
        else:
            is_consistent = False
        
        test_results["data_consistency"].append({
            "success": success_count == 10 and is_consistent,
            "total_calls": 10,
            "success_count": success_count,
            "error_count": error_count,
            "is_consistent": is_consistent,
            "total_time_ms": total_time,
            "avg_time_ms": total_time / 10
        })
        
        if test_results["data_consistency"][-1]["success"]:
            print(f"\n   ✅ 并行计算安全性验证通过")
        else:
            print(f"\n   ❌ 并行计算安全性验证失败")
        
    except Exception as e:
        import traceback
        print(f"\n   ❌ 并行计算安全性测试失败: {e}")
        print(traceback.format_exc())
        test_results["data_consistency"].append({
            "success": False,
            "error": str(e)
        })

# 运行异步测试
print("\n运行异步测试...")
asyncio.run(test_orchestrator())
asyncio.run(test_parallel_safety())

# 汇总结果
print("\n\n" + "="*60)
print("测试结果汇总")
print("="*60)

# 规则匹配完整性
rule_success = sum(1 for r in test_results["rule_matching"] if r.get("success"))
rule_total = len(test_results["rule_matching"])
print(f"\n1. 规则匹配完整性测试: {rule_success}/{rule_total} 通过")
for i, result in enumerate(test_results["rule_matching"]):
    status = "✅" if result.get("success") else "❌"
    matched_count = result.get('matched_count', 0)
    expected_min = result.get('expected_min', 0)
    match_time = result.get('match_time_ms', 0)
    print(f"   {status} 匹配到 {matched_count} 个规则（期望至少{expected_min}个），耗时 {match_time:.0f}ms")

# BaziDataOrchestrator功能
orchestrator_success = sum(1 for r in test_results["orchestrator"] if r.get("success"))
orchestrator_total = len(test_results["orchestrator"])
print(f"\n2. BaziDataOrchestrator功能测试: {orchestrator_success}/{orchestrator_total} 通过")
for i, result in enumerate(test_results["orchestrator"]):
    status = "✅" if result.get("success") else "❌"
    first_time = result.get('first_call_time_ms', 0)
    second_time = result.get('second_call_time_ms', 0)
    cache_improvement = result.get('cache_improvement_percent', 0)
    print(f"   {status} 首次={first_time:.0f}ms, 缓存={second_time:.0f}ms, 提升={cache_improvement:.1f}%")

# 并行计算安全性
parallel_success = sum(1 for r in test_results["data_consistency"] if r.get("success"))
parallel_total = len(test_results["data_consistency"])
print(f"\n3. 并行计算安全性测试: {parallel_success}/{parallel_total} 通过")
for i, result in enumerate(test_results["data_consistency"]):
    status = "✅" if result.get("success") else "❌"
    success_count = result.get('success_count', 0)
    avg_time = result.get('avg_time_ms', 0)
    print(f"   {status} {success_count}/10 次调用成功，平均耗时={avg_time:.0f}ms")

# 总体结果
total_success = rule_success + orchestrator_success + parallel_success
total_tests = rule_total + orchestrator_total + parallel_total
print(f"\n{'='*60}")
print(f"总计: {total_success}/{total_tests} 通过")
print(f"{'='*60}")

if total_success == total_tests:
    print("\n🎉 所有测试通过！优化验证成功！")
    sys.exit(0)
else:
    print(f"\n⚠️  有 {total_tests - total_success} 个测试失败，请检查。")
    sys.exit(1)

