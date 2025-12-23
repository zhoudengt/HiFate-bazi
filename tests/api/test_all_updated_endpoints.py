#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试所有更新后的接口
测试所有21个接口的新功能（农历输入、时区转换、向后兼容性）
"""

import sys
import os
import json
import time
from typing import Dict, Any, List, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from fastapi.testclient import TestClient
    from server.main import app
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    print("⚠️  无法导入 TestClient，将使用 HTTP 请求方式测试")
    try:
        import requests
        REQUESTS_AVAILABLE = True
        BASE_URL = "http://localhost:8001"
    except ImportError:
        REQUESTS_AVAILABLE = False
        print("⚠️  无法导入 requests，请安装依赖")


# 测试数据
BASE_REQUEST = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
}

LUNAR_REQUEST = {
    "solar_date": "2024年正月初一",
    "solar_time": "12:00",
    "gender": "male",
    "calendar_type": "lunar"
}

TIMEZONE_REQUEST = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "location": "德国"
}

COMBINED_REQUEST = {
    "solar_date": "2024年正月初一",
    "solar_time": "12:00",
    "gender": "male",
    "calendar_type": "lunar",
    "location": "德国"
}

# 所有需要测试的接口
ENDPOINTS = [
    # 排盘相关
    ("/api/v1/bazi/pan/display", "基本排盘", BASE_REQUEST),
    ("/api/v1/bazi/dayun/display", "大运展示", BASE_REQUEST),
    ("/api/v1/bazi/liunian/display", "流年展示", BASE_REQUEST),
    ("/api/v1/bazi/liuyue/display", "流月展示", BASE_REQUEST),
    ("/api/v1/bazi/fortune/display", "大运流年流月统一接口", BASE_REQUEST),
    
    # 分析相关
    ("/api/v1/bazi/wangshuai", "计算命局旺衰", BASE_REQUEST),
    ("/api/v1/bazi/formula-analysis", "算法公式规则分析", BASE_REQUEST),
    ("/api/v1/bazi/wuxing-proportion", "五行占比", BASE_REQUEST),
    ("/api/v1/bazi/rizhu-liujiazi", "日元-六十甲子", BASE_REQUEST),
    ("/api/v1/bazi/xishen-jishen", "喜神忌神", BASE_REQUEST),
    ("/api/v1/bazi/rules/match", "匹配八字规则", BASE_REQUEST),
    ("/api/v1/bazi/liunian-enhanced", "流年大运增强分析", BASE_REQUEST),
    ("/api/v1/bazi/ai-analyze", "Coze AI分析八字", BASE_REQUEST),
    
    # 运势相关
    ("/api/v1/bazi/monthly-fortune", "月运势", BASE_REQUEST),
    ("/api/v1/bazi/daily-fortune", "今日运势分析", BASE_REQUEST),
    ("/api/v1/daily-fortune-calendar/query", "每日运势日历", {"date": "2025-01-15", **BASE_REQUEST}),
    
    # 已支持接口（用于对比）
    ("/api/v1/bazi/calculate", "计算生辰八字", BASE_REQUEST),
    ("/api/v1/bazi/interface", "基本信息", BASE_REQUEST),
    ("/api/v1/bazi/detail", "详细八字信息", {**BASE_REQUEST, "current_time": "2025-01-15 10:00"}),
    ("/api/v1/bazi/shengong-minggong", "身宫命宫胎元", BASE_REQUEST),
]


class TestResult:
    """测试结果"""
    def __init__(self, name: str, success: bool, error: str = None, response_time: float = 0):
        self.name = name
        self.success = success
        self.error = error
        self.response_time = response_time


def test_endpoint(client, endpoint: str, name: str, request_data: Dict[str, Any]) -> TestResult:
    """测试单个接口"""
    start_time = time.time()
    try:
        if CLIENT_AVAILABLE:
            response = client.post(endpoint, json=request_data, timeout=30)
            status_code = response.status_code
            try:
                data = response.json()
            except:
                data = {"error": "响应不是有效的 JSON"}
        elif REQUESTS_AVAILABLE:
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json=request_data,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            status_code = response.status_code
            try:
                data = response.json()
            except:
                data = {"error": "响应不是有效的 JSON"}
        else:
            return TestResult(name, False, "测试客户端不可用", 0)
        
        response_time = time.time() - start_time
        
        if status_code == 200:
            if isinstance(data, dict) and data.get("success") is not False:
                return TestResult(name, True, None, response_time)
            else:
                error_msg = data.get("error", "success 字段为 False")
                return TestResult(name, False, error_msg, response_time)
        else:
            error_msg = f"状态码: {status_code}"
            if isinstance(data, dict) and "error" in data:
                error_msg += f", 错误: {data['error']}"
            return TestResult(name, False, error_msg, response_time)
            
    except Exception as e:
        response_time = time.time() - start_time
        return TestResult(name, False, str(e), response_time)


def test_endpoint_with_variants(client, endpoint: str, name: str) -> List[TestResult]:
    """测试接口的多种变体（基础、农历、时区、组合）"""
    results = []
    
    # 1. 基础测试（向后兼容）
    result = test_endpoint(client, endpoint, f"{name} - 基础（向后兼容）", BASE_REQUEST)
    results.append(result)
    
    # 2. 农历输入测试
    if endpoint not in ["/api/v1/daily-fortune-calendar/query"]:  # 某些接口可能不支持农历
        result = test_endpoint(client, endpoint, f"{name} - 农历输入", LUNAR_REQUEST)
        results.append(result)
    
    # 3. 时区转换测试
    result = test_endpoint(client, endpoint, f"{name} - 时区转换", TIMEZONE_REQUEST)
    results.append(result)
    
    # 4. 组合场景测试
    if endpoint not in ["/api/v1/daily-fortune-calendar/query"]:
        result = test_endpoint(client, endpoint, f"{name} - 农历+时区", COMBINED_REQUEST)
        results.append(result)
    
    return results


def run_all_tests():
    """运行所有测试"""
    print("=" * 80)
    print("全面测试所有更新后的接口")
    print("=" * 80)
    print()
    
    # 创建测试客户端
    if CLIENT_AVAILABLE:
        client = TestClient(app)
        print("✅ 使用 TestClient 进行测试")
    elif REQUESTS_AVAILABLE:
        client = None
        print(f"✅ 使用 HTTP 请求进行测试（BASE_URL: {BASE_URL}）")
        print("⚠️  请确保后端服务正在运行")
    else:
        print("❌ 无法创建测试客户端，请安装依赖")
        return
    
    print()
    
    all_results = []
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    # 测试所有接口
    for endpoint, name, base_request in ENDPOINTS:
        print(f"测试接口: {name} ({endpoint})")
        print("-" * 80)
        
        results = test_endpoint_with_variants(client, endpoint, name)
        all_results.extend(results)
        
        for result in results:
            total_tests += 1
            if result.success:
                passed_tests += 1
                print(f"  ✅ {result.name}: 通过 ({result.response_time:.2f}s)")
            else:
                failed_tests += 1
                print(f"  ❌ {result.name}: 失败 - {result.error}")
        
        print()
    
    # 汇总结果
    print("=" * 80)
    print("测试汇总")
    print("=" * 80)
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"失败: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
    print()
    
    # 失败的测试详情
    if failed_tests > 0:
        print("失败的测试:")
        print("-" * 80)
        for result in all_results:
            if not result.success:
                print(f"  ❌ {result.name}")
                print(f"     错误: {result.error}")
                print()
    
    # 性能统计
    response_times = [r.response_time for r in all_results if r.success]
    if response_times:
        print("性能统计:")
        print(f"  平均响应时间: {sum(response_times)/len(response_times):.2f}s")
        print(f"  最快: {min(response_times):.2f}s")
        print(f"  最慢: {max(response_times):.2f}s")
        print()
    
    return all_results


if __name__ == "__main__":
    results = run_all_tests()
    sys.exit(0 if all(r.success for r in results) else 1)

