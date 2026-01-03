#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试缓存性能（不通过API）
测试 BaziDetailService 和 SpecialLiunianService 的缓存效果
"""

import sys
import os
import time
import asyncio
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置环境变量，避免 gRPC 调用
os.environ['BAZI_FORTUNE_SERVICE_URL'] = ''


def test_bazi_detail_cache():
    """测试 BaziDetailService 缓存"""
    print("\n" + "="*80)
    print("测试 1: BaziDetailService.calculate_detail_full() 缓存性能")
    print("="*80)
    
    try:
        from server.services.bazi_detail_service import BaziDetailService
        
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
        first_time = time.time() - start_time
        print(f"   耗时: {first_time:.3f}秒")
        print(f"   结果: {'成功' if result1 else '失败'}")
        if result1:
            dayun_count = len(result1.get('dayun_sequence', []))
            liunian_count = len(result1.get('liunian_sequence', []))
            print(f"   大运数量: {dayun_count}")
            print(f"   流年数量: {liunian_count}")
        
        # 第二次查询（缓存命中）
        print("\n📊 第二次查询（缓存命中）...")
        start_time = time.time()
        result2 = BaziDetailService.calculate_detail_full(
            solar_date, solar_time, gender, current_time
        )
        second_time = time.time() - start_time
        print(f"   耗时: {second_time:.3f}秒")
        print(f"   结果: {'成功' if result2 else '失败'}")
        
        # 性能提升
        if first_time > 0 and second_time > 0:
            speedup = first_time / second_time
            print(f"\n✅ 性能提升: {speedup:.2f}倍")
            print(f"   首次查询: {first_time:.3f}秒")
            print(f"   缓存命中: {second_time:.3f}秒")
            print(f"   节省时间: {first_time - second_time:.3f}秒")
            return {
                'first_time': first_time,
                'second_time': second_time,
                'speedup': speedup
            }
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_special_liunian_cache():
    """测试 SpecialLiunianService 缓存"""
    print("\n" + "="*80)
    print("测试 2: SpecialLiunianService.get_special_liunians_batch() 缓存性能")
    print("="*80)
    
    try:
        from server.services.bazi_detail_service import BaziDetailService
        from server.services.special_liunian_service import SpecialLiunianService
        
        solar_date = "1990-05-15"
        solar_time = "14:30"
        gender = "male"
        current_time = datetime.now()
        
        # 先获取大运序列
        print("\n📊 获取大运序列...")
        detail_result = BaziDetailService.calculate_detail_full(
            solar_date, solar_time, gender, current_time
        )
        dayun_sequence = detail_result.get('dayun_sequence', [])
        print(f"   大运数量: {len(dayun_sequence)}")
        
        if not dayun_sequence:
            print("❌ 无法获取大运序列，跳过测试")
            return None
        
        # 首次查询（缓存未命中）
        print("\n📊 首次查询（缓存未命中）...")
        start_time = time.time()
        result1 = await SpecialLiunianService.get_special_liunians_batch(
            solar_date, solar_time, gender, dayun_sequence, dayun_count=13, current_time=current_time
        )
        first_time = time.time() - start_time
        print(f"   耗时: {first_time:.3f}秒")
        print(f"   特殊流年数量: {len(result1) if result1 else 0}")
        
        # 第二次查询（缓存命中）
        print("\n📊 第二次查询（缓存命中）...")
        start_time = time.time()
        result2 = await SpecialLiunianService.get_special_liunians_batch(
            solar_date, solar_time, gender, dayun_sequence, dayun_count=13, current_time=current_time
        )
        second_time = time.time() - start_time
        print(f"   耗时: {second_time:.3f}秒")
        print(f"   特殊流年数量: {len(result2) if result2 else 0}")
        
        # 性能提升
        if first_time > 0 and second_time > 0:
            speedup = first_time / second_time
            print(f"\n✅ 性能提升: {speedup:.2f}倍")
            print(f"   首次查询: {first_time:.3f}秒")
            print(f"   缓存命中: {second_time:.3f}秒")
            print(f"   节省时间: {first_time - second_time:.3f}秒")
            return {
                'first_time': first_time,
                'second_time': second_time,
                'speedup': speedup,
                'count': len(result1) if result1 else 0
            }
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    print("\n" + "="*80)
    print("大运流年查询缓存性能测试（直接测试服务层）")
    print("="*80)
    
    results = {}
    
    # 测试 1: BaziDetailService
    try:
        results['bazi_detail'] = test_bazi_detail_cache()
    except Exception as e:
        print(f"❌ 测试 1 失败: {e}")
    
    # 测试 2: SpecialLiunianService
    try:
        results['special_liunian'] = asyncio.run(test_special_liunian_cache())
    except Exception as e:
        print(f"❌ 测试 2 失败: {e}")
    
    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    if results.get('bazi_detail'):
        r = results['bazi_detail']
        print(f"\n✅ BaziDetailService 缓存性能:")
        print(f"   首次查询: {r['first_time']:.3f}秒")
        print(f"   缓存命中: {r['second_time']:.3f}秒")
        print(f"   性能提升: {r['speedup']:.2f}倍")
        print(f"   节省时间: {r['first_time'] - r['second_time']:.3f}秒")
    
    if results.get('special_liunian'):
        r = results['special_liunian']
        print(f"\n✅ SpecialLiunianService 缓存性能:")
        print(f"   首次查询: {r['first_time']:.3f}秒")
        print(f"   缓存命中: {r['second_time']:.3f}秒")
        print(f"   性能提升: {r['speedup']:.2f}倍")
        print(f"   节省时间: {r['first_time'] - r['second_time']:.3f}秒")
        print(f"   特殊流年数量: {r['count']}")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)
    
    # 性能评估
    if results.get('bazi_detail') and results.get('special_liunian'):
        bazi_speedup = results['bazi_detail']['speedup']
        liunian_speedup = results['special_liunian']['speedup']
        avg_speedup = (bazi_speedup + liunian_speedup) / 2
        
        print(f"\n📊 总体性能评估:")
        print(f"   平均性能提升: {avg_speedup:.2f}倍")
        if avg_speedup > 10:
            print(f"   ✅ 缓存优化效果显著！")
        elif avg_speedup > 5:
            print(f"   ✅ 缓存优化效果良好")
        elif avg_speedup > 2:
            print(f"   ✅ 缓存优化有效")
        else:
            print(f"   ⚠️  缓存优化效果有限，可能需要进一步优化")


if __name__ == '__main__':
    main()

