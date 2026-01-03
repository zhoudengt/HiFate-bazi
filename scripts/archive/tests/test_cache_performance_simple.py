#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大运流年查询性能测试脚本（简化版）
直接测试缓存逻辑，不依赖完整的服务导入
"""

import sys
import os
import time
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def test_cache_system():
    """测试缓存系统"""
    print("\n" + "="*80)
    print("测试：多级缓存系统性能")
    print("="*80)
    
    try:
        from server.utils.cache_multi_level import get_multi_cache
        cache = get_multi_cache()
        
        # 测试数据
        test_key = "test:bazi_detail:1990-05-15:14:30:male:default:all:all"
        test_value = {
            "test": "data",
            "timestamp": datetime.now().isoformat(),
            "large_data": "x" * 10000  # 10KB 数据
        }
        
        # 测试 1: 写入缓存
        print("\n📊 测试 1: 写入缓存...")
        start_time = time.time()
        cache.set(test_key, test_value)
        write_time = time.time() - start_time
        print(f"   耗时: {write_time*1000:.2f}ms")
        
        # 测试 2: L1 缓存读取（内存）
        print("\n📊 测试 2: L1 缓存读取（内存）...")
        start_time = time.time()
        result1 = cache.get(test_key)
        l1_read_time = time.time() - start_time
        print(f"   耗时: {l1_read_time*1000:.2f}ms")
        print(f"   结果: {'成功' if result1 else '失败'}")
        
        # 测试 3: L2 缓存读取（Redis，如果可用）
        print("\n📊 测试 3: L2 缓存读取（Redis）...")
        # 先清空 L1 缓存，强制从 L2 读取
        cache.l1.clear()
        start_time = time.time()
        result2 = cache.get(test_key)
        l2_read_time = time.time() - start_time
        print(f"   耗时: {l2_read_time*1000:.2f}ms")
        print(f"   结果: {'成功' if result2 else '失败'}")
        print(f"   Redis 状态: {'可用' if cache.l2._available else '不可用'}")
        
        # 测试 4: 缓存统计
        print("\n📊 测试 4: 缓存统计...")
        stats = cache.stats()
        print(f"   L1 缓存: {stats.get('l1', {})}")
        print(f"   L2 缓存: {stats.get('l2', {})}")
        
        return {
            'write_time': write_time,
            'l1_read_time': l1_read_time,
            'l2_read_time': l2_read_time,
            'redis_available': cache.l2._available
        }
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_cache_key_generation():
    """测试缓存键生成"""
    print("\n" + "="*80)
    print("测试：缓存键生成")
    print("="*80)
    
    try:
        from server.services.bazi_detail_service import BaziDetailService
        
        # 模拟缓存键生成逻辑
        solar_date = "1990-05-15"
        solar_time = "14:30"
        gender = "male"
        current_time = datetime.now()
        current_time_iso = current_time.isoformat()
        dayun_index = None
        target_year = None
        
        cache_key_parts = [
            'bazi_detail',
            solar_date,
            solar_time,
            gender,
            current_time_iso or 'default',
            str(dayun_index) if dayun_index is not None else 'all',
            str(target_year) if target_year is not None else 'all'
        ]
        cache_key = ':'.join(cache_key_parts)
        
        print(f"\n📊 缓存键示例:")
        print(f"   键: {cache_key}")
        print(f"   长度: {len(cache_key)} 字符")
        
        return cache_key
        
    except Exception as e:
        print(f"⚠️  无法测试缓存键生成（可能缺少依赖）: {e}")
        return None


def main():
    """主函数"""
    print("\n" + "="*80)
    print("大运流年查询性能测试（简化版）")
    print("="*80)
    
    results = {}
    
    # 测试缓存系统
    try:
        results['cache'] = test_cache_system()
    except Exception as e:
        print(f"❌ 缓存系统测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试缓存键生成
    try:
        results['cache_key'] = test_cache_key_generation()
    except Exception as e:
        print(f"⚠️  缓存键生成测试失败: {e}")
    
    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    if results.get('cache'):
        r = results['cache']
        print(f"\n✅ 缓存系统性能:")
        print(f"   写入耗时: {r['write_time']*1000:.2f}ms")
        print(f"   L1 读取耗时: {r['l1_read_time']*1000:.2f}ms")
        print(f"   L2 读取耗时: {r['l2_read_time']*1000:.2f}ms")
        print(f"   Redis 状态: {'可用' if r['redis_available'] else '不可用'}")
        
        if r['l1_read_time'] > 0 and r['l2_read_time'] > 0:
            speedup = r['l2_read_time'] / r['l1_read_time'] if r['l1_read_time'] > 0 else 0
            print(f"   L1 vs L2 速度比: {speedup:.2f}倍")
    
    if results.get('cache_key'):
        print(f"\n✅ 缓存键生成:")
        print(f"   键: {results['cache_key'][:80]}...")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)
    print("\n💡 提示：要测试完整的服务性能，请确保：")
    print("   1. Redis 服务已启动")
    print("   2. 所有依赖已安装（pip install -r requirements.txt）")
    print("   3. 运行完整测试：python3 test_dayun_liunian_performance.py")


if __name__ == '__main__':
    main()

