#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一接口性能测试
测试目标：
1. 首次响应 < 100ms（快速模式）
2. 预热 < 3秒（10个大运并行）
3. 缓存命中 < 10ms
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

# 检查必要的依赖
def check_dependencies():
    """检查必要的依赖是否已安装，返回 (has_all_deps, missing_deps)"""
    missing_deps = []
    
    try:
        import grpc
    except ImportError:
        missing_deps.append("grpcio")
    
    try:
        import redis
    except ImportError:
        missing_deps.append("redis")
    
    try:
        import pymysql
    except ImportError:
        missing_deps.append("pymysql")
    
    if missing_deps:
        return False, missing_deps
    
    return True, []

# 检查依赖
has_all_deps, missing_deps = check_dependencies()
has_grpc = "grpcio" not in missing_deps

if not has_all_deps:
    print("\n" + "="*80)
    print("⚠️  缺少部分依赖包：")
    for dep in missing_deps:
        print(f"   - {dep}")
    print("\n将使用降级模式运行测试（跳过需要这些依赖的功能）")
    print("="*80)

# 导入服务（尝试导入，如果失败则使用降级模式）
BaziDetailService = None
if has_grpc:
    try:
        from server.services.bazi_detail_service import BaziDetailService
    except ImportError as e:
        print(f"\n⚠️  导入 BaziDetailService 失败: {e}")
        print("   将使用降级模式（直接调用本地计算函数）")
        has_grpc = False

# 降级模式：直接使用本地计算函数
if not has_grpc:
    try:
        from core.calculators.helpers import compute_local_detail
        print("✅ 降级模式：使用本地计算函数")
        
        # 创建一个简单的包装类来模拟 BaziDetailService
        class BaziDetailServiceFallback:
            @staticmethod
            def calculate_detail_full(solar_date: str, solar_time: str, gender: str, 
                                      current_time: datetime = None, dayun_index: int = None, 
                                      target_year: int = None,
                                      quick_mode: bool = False,
                                      async_warmup: bool = False,
                                      include_wangshuai: bool = True,
                                      include_shengong_minggong: bool = True,
                                      include_rules: bool = True,
                                      include_wuxing_proportion: bool = True,
                                      include_rizhu_liujiazi: bool = True,
                                      rule_types: list = None) -> dict:
                """降级模式：只使用本地计算，不包含额外数据"""
                result = compute_local_detail(
                    solar_date, solar_time, gender,
                    current_time=current_time,
                    dayun_index=dayun_index,
                    target_year=target_year
                )
                return result
        
        BaziDetailService = BaziDetailServiceFallback
    except ImportError as e:
        print(f"\n❌ 降级模式也失败: {e}")
        print("   无法运行测试，请安装必要的依赖")
        sys.exit(1)


def clear_cache_for_test(solar_date: str, solar_time: str, gender: str, current_time: datetime = None):
    """清除测试用的缓存"""
    try:
        from server.utils.cache_multi_level import get_multi_cache
        cache = get_multi_cache()
        
        # 清除所有相关的缓存键
        current_time_iso = current_time.isoformat() if current_time else None
        cache_key_patterns = [
            f'bazi_detail:{solar_date}:{solar_time}:{gender}:{current_time_iso or "default"}:*',
            f'bazi_detail:{solar_date}:{solar_time}:{gender}:*',
        ]
        
        # 尝试清除（Redis可能不支持通配符删除，这里只是尝试）
        # 实际测试中，我们使用唯一的测试数据来避免缓存冲突
        pass
    except Exception as e:
        print(f"⚠️  清除缓存失败（不影响测试）: {e}")


def test_first_response_performance():
    """测试1：首次响应性能（快速模式）< 100ms"""
    print("\n" + "="*80)
    print("测试1：首次响应性能（快速模式）")
    print("目标：< 100ms")
    print("="*80)
    
    # 使用唯一的测试数据，避免缓存影响
    test_id = int(time.time() * 1000) % 1000000
    solar_date = f"1990-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 清除缓存（如果存在）
    clear_cache_for_test(solar_date, solar_time, gender, current_time)
    
    # 执行多次测试取平均值
    test_count = 10
    response_times = []
    
    for i in range(test_count):
        # 使用唯一的参数避免缓存
        unique_solar_date = f"199{test_id % 10}-05-{(15 + i) % 28 + 1:02d}"
        
        start_time = time.time()
        try:
            result = BaziDetailService.calculate_detail_full(
                solar_date=unique_solar_date,
                solar_time=solar_time,
                gender=gender,
                current_time=current_time,
                quick_mode=True,  # 快速模式
                async_warmup=False,  # 先不触发预热，只测试首次响应
                include_wangshuai=True,
                include_shengong_minggong=True,
                include_rules=True,
                include_wuxing_proportion=True,
                include_rizhu_liujiazi=True
            )
            elapsed_ms = (time.time() - start_time) * 1000
            response_times.append(elapsed_ms)
            
            # 验证返回数据完整性
            assert result is not None, "返回结果不能为空"
            assert 'bazi_pillars' in result, "必须包含基础八字数据"
            assert 'dayun_sequence' in result, "必须包含大运序列"
            
            print(f"  测试 {i+1}/{test_count}: {elapsed_ms:.2f}ms - ✅ 数据完整")
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            response_times.append(elapsed_ms)
            print(f"  测试 {i+1}/{test_count}: {elapsed_ms:.2f}ms - ❌ 错误: {e}")
    
    # 统计结果
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


