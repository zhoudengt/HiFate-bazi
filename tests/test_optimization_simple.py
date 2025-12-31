#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化优化验证测试 - 验证API优化效果（不依赖数据库）

测试内容：
1. 优化后的API接口功能测试
2. 数据完整性验证
3. 缓存效果验证
"""

import sys
import os
import asyncio
import time
from typing import Dict, Any

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    from server.services.bazi_data_orchestrator import BaziDataOrchestrator
    from server.utils.data_validator import validate_bazi_data
except ImportError as e:
    print(f"⚠️  导入失败: {e}")
    print("请确保已安装所有依赖并激活虚拟环境")
    sys.exit(1)


async def test_optimized_api(
    solar_date: str,
    solar_time: str,
    gender: str
) -> Dict[str, Any]:
    """
    测试优化后的API接口
    
    Args:
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
        
    Returns:
        dict: 测试结果
    """
    print(f"\n{'='*60}")
    print(f"测试优化后的API接口")
    print(f"{'='*60}")
    print(f"参数: {solar_date} {solar_time} {gender}")
    
    try:
        # 1. 测试 BaziDataOrchestrator.fetch_data()
        print("\n1. 测试 BaziDataOrchestrator.fetch_data()...")
        
        modules = {
            'bazi': True,
            'wangshuai': True,
            'detail': True
        }
        
        # 第一次调用（缓存未命中）
        print("   第一次调用（缓存未命中）...")
        start_time = time.time()
        unified_data_1 = await BaziDataOrchestrator.fetch_data(
            solar_date, solar_time, gender, modules,
            use_cache=True, parallel=True
        )
        time_1 = (time.time() - start_time) * 1000
        print(f"   耗时: {time_1:.0f}ms")
        
        # 验证数据完整性
        bazi_1 = unified_data_1.get('bazi', {})
        wangshuai_1 = unified_data_1.get('wangshuai', {})
        detail_1 = unified_data_1.get('detail', {})
        
        has_bazi = bool(bazi_1)
        has_wangshuai = bool(wangshuai_1)
        has_detail = bool(detail_1)
        
        print(f"   数据完整性: bazi={has_bazi}, wangshuai={has_wangshuai}, detail={has_detail}")
        
        # 第二次调用（缓存命中）
        print("   第二次调用（缓存命中）...")
        start_time = time.time()
        unified_data_2 = await BaziDataOrchestrator.fetch_data(
            solar_date, solar_time, gender, modules,
            use_cache=True, parallel=True
        )
        time_2 = (time.time() - start_time) * 1000
        print(f"   耗时: {time_2:.0f}ms")
        
        # 验证数据一致性
        print("\n2. 验证数据一致性...")
        bazi_2 = unified_data_2.get('bazi', {})
        wangshuai_2 = unified_data_2.get('wangshuai', {})
        detail_2 = unified_data_2.get('detail', {})
        
        is_consistent = (
            bazi_1 == bazi_2 and
            wangshuai_1 == wangshuai_2 and
            detail_1 == detail_2
        )
        
        print(f"   数据一致性: {'✅ 通过' if is_consistent else '❌ 失败'}")
        
        # 计算缓存效果
        cache_improvement = ((time_1 - time_2) / time_1 * 100) if time_1 > 0 else 0
        print(f"   缓存效果: 性能提升 {cache_improvement:.1f}%")
        
        result = {
            "success": is_consistent and has_bazi and has_wangshuai and has_detail,
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender,
            "first_call_time_ms": time_1,
            "second_call_time_ms": time_2,
            "cache_improvement_percent": cache_improvement,
            "is_consistent": is_consistent,
            "has_bazi": has_bazi,
            "has_wangshuai": has_wangshuai,
            "has_detail": has_detail,
            "error": None
        }
        
        if result["success"]:
            print(f"\n✅ API接口测试通过")
        else:
            print(f"\n❌ API接口测试失败")
            if not has_bazi:
                print("   - bazi数据缺失")
            if not has_wangshuai:
                print("   - wangshuai数据缺失")
            if not has_detail:
                print("   - detail数据缺失")
            if not is_consistent:
                print("   - 数据不一致")
        
        return result
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"\n❌ 测试失败: {e}\n{error_msg}")
        return {
            "success": False,
            "error": str(e),
            "traceback": error_msg
        }


async def test_parallel_safety(
    solar_date: str,
    solar_time: str,
    gender: str
) -> Dict[str, Any]:
    """
    测试并行计算安全性
    
    Args:
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
        
    Returns:
        dict: 测试结果
    """
    print(f"\n{'='*60}")
    print(f"测试并行计算安全性")
    print(f"{'='*60}")
    print(f"参数: {solar_date} {solar_time} {gender}")
    
    try:
        # 多次并行调用，验证数据一致性
        print("\n1. 执行10次并行调用...")
        modules = {
            'bazi': True,
            'wangshuai': True,
            'detail': True
        }
        
        tasks = []
        for i in range(10):
            task = BaziDataOrchestrator.fetch_data(
                solar_date, solar_time, gender, modules,
                use_cache=True, parallel=True
            )
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.time() - start_time) * 1000
        print(f"   总耗时: {total_time:.0f}ms")
        print(f"   平均耗时: {total_time / 10:.0f}ms")
        
        # 验证所有结果都成功
        print("\n2. 验证所有结果都成功...")
        success_count = 0
        error_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                print(f"   调用 {i+1}: ❌ 失败 - {result}")
            else:
                success_count += 1
                if i < 3:  # 只显示前3个
                    print(f"   调用 {i+1}: ✅ 成功")
        
        print(f"   成功: {success_count}, 失败: {error_count}")
        
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
                        if inconsistent_count <= 3:  # 只显示前3个不一致的
                            print(f"   调用 {i+1}: ❌ 数据不一致")
                
                if is_consistent:
                    print(f"   ✅ 所有调用数据一致")
                else:
                    print(f"   ❌ 有 {inconsistent_count} 个调用数据不一致")
            else:
                is_consistent = False
        else:
            is_consistent = False
        
        result = {
            "success": success_count == 10 and is_consistent,
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender,
            "total_calls": 10,
            "success_count": success_count,
            "error_count": error_count,
            "is_consistent": is_consistent,
            "total_time_ms": total_time,
            "avg_time_ms": total_time / 10,
            "error": None
        }
        
        if result["success"]:
            print(f"\n✅ 并行计算安全性测试通过")
        else:
            print(f"\n❌ 并行计算安全性测试失败")
            if success_count < 10:
                print(f"   - 有 {error_count} 个调用失败")
            if not is_consistent:
                print(f"   - 数据不一致")
        
        return result
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"\n❌ 测试失败: {e}\n{error_msg}")
        return {
            "success": False,
            "error": str(e),
            "traceback": error_msg
        }


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("简化优化验证测试")
    print("="*60)
    
    # 测试用例
    test_cases = [
        {
            "name": "测试用例1",
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male",
        },
        {
            "name": "测试用例2",
            "solar_date": "1995-05-20",
            "solar_time": "14:30",
            "gender": "female",
        },
    ]
    
    # 测试结果
    test_results = {
        "optimized_api": [],
        "parallel_safety": []
    }
    
    # 运行测试用例
    for test_case in test_cases:
        print(f"\n\n{'#'*60}")
        print(f"测试用例: {test_case['name']}")
        print(f"{'#'*60}")
        
        solar_date = test_case['solar_date']
        solar_time = test_case['solar_time']
        gender = test_case['gender']
        
        # 1. 测试优化后的API接口
        api_result = await test_optimized_api(solar_date, solar_time, gender)
        test_results["optimized_api"].append(api_result)
        
        # 2. 测试并行计算安全性
        parallel_result = await test_parallel_safety(solar_date, solar_time, gender)
        test_results["parallel_safety"].append(parallel_result)
    
    # 汇总结果
    print("\n\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    # 优化后的API接口
    api_success = sum(1 for r in test_results["optimized_api"] if r.get("success"))
    api_total = len(test_results["optimized_api"])
    print(f"\n优化后的API接口测试: {api_success}/{api_total} 通过")
    for i, result in enumerate(test_results["optimized_api"]):
        status = "✅" if result.get("success") else "❌"
        cache_improvement = result.get('cache_improvement_percent', 0)
        first_time = result.get('first_call_time_ms', 0)
        second_time = result.get('second_call_time_ms', 0)
        print(f"  {status} 测试用例 {i+1}: 首次={first_time:.0f}ms, 缓存={second_time:.0f}ms, 提升={cache_improvement:.1f}%")
    
    # 并行计算安全性
    parallel_success = sum(1 for r in test_results["parallel_safety"] if r.get("success"))
    parallel_total = len(test_results["parallel_safety"])
    print(f"\n并行计算安全性测试: {parallel_success}/{parallel_total} 通过")
    for i, result in enumerate(test_results["parallel_safety"]):
        status = "✅" if result.get("success") else "❌"
        success_count = result.get('success_count', 0)
        avg_time = result.get('avg_time_ms', 0)
        print(f"  {status} 测试用例 {i+1}: {success_count}/10 次调用成功, 平均耗时={avg_time:.0f}ms")
    
    # 总体结果
    total_success = api_success + parallel_success
    total_tests = api_total + parallel_total
    print(f"\n{'='*60}")
    print(f"总计: {total_success}/{total_tests} 通过")
    print(f"{'='*60}")
    
    if total_success == total_tests:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total_tests - total_success} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

