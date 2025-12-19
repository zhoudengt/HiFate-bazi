#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动修复循环：持续测试直到问题解决
"""

import sys
import os
import json
import requests
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_production_api() -> dict:
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


def clear_cache():
    """清除缓存"""
    try:
        url = "http://8.210.52.217:8001/api/v1/hot-reload/check"
        requests.post(url, timeout=30)
        return True
    except:
        return False


def main():
    """主函数 - 持续测试直到问题解决"""
    print("="*80)
    print("🔄 自动修复循环：持续测试直到问题解决")
    print("="*80)
    
    # 目标：本地匹配 63 条，生产环境应该接近这个数量
    target_min = 50  # 允许一些差异
    
    iteration = 0
    max_iterations = 20  # 最多测试 20 次
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'='*80}")
        print(f"测试 #{iteration}/{max_iterations} ({time.strftime('%H:%M:%S')})")
        print(f"{'='*80}")
        
        # 每 5 次清除一次缓存
        if iteration % 5 == 0 and iteration > 1:
            print("🧹 清除缓存...")
            clear_cache()
            time.sleep(3)
        
        # 测试生产环境
        result = test_production_api()
        
        if not result['success']:
            print(f"❌ 测试失败: {result['error']}")
            time.sleep(10)
            continue
        
        stats = result['stats']
        total = stats.get('total_matched', 0)
        
        print(f"\n📊 当前匹配结果:")
        print(f"  总匹配数: {total} 条 (目标: {target_min}+ 条)")
        print(f"  财富: {stats.get('wealth_count', 0)}")
        print(f"  婚姻: {stats.get('marriage_count', 0)}")
        print(f"  事业: {stats.get('career_count', 0)} ⚠️")
        print(f"  身体: {stats.get('health_count', 0)}")
        print(f"  总评: {stats.get('summary_count', 0)}")
        
        # 判断是否解决
        if total >= target_min:
            print(f"\n{'='*80}")
            print("🎉 问题已解决！")
            print(f"{'='*80}")
            print(f"匹配数量: {total} 条 (目标: {target_min}+ 条)")
            print(f"\n详细统计:")
            for key, value in stats.items():
                if key.endswith('_count'):
                    print(f"  - {key}: {value}")
            break
        else:
            diff = target_min - total
            print(f"\n⚠️  仍需修复 (差异: {diff} 条)")
            
            if iteration == 1:
                print(f"\n💡 建议:")
                print(f"  1. 检查生产环境数据库规则数量")
                print(f"  2. 同步规则到生产环境")
                print(f"  3. 清除缓存")
                print(f"\n执行修复:")
                print(f"  bash scripts/check_and_fix_production_db.sh")
                print(f"\n或手动执行:")
                print(f"  scp scripts/temp_rules_export.sql root@8.210.52.217:/tmp/rules_import.sql")
                print(f"  ssh root@8.210.52.217 'docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql'")
                print(f"  curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check")
        
        # 等待
        if iteration < max_iterations:
            print(f"\n⏳ 等待 10 秒后继续测试...")
            time.sleep(10)
    
    if iteration >= max_iterations:
        print(f"\n⚠️  已达到最大测试次数 ({max_iterations})，停止测试")
        print(f"💡 请手动执行修复步骤后，再次运行此脚本验证")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试已停止")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

