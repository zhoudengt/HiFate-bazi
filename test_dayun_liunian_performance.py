#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大运流年查询性能测试脚本
测试缓存命中率、性能提升（首次查询 vs 缓存命中）、并发性能
"""

import sys
import os
import time
import asyncio
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from server.services.bazi_detail_service import BaziDetailService
from server.services.special_liunian_service import SpecialLiunianService


def test_bazi_detail_cache_performance():
    """测试 BaziDetailService 缓存性能"""
    print("\n" + "="*80)
    print("测试 1: BaziDetailService.calculate_detail_full() 缓存性能")
    print("="*80)
    
    solar_date = "1990-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 首次查询（缓存未命中）
    print("\n📊 首次查询（缓存未命中）...")
    start_time = time.time()
    result1 = BaziDetailService.calculate_detail_full(
        solar_date, solar_time, gender, current_time
    )
    first_query_time = time.time() - start_time
    print(f"   耗时: {first_query_time:.3f}秒")
    print(f"   结果: {'成功' if result1 else '失败'}")
    
    # 第二次查询（缓存命中）
    print("\n📊 第二次查询（缓存命中）...")
    start_time = time.time()
    result2 = BaziDetailService.calculate_detail_full(
        solar_date, solar_time, gender, current_time
    )
    second_query_time = time.time() - start_time
    print(f"   耗时: {second_query_time:.3f}秒")
    print(f"   结果: {'成功' if result2 else '失败'}")
    
    # 性能提升
    if first_query_time > 0:
        speedup = first_query_time / second_query_time if second_query_time > 0 else float('inf')
        print(f"\n✅ 性能提升: {speedup:.2f}倍")
        print(f"   首次查询: {first_query_time:.3f}秒")
        print(f"   缓存命中: {second_query_time:.3f}秒")
    
    return {
        'first_query_time': first_query_time,
        'second_query_time': second_query_time,
        'speedup': speedup if first_query_time > 0 and second_query_time > 0 else 0
    }


async def test_special_liunian_cache_performance():
    """测试 SpecialLiunianService 缓存性能"""
    print("\n" + "="*80)
    print("测试 2: SpecialLiunianService.get_special_liunians_batch() 缓存性能")
    print("="*80)
    
    solar_date = "1990-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 先获取大运序列
    detail_result = BaziDetailService.calculate_detail_full(
        solar_date, solar_time, gender, current_time
    )
    dayun_sequence = detail_result.get('dayun_sequence', [])
    
    if not dayun_sequence:
        print("❌ 无法获取大运序列，跳过测试")
        return None
    
    # 首次查询（缓存未命中）
    print("\n📊 首次查询（缓存未命中）...")
    start_time = time.time()
    result1 = await SpecialLiunianService.get_special_liunians_batch(
        solar_date, solar_time, gender, dayun_sequence, dayun_count=13, current_time=current_time
    )
    first_query_time = time.time() - start_time
    print(f"   耗时: {first_query_time:.3f}秒")
    print(f"   结果: {len(result1) if result1 else 0} 个特殊流年")
    
    # 第二次查询（缓存命中）
    print("\n📊 第二次查询（缓存命中）...")
    start_time = time.time()
    result2 = await SpecialLiunianService.get_special_liunians_batch(
        solar_date, solar_time, gender, dayun_sequence, dayun_count=13, current_time=current_time
    )
    second_query_time = time.time() - start_time
    print(f"   耗时: {second_query_time:.3f}秒")
    print(f"   结果: {len(result2) if result2 else 0} 个特殊流年")
    
    # 性能提升
    if first_query_time > 0:
        speedup = first_query_time / second_query_time if second_query_time > 0 else float('inf')
        print(f"\n✅ 性能提升: {speedup:.2f}倍")
        print(f"   首次查询: {first_query_time:.3f}秒")
        print(f"   缓存命中: {second_query_time:.3f}秒")
    
    return {
        'first_query_time': first_query_time,
        'second_query_time': second_query_time,
        'speedup': speedup if first_query_time > 0 and second_query_time > 0 else 0,
        'result_count': len(result1) if result1 else 0
    }


async def test_concurrent_performance():
    """测试并发性能"""
    print("\n" + "="*80)
    print("测试 3: 并发性能测试（10个并发请求）")
    print("="*80)
    
    solar_date = "1990-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 先获取大运序列
    detail_result = BaziDetailService.calculate_detail_full(
        solar_date, solar_time, gender, current_time
    )
    dayun_sequence = detail_result.get('dayun_sequence', [])
    
    if not dayun_sequence:
        print("❌ 无法获取大运序列，跳过测试")
        return None
    
    # 并发查询（10个请求）
    print("\n📊 并发查询（10个请求）...")
    start_time = time.time()
    
    async def single_query():
        return await SpecialLiunianService.get_special_liunians_batch(
            solar_date, solar_time, gender, dayun_sequence, dayun_count=13, current_time=current_time
        )
    
    tasks = [single_query() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    concurrent_time = time.time() - start_time
    avg_time = concurrent_time / 10
    
    print(f"   总耗时: {concurrent_time:.3f}秒")
    print(f"   平均耗时: {avg_time:.3f}秒/请求")
    print(f"   成功请求: {sum(1 for r in results if r)}/10")
    
    return {
        'total_time': concurrent_time,
        'avg_time': avg_time,
        'success_count': sum(1 for r in results if r)
    }


def main():
    """主函数"""
    print("\n" + "="*80)
    print("大运流年查询性能测试")
    print("="*80)
    
    results = {}
    
    # 测试 1: BaziDetailService 缓存性能
    try:
        results['bazi_detail'] = test_bazi_detail_cache_performance()
    except Exception as e:
        print(f"❌ 测试 1 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 2: SpecialLiunianService 缓存性能
    try:
        results['special_liunian'] = asyncio.run(test_special_liunian_cache_performance())
    except Exception as e:
        print(f"❌ 测试 2 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 3: 并发性能
    try:
        results['concurrent'] = asyncio.run(test_concurrent_performance())
    except Exception as e:
        print(f"❌ 测试 3 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    if results.get('bazi_detail'):
        r = results['bazi_detail']
        print(f"\n✅ BaziDetailService 缓存性能:")
        print(f"   首次查询: {r['first_query_time']:.3f}秒")
        print(f"   缓存命中: {r['second_query_time']:.3f}秒")
        print(f"   性能提升: {r['speedup']:.2f}倍")
    
    if results.get('special_liunian'):
        r = results['special_liunian']
        print(f"\n✅ SpecialLiunianService 缓存性能:")
        print(f"   首次查询: {r['first_query_time']:.3f}秒")
        print(f"   缓存命中: {r['second_query_time']:.3f}秒")
        print(f"   性能提升: {r['speedup']:.2f}倍")
        print(f"   特殊流年数量: {r['result_count']}")
    
    if results.get('concurrent'):
        r = results['concurrent']
        print(f"\n✅ 并发性能:")
        print(f"   总耗时: {r['total_time']:.3f}秒")
        print(f"   平均耗时: {r['avg_time']:.3f}秒/请求")
        print(f"   成功请求: {r['success_count']}/10")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == '__main__':
    main()

