#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速API检查脚本 - 验证优化后的接口是否正常工作

使用方法：
1. 启动API服务
2. 运行此脚本检查接口是否正常响应
"""


import pytest
pytest.skip("独立脚本，使用自定义参数不兼容 pytest fixture 机制，请单独运行", allow_module_level=True)

import requests
import json
import time
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8000/api/v1"

# 测试用例
TEST_CASES = [
    {
        "name": "健康分析接口",
        "endpoint": "/health/stream",
        "method": "POST",
        "data": {
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male"
        }
    },
    {
        "name": "公式分析接口",
        "endpoint": "/bazi/formula-analysis",
        "method": "POST",
        "data": {
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male"
        }
    },
    {
        "name": "规则匹配接口",
        "endpoint": "/bazi/rules/match",
        "method": "POST",
        "data": {
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male",
            "include_bazi": True
        }
    },
]


def test_api_endpoint(name: str, endpoint: str, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    测试API接口
    
    Args:
        name: 接口名称
        endpoint: 接口路径
        method: HTTP方法
        data: 请求数据
        
    Returns:
        dict: 测试结果
    """
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    print(f"接口: {endpoint}")
    print(f"方法: {method}")
    print(f"数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        url = f"{BASE_URL}{endpoint}"
        
        # 第一次调用（缓存未命中）
        print("\n第一次调用（缓存未命中）...")
        start_time = time.time()
        if method == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            response = requests.get(url, params=data, timeout=30)
        time_1 = (time.time() - start_time) * 1000
        
        print(f"状态码: {response.status_code}")
        print(f"耗时: {time_1:.0f}ms")
        
        if response.status_code != 200:
            return {
                "success": False,
                "name": name,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }
        
        # 解析响应
        if endpoint.endswith("/stream"):
            # 流式接口，检查响应头
            content_type = response.headers.get("Content-Type", "")
            is_stream = "text/event-stream" in content_type
            print(f"响应类型: {content_type}")
            print(f"是否为流式: {is_stream}")
            result_1 = {"is_stream": is_stream, "content_length": len(response.content)}
        else:
            result_1 = response.json()
            print(f"响应数据: {json.dumps(result_1, ensure_ascii=False, indent=2)[:500]}...")
        
        # 第二次调用（缓存命中）
        print("\n第二次调用（缓存命中）...")
        start_time = time.time()
        if method == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            response = requests.get(url, params=data, timeout=30)
        time_2 = (time.time() - start_time) * 1000
        
        print(f"状态码: {response.status_code}")
        print(f"耗时: {time_2:.0f}ms")
        
        if response.status_code != 200:
            return {
                "success": False,
                "name": name,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }
        
        # 解析响应
        if endpoint.endswith("/stream"):
            result_2 = {"is_stream": True, "content_length": len(response.content)}
        else:
            result_2 = response.json()
        
        # 验证数据一致性
        print("\n验证数据一致性...")
        if endpoint.endswith("/stream"):
            is_consistent = result_1["content_length"] == result_2["content_length"]
        else:
            is_consistent = result_1 == result_2
        
        print(f"数据一致性: {'✅ 通过' if is_consistent else '❌ 失败'}")
        
        # 计算缓存效果
        cache_improvement = ((time_1 - time_2) / time_1 * 100) if time_1 > 0 else 0
        print(f"缓存效果: 性能提升 {cache_improvement:.1f}%")
        
        result = {
            "success": is_consistent and response.status_code == 200,
            "name": name,
            "endpoint": endpoint,
            "first_call_time_ms": time_1,
            "second_call_time_ms": time_2,
            "cache_improvement_percent": cache_improvement,
            "is_consistent": is_consistent,
            "status_code": response.status_code,
            "error": None
        }
        
        if result["success"]:
            print(f"\n✅ 测试通过")
        else:
            print(f"\n❌ 测试失败")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")
        return {
            "success": False,
            "name": name,
            "endpoint": endpoint,
            "error": str(e)
        }
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"\n❌ 测试失败: {e}\n{error_msg}")
        return {
            "success": False,
            "name": name,
            "endpoint": endpoint,
            "error": str(e),
            "traceback": error_msg
        }


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("快速API检查")
    print("="*60)
    print(f"API基础URL: {BASE_URL}")
    print("\n注意：请确保API服务已启动")
    
    # 测试结果
    results = []
    
    # 运行测试
    for test_case in TEST_CASES:
        result = test_api_endpoint(
            test_case["name"],
            test_case["endpoint"],
            test_case["method"],
            test_case["data"]
        )
        results.append(result)
    
    # 汇总结果
    print("\n\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    success_count = sum(1 for r in results if r.get("success"))
    total_count = len(results)
    
    print(f"\n总计: {success_count}/{total_count} 通过")
    
    for result in results:
        status = "✅" if result.get("success") else "❌"
        name = result.get("name", "未知")
        endpoint = result.get("endpoint", "未知")
        cache_improvement = result.get('cache_improvement_percent', 0)
        print(f"  {status} {name} ({endpoint}): 缓存提升={cache_improvement:.1f}%")
        if not result.get("success"):
            error = result.get("error", "未知错误")
            print(f"     错误: {error}")
    
    if success_count == total_count:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total_count - success_count} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

