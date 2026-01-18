#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一接口性能测试（简化版）
只测试核心计算功能，不依赖外部服务（grpc、redis、数据库等）

测试目标：
1. 首次响应 < 100ms（快速模式）
2. 预热 < 3秒（10个大运并行）
3. 缓存命中 < 10ms（内存缓存）
"""

import sys
import os
import time
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 直接使用本地计算函数，不依赖服务层
try:
    from core.calculators.helpers import compute_local_detail
    print("✅ 使用本地计算函数")
except ImportError as e:
    print(f"❌ 无法导入本地计算函数: {e}")
    sys.exit(1)


# 简单的内存缓存实现
class SimpleCache:
    """简单的内存缓存，用于测试缓存性能"""
    def __init__(self):
        self._cache = {}
    
    def get(self, key):
        return self._cache.get(key)
    
    def set(self, key, value):
        self._cache[key] = value
    
    def clear(self):
        self._cache.clear()


# 全局缓存实例
simple_cache = SimpleCache()


def compute_with_cache(solar_date: str, solar_time: str, gender: str, 
                       current_time: datetime = None, dayun_index: int = None,
                       use_cache: bool = True):
    """带缓存的计算函数"""
    # 生成缓存键
    cache_key = f"{solar_date}:{solar_time}:{gender}:{current_time.isoformat() if current_time else 'default'}:{dayun_index or 'all'}"
    
    # 尝试从缓存读取
    if use_cache:
        cached = simple_cache.get(cache_key)
        if cached:
            return cached, True
    
    # 计算
    result = compute_local_detail(
        solar_date, solar_time, gender,
        current_time=current_time,
        dayun_index=dayun_index
    )
    
    # 写入缓存
    if use_cache:
        simple_cache.set(cache_key, result)
    
    return result, False


def test_first_response_performance():
    """测试1：首次响应性能（快速模式）< 100ms"""
    print("\n" + "="*80)
    print("测试1：首次响应性能（快速模式）")
    print("目标：< 100ms")
    print("="*80)
    
    # 使用唯一的测试数据
    test_id = int(time.time() * 1000) % 1000000
    solar_date = f"1990-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 执行多次测试取平均值
    test_count = 10
    response_times = []
    
    for i in range(test_count):
        # 使用唯一的参数避免缓存
        unique_solar_date = f"199{test_id % 10}-05-{(15 + i) % 28 + 1:02d}"
        
        start_time = time.time()
        try:
            result, _ = compute_with_cache(
                unique_solar_date, solar_time, gender,
                current_time=current_time,
                dayun_index=0,  # 只计算第一个大运（快速模式）
                use_cache=False  # 首次计算不使用缓存
            )
            elapsed_ms = (time.time() - start_time) * 1000
            response_times.append(elapsed_ms)
            
            # 验证返回数据完整性
            assert result is not None, "返回结果不能为空"
            assert 'bazi_pillars' in result, "必须包含基础八字数据"
            
            print(f"  测试 {i+1}/{test_count}: {elapsed_ms:.2f}ms - ✅ 数据完整")
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            response_times.append(elapsed_ms)
            print(f"  测试 {i+1}/{test_count}: {elapsed_ms:.2f}ms - ❌ 错误: {e}")
    
    # 统计结果
    if response_times:
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        median_time = statistics.median(response_times)
        
        print(f"\n📊 统计结果：")
        print(f"  平均响应时间: {avg_time:.2f}ms")
        print(f"  最小响应时间: {min_time:.2f}ms")
        print(f"  最大响应时间: {max_time:.2f}ms")
        print(f"  中位数响应时间: {median_time:.2f}ms")
        
        # 判断是否达标
        target_ms = 100
        if avg_time < target_ms:
            print(f"\n✅ 测试通过：平均响应时间 {avg_time:.2f}ms < 目标 {target_ms}ms")
            return True
        else:
            print(f"\n❌ 测试失败：平均响应时间 {avg_time:.2f}ms >= 目标 {target_ms}ms")
            return False
    else:
        print("\n❌ 所有测试都失败")
        return False


def test_cache_hit_performance():
    """测试2：缓存命中性能 < 10ms"""
    print("\n" + "="*80)
    print("测试2：缓存命中性能（内存缓存）")
    print("目标：< 10ms")
    print("="*80)
    
    # 使用固定的测试数据
    solar_date = "1990-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 先执行一次计算，确保缓存存在
    print("  预热：执行首次计算以填充缓存...")
    start_time = time.time()
    result, _ = compute_with_cache(
        solar_date, solar_time, gender,
        current_time=current_time,
        dayun_index=0,
        use_cache=True
    )
    warmup_time = (time.time() - start_time) * 1000
    print(f"  预热完成，耗时: {warmup_time:.2f}ms")
    
    # 执行多次缓存命中测试
    test_count = 20
    cache_hit_times = []
    
    for i in range(test_count):
        start_time = time.time()
        try:
            result, cached = compute_with_cache(
                solar_date, solar_time, gender,
                current_time=current_time,
                dayun_index=0,
                use_cache=True
            )
            elapsed_ms = (time.time() - start_time) * 1000
            cache_hit_times.append(elapsed_ms)
            
            assert result is not None, "返回结果不能为空"
            status = "✅" if cached else "⚠️"
            print(f"  测试 {i+1}/{test_count}: {elapsed_ms:.2f}ms - {status}")
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            cache_hit_times.append(elapsed_ms)
            print(f"  测试 {i+1}/{test_count}: {elapsed_ms:.2f}ms - ❌ 错误: {e}")
    
    # 统计结果
    if cache_hit_times:
        avg_time = statistics.mean(cache_hit_times)
        min_time = min(cache_hit_times)
        max_time = max(cache_hit_times)
        median_time = statistics.median(cache_hit_times)
        
        print(f"\n📊 统计结果：")
        print(f"  平均响应时间: {avg_time:.2f}ms")
        print(f"  最小响应时间: {min_time:.2f}ms")
        print(f"  最大响应时间: {max_time:.2f}ms")
        print(f"  中位数响应时间: {median_time:.2f}ms")
        
        # 判断是否达标
        target_ms = 10
        if avg_time < target_ms:
            print(f"\n✅ 测试通过：平均响应时间 {avg_time:.2f}ms < 目标 {target_ms}ms")
            return True
        else:
            print(f"\n❌ 测试失败：平均响应时间 {avg_time:.2f}ms >= 目标 {target_ms}ms")
            return False
    else:
        print("\n❌ 所有测试都失败")
        return False


def test_async_warmup_performance():
    """测试3：异步预热性能 < 3秒（10个大运并行）"""
    print("\n" + "="*80)
    print("测试3：异步预热性能（10个大运并行）")
    print("目标：< 3秒")
    print("="*80)
    
    # 使用唯一的测试数据
    test_id = int(time.time() * 1000) % 1000000
    solar_date = f"199{test_id % 10}-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 测试方法：并行计算10个大运
    print("\n  并行计算10个大运...")
    
    def warmup_dayun(dayun_idx: int):
        """预热单个大运"""
        try:
            result = compute_local_detail(
                solar_date, solar_time, gender,
                current_time=current_time,
                dayun_index=dayun_idx
            )
            # 验证结果
            if result and 'bazi_pillars' in result:
                return dayun_idx, True, None
            else:
                return dayun_idx, False, "返回结果为空或不完整"
        except Exception as e:
            return dayun_idx, False, str(e)
    
    start_time = time.time()
    
    # 并行计算10个大运
    executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="bazi_warmup_test")
    futures = []
    for dayun_index in range(10):
        future = executor.submit(warmup_dayun, dayun_index)
        futures.append(future)
    
    # 等待所有任务完成
    completed_count = 0
    failed_count = 0
    for future in as_completed(futures):
        dayun_idx, success, error = future.result()
        if success:
            completed_count += 1
            print(f"    ✅ 大运 {dayun_idx} 预热完成")
        else:
            failed_count += 1
            print(f"    ❌ 大运 {dayun_idx} 预热失败: {error}")
    
    elapsed_time = time.time() - start_time
    elapsed_ms = elapsed_time * 1000
    
    print(f"\n📊 预热结果：")
    print(f"  总耗时: {elapsed_ms:.2f}ms ({elapsed_time:.2f}秒)")
    print(f"  成功: {completed_count}/10")
    print(f"  失败: {failed_count}/10")
    
    # 判断是否达标
    target_seconds = 3
    if elapsed_time < target_seconds:
        print(f"\n✅ 测试通过：预热时间 {elapsed_time:.2f}秒 < 目标 {target_seconds}秒")
        return True
    else:
        print(f"\n❌ 测试失败：预热时间 {elapsed_time:.2f}秒 >= 目标 {target_seconds}秒")
        return False


def test_end_to_end_performance():
    """测试4：端到端性能（快速模式 + 异步预热）"""
    print("\n" + "="*80)
    print("测试4：端到端性能（快速模式 + 异步预热）")
    print("目标：首次响应 < 100ms，预热 < 3秒")
    print("="*80)
    
    # 使用唯一的测试数据
    test_id = int(time.time() * 1000) % 1000000
    solar_date = f"199{test_id % 10}-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 测试快速模式（只计算当前大运）
    print("\n  执行快速模式计算（只计算第一个大运）...")
    
    start_time = time.time()
    result, _ = compute_with_cache(
        solar_date, solar_time, gender,
        current_time=current_time,
        dayun_index=0,  # 快速模式：只计算第一个大运
        use_cache=False
    )
    first_response_time = (time.time() - start_time) * 1000
    
    print(f"  首次响应时间: {first_response_time:.2f}ms")
    
    # 验证返回数据
    assert result is not None, "返回结果不能为空"
    assert 'bazi_pillars' in result, "必须包含基础八字数据"
    
    print(f"  ✅ 数据完整性验证通过")
    
    # 测试异步预热（并行计算其余9个大运）
    print(f"\n  执行异步预热（并行计算其余9个大运）...")
    warmup_start = time.time()
    
    def warmup_dayun(dayun_idx: int):
        """预热单个大运"""
        try:
            compute_local_detail(
                solar_date, solar_time, gender,
                current_time=current_time,
                dayun_index=dayun_idx
            )
            return dayun_idx, True
        except Exception as e:
            return dayun_idx, False
    
    # 并行计算其余9个大运（索引1-9）
    executor = ThreadPoolExecutor(max_workers=9, thread_name_prefix="bazi_warmup_e2e")
    futures = []
    for dayun_index in range(1, 10):
        future = executor.submit(warmup_dayun, dayun_index)
        futures.append(future)
    
    # 等待所有任务完成
    completed_count = 0
    for future in as_completed(futures):
        dayun_idx, success = future.result()
        if success:
            completed_count += 1
    
    warmup_elapsed = time.time() - warmup_start
    
    print(f"  预热等待时间: {warmup_elapsed:.2f}秒")
    print(f"  已预热大运数: {completed_count}/9")
    
    # 判断是否达标
    first_response_ok = first_response_time < 100
    warmup_ok = warmup_elapsed < 3.0
    
    if first_response_ok and warmup_ok:
        print(f"\n✅ 测试通过：")
        print(f"  首次响应: {first_response_time:.2f}ms < 100ms ✅")
        print(f"  预热时间: {warmup_elapsed:.2f}秒 < 3秒 ✅")
        return True
    else:
        print(f"\n❌ 测试失败：")
        if not first_response_ok:
            print(f"  首次响应: {first_response_time:.2f}ms >= 100ms ❌")
        if not warmup_ok:
            print(f"  预热时间: {warmup_elapsed:.2f}秒 >= 3秒 ❌")
        return False


def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("统一接口性能测试（简化版）")
    print("="*80)
    print("\n测试目标：")
    print("  1. 首次响应 < 100ms（快速模式）")
    print("  2. 预热 < 3秒（10个大运并行）")
    print("  3. 缓存命中 < 10ms（内存缓存）")
    print("\n注意：此版本只测试核心计算功能，不依赖外部服务")
    print("="*80)
    
    results = {}
    
    # 测试1：首次响应性能
    try:
        results['first_response'] = test_first_response_performance()
    except Exception as e:
        print(f"\n❌ 测试1失败: {e}")
        import traceback
        traceback.print_exc()
        results['first_response'] = False
    
    # 测试2：缓存命中性能
    try:
        results['cache_hit'] = test_cache_hit_performance()
    except Exception as e:
        print(f"\n❌ 测试2失败: {e}")
        import traceback
        traceback.print_exc()
        results['cache_hit'] = False
    
    # 测试3：异步预热性能
    try:
        results['async_warmup'] = test_async_warmup_performance()
    except Exception as e:
        print(f"\n❌ 测试3失败: {e}")
        import traceback
        traceback.print_exc()
        results['async_warmup'] = False
    
    # 测试4：端到端性能
    try:
        results['end_to_end'] = test_end_to_end_performance()
    except Exception as e:
        print(f"\n❌ 测试4失败: {e}")
        import traceback
        traceback.print_exc()
        results['end_to_end'] = False
    
    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查性能指标")
        return 1


if __name__ == "__main__":
    exit(main())