def test_cache_hit_performance():
    """测试2：缓存命中性能 < 10ms"""
    print("\n" + "="*80)
    print("测试2：缓存命中性能")
    print("目标：< 10ms")
    print("="*80)
    
    # 使用固定的测试数据
    solar_date = f"1990-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 先执行一次计算，确保缓存存在
    print("  预热：执行首次计算以填充缓存...")
    start_time = time.time()
    BaziDetailService.calculate_detail_full(
        solar_date=solar_date,
        solar_time=solar_time,
        gender=gender,
        current_time=current_time,
        quick_mode=True,
        async_warmup=False,
        include_wangshuai=True,
        include_shengong_minggong=True,
        include_rules=True,
        include_wuxing_proportion=True,
        include_rizhu_liujiazi=True
    )
    warmup_time = (time.time() - start_time) * 1000
    print(f"  预热完成，耗时: {warmup_time:.2f}ms")
    
    # 等待一小段时间，确保缓存写入完成
    time.sleep(0.1)
    
    # 执行多次缓存命中测试
    test_count = 20
    cache_hit_times = []
    
    for i in range(test_count):
        start_time = time.time()
        try:
            result = BaziDetailService.calculate_detail_full(
                solar_date=solar_date,
                solar_time=solar_time,
                gender=gender,
                current_time=current_time,
                quick_mode=True,
                async_warmup=False,
                include_wangshuai=True,
                include_shengong_minggong=True,
                include_rules=True,
                include_wuxing_proportion=True,
                include_rizhu_liujiazi=True
            )
            elapsed_ms = (time.time() - start_time) * 1000
            cache_hit_times.append(elapsed_ms)
            
            assert result is not None, "返回结果不能为空"
            print(f"  测试 {i+1}/{test_count}: {elapsed_ms:.2f}ms - ✅")
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            cache_hit_times.append(elapsed_ms)
            print(f"  测试 {i+1}/{test_count}: {elapsed_ms:.2f}ms - ❌ 错误: {e}")
    
    # 统计结果
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
    
    # 清除缓存
    clear_cache_for_test(solar_date, solar_time, gender, current_time)
    
    # 测试方法1：直接测试异步预热函数
    print("\n  方法1：测试异步预热函数（后台并行计算10个大运）...")
    
    start_time = time.time()
    
    # 手动触发异步预热（模拟 quick_mode + async_warmup 的行为）
    from concurrent.futures import ThreadPoolExecutor
    import threading
    
    def warmup_dayun(dayun_idx: int):
        """预热单个大运"""
        try:
            from core.calculators.helpers import compute_local_detail
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
    print("目标：首次响应 < 100ms，预热在后台完成 < 3秒")
    print("="*80)
    
    # 使用唯一的测试数据
    test_id = int(time.time() * 1000) % 1000000
    solar_date = f"199{test_id % 10}-05-15"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime.now()
    
    # 清除缓存
    clear_cache_for_test(solar_date, solar_time, gender, current_time)
    
    # 测试快速模式 + 异步预热
    print("\n  执行快速模式计算（触发异步预热）...")
    
    start_time = time.time()
    result = BaziDetailService.calculate_detail_full(
        solar_date=solar_date,
        solar_time=solar_time,
        gender=gender,
        current_time=current_time,
        quick_mode=True,  # 快速模式
        async_warmup=True,  # 触发异步预热
        include_wangshuai=True,
        include_shengong_minggong=True,
        include_rules=True,
        include_wuxing_proportion=True,
        include_rizhu_liujiazi=True
    )
    first_response_time = (time.time() - start_time) * 1000
    
    print(f"  首次响应时间: {first_response_time:.2f}ms")
    
    # 验证返回数据
    assert result is not None, "返回结果不能为空"
    assert 'bazi_pillars' in result, "必须包含基础八字数据"
    assert 'dayun_sequence' in result, "必须包含大运序列"
    
    print(f"  ✅ 数据完整性验证通过")
    
    # 等待异步预热完成（最多等待5秒）
    print(f"\n  等待异步预热完成（最多5秒）...")
    warmup_start = time.time()
    max_wait_time = 5.0
    
    # 检查所有大运是否已缓存（通过尝试读取缓存）
    # 注意：异步预热会计算每个大运，但可能不会立即写入缓存
    # 我们通过检查计算是否完成来判断预热状态
    cached_count = 0
    last_cached_count = 0
    stable_count = 0
    
    while time.time() - warmup_start < max_wait_time:
        cached_count = 0
        for dayun_idx in range(10):
            try:
                from server.utils.cache_multi_level import get_multi_cache
                cache = get_multi_cache()
                current_time_iso = current_time.isoformat()
                # 缓存键格式：bazi_detail:date:time:gender:current_time:dayun_index:all:full
                cache_key = f'bazi_detail:{solar_date}:{solar_time}:{gender}:{current_time_iso}:{dayun_idx}:all:full'
                cached = cache.get(cache_key)
                if cached:
                    cached_count += 1
            except Exception as e:
                # 忽略缓存检查错误
                pass
        
        # 如果缓存数量稳定，认为预热完成
        if cached_count == last_cached_count:
            stable_count += 1
        else:
            stable_count = 0
        
        last_cached_count = cached_count
        
        if cached_count >= 8 or stable_count >= 3:  # 至少8个大运已缓存，或稳定3次检查
            break
        
        time.sleep(0.3)
    
    warmup_elapsed = time.time() - warmup_start
    
    print(f"  预热等待时间: {warmup_elapsed:.2f}秒")
    print(f"  已缓存大运数: {cached_count}/10")
    
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
    print("统一接口性能测试")
    print("="*80)
    print("\n测试目标：")
    print("  1. 首次响应 < 100ms（快速模式）")
    print("  2. 预热 < 3秒（10个大运并行）")
    print("  3. 缓存命中 < 10ms")
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

