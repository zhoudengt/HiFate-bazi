#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大运流年查询 API 性能测试
通过 HTTP API 测试实际性能（包括缓存效果）
"""

import sys
import os
import time
import requests
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def test_api_performance(base_url="http://localhost:8001"):
    """测试 API 性能"""
    print("\n" + "="*80)
    print("测试：大运流年查询 API 性能")
    print("="*80)
    
    # 测试数据
    test_data = {
        "solar_date": "1990-05-15",
        "solar_time": "14:30",
        "gender": "male"
    }
    
    # 测试接口列表
    test_endpoints = [
        {
            "name": "八字计算",
            "url": f"{base_url}/api/v1/bazi/calculate",
            "method": "POST"
        },
        {
            "name": "公式分析（包含大运流年）",
            "url": f"{base_url}/api/v1/bazi/formula-analysis",
            "method": "POST"
        },
        {
            "name": "总评分析（包含大运流年）",
            "url": f"{base_url}/api/v1/general-review-analysis/stream",
            "method": "POST"
        }
    ]
    
    results = {}
    
    for endpoint in test_endpoints:
        print(f"\n{'='*80}")
        print(f"测试接口: {endpoint['name']}")
        print(f"URL: {endpoint['url']}")
        print(f"{'='*80}")
        
        # 首次查询（缓存未命中）
        print("\n📊 首次查询（缓存未命中）...")
        try:
            start_time = time.time()
            if endpoint['method'] == 'POST':
                response = requests.post(
                    endpoint['url'],
                    json=test_data,
                    timeout=60
                )
            else:
                response = requests.get(endpoint['url'], timeout=60)
            
            first_query_time = time.time() - start_time
            status_code = response.status_code
            
            print(f"   耗时: {first_query_time:.3f}秒")
            print(f"   状态码: {status_code}")
            print(f"   响应大小: {len(response.content)} 字节")
            
            if status_code == 200:
                # 第二次查询（缓存命中）
                print("\n📊 第二次查询（缓存命中）...")
                start_time = time.time()
                if endpoint['method'] == 'POST':
                    response2 = requests.post(
                        endpoint['url'],
                        json=test_data,
                        timeout=60
                    )
                else:
                    response2 = requests.get(endpoint['url'], timeout=60)
                
                second_query_time = time.time() - start_time
                status_code2 = response2.status_code
                
                print(f"   耗时: {second_query_time:.3f}秒")
                print(f"   状态码: {status_code2}")
                print(f"   响应大小: {len(response2.content)} 字节")
                
                # 性能提升
                if first_query_time > 0 and second_query_time > 0:
                    speedup = first_query_time / second_query_time
                    print(f"\n✅ 性能提升: {speedup:.2f}倍")
                    print(f"   首次查询: {first_query_time:.3f}秒")
                    print(f"   缓存命中: {second_query_time:.3f}秒")
                    print(f"   节省时间: {first_query_time - second_query_time:.3f}秒")
                
                results[endpoint['name']] = {
                    'first_query_time': first_query_time,
                    'second_query_time': second_query_time,
                    'speedup': speedup if first_query_time > 0 and second_query_time > 0 else 0,
                    'status': 'success'
                }
            else:
                print(f"   ⚠️  请求失败，状态码: {status_code}")
                results[endpoint['name']] = {
                    'status': 'failed',
                    'status_code': status_code
                }
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ 无法连接到服务器: {base_url}")
            print(f"   💡 提示: 请确保服务已启动 (python3 server/start.py)")
            results[endpoint['name']] = {
                'status': 'connection_error'
            }
        except requests.exceptions.Timeout:
            print(f"   ⚠️  请求超时（>60秒）")
            results[endpoint['name']] = {
                'status': 'timeout'
            }
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results[endpoint['name']] = {
                'status': 'error',
                'error': str(e)
            }
    
    return results


def main():
    """主函数"""
    print("\n" + "="*80)
    print("大运流年查询 API 性能测试")
    print("="*80)
    
    # 测试本地服务
    base_url = "http://localhost:8001"
    print(f"\n测试目标: {base_url}")
    print("💡 提示: 如果服务未启动，请先运行: python3 server/start.py")
    
    results = test_api_performance(base_url)
    
    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    success_count = sum(1 for r in results.values() if r.get('status') == 'success')
    total_count = len(results)
    
    print(f"\n✅ 成功测试: {success_count}/{total_count}")
    
    for name, result in results.items():
        if result.get('status') == 'success':
            print(f"\n📊 {name}:")
            print(f"   首次查询: {result['first_query_time']:.3f}秒")
            print(f"   缓存命中: {result['second_query_time']:.3f}秒")
            print(f"   性能提升: {result['speedup']:.2f}倍")
        elif result.get('status') == 'connection_error':
            print(f"\n⚠️  {name}: 无法连接到服务器")
        elif result.get('status') == 'timeout':
            print(f"\n⚠️  {name}: 请求超时")
        else:
            print(f"\n❌ {name}: {result.get('status', 'unknown')}")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == '__main__':
    main()

