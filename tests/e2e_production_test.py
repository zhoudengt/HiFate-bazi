#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境端到端测试脚本
覆盖所有关键接口，确保部署后功能正常

使用方法：
    python3 tests/e2e_production_test.py [--node1-url URL] [--node2-url URL]
    
示例：
    python3 tests/e2e_production_test.py --node1-url http://8.210.52.217:8001 --node2-url http://47.243.160.43:8001
"""

import sys
import os
import json
import time
import argparse
import requests
from typing import Dict, List, Tuple
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 默认配置
DEFAULT_NODE1_URL = "http://8.210.52.217:8001"
DEFAULT_NODE2_URL = "http://47.243.160.43:8001"
TIMEOUT = 30  # 请求超时时间（秒）

# 测试数据
TEST_BAZI_DATA = {
    "solar_date": "1990-01-15",
    "solar_time": "12:00",
    "gender": "male"
}

TEST_BAZI_DATA_FEMALE = {
    "solar_date": "1995-05-20",
    "solar_time": "14:30",
    "gender": "female"
}


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class E2ETestResult:
    """测试结果"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors: List[Tuple[str, str]] = []
    
    def add_test(self, name: str, passed: bool, error: str = None):
        self.total += 1
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            if error:
                self.errors.append((name, error))
    
    def print_summary(self):
        print("\n" + "=" * 80)
        print(f"{Colors.BOLD}测试结果汇总{Colors.RESET}")
        print("=" * 80)
        print(f"总测试数: {self.total}")
        print(f"{Colors.GREEN}通过: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}失败: {self.failed}{Colors.RESET}")
        print(f"成功率: {self.passed / self.total * 100:.1f}%")
        
        if self.errors:
            print(f"\n{Colors.RED}失败的测试:{Colors.RESET}")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        
        print("=" * 80)
        return self.failed == 0


def test_endpoint(
    name: str,
    url: str,
    method: str = "GET",
    data: Dict = None,
    expected_status: int = 200,
    expected_keys: List[str] = None,
    timeout: int = TIMEOUT
) -> Tuple[bool, str]:
    """
    测试单个端点
    
    Returns:
        (success, error_message)
    """
    try:
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout, headers={"Content-Type": "application/json"})
        else:
            return False, f"不支持的 HTTP 方法: {method}"
        
        if response.status_code != expected_status:
            return False, f"状态码错误: 期望 {expected_status}, 实际 {response.status_code}"
        
        if expected_keys:
            try:
                json_data = response.json()
                for key in expected_keys:
                    if key not in json_data:
                        return False, f"响应中缺少字段: {key}"
            except json.JSONDecodeError:
                return False, "响应不是有效的 JSON"
        
        return True, ""
    
    except requests.exceptions.Timeout:
        return False, f"请求超时（>{timeout}秒）"
    except requests.exceptions.ConnectionError:
        return False, "连接错误，服务可能未启动"
    except Exception as e:
        return False, f"异常: {str(e)}"


def test_health_check(base_url: str, result: E2ETestResult):
    """测试健康检查接口"""
    print(f"\n{Colors.BLUE}测试健康检查接口{Colors.RESET}")
    
    # 基本健康检查
    success, error = test_endpoint(
        "健康检查 (/)",
        f"{base_url}/health",
        expected_keys=["status"]
    )
    result.add_test("健康检查 (/)", success, error)
    print(f"  {'✅' if success else '❌'} 健康检查 (/): {'通过' if success else error}")
    
    # API 健康检查
    success, error = test_endpoint(
        "健康检查 (/api/v1/health)",
        f"{base_url}/api/v1/health",
        expected_keys=["status"]
    )
    result.add_test("健康检查 (/api/v1/health)", success, error)
    print(f"  {'✅' if success else '❌'} 健康检查 (/api/v1/health): {'通过' if success else error}")


def test_bazi_calculate(base_url: str, result: E2ETestResult):
    """测试八字计算接口"""
    print(f"\n{Colors.BLUE}测试八字计算接口{Colors.RESET}")
    
    # 男性八字计算
    success, error = test_endpoint(
        "八字计算 (男性)",
        f"{base_url}/api/v1/bazi/calculate",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success", "data"]
    )
    result.add_test("八字计算 (男性)", success, error)
    print(f"  {'✅' if success else '❌'} 八字计算 (男性): {'通过' if success else error}")
    
    # 女性八字计算
    success, error = test_endpoint(
        "八字计算 (女性)",
        f"{base_url}/api/v1/bazi/calculate",
        method="POST",
        data=TEST_BAZI_DATA_FEMALE,
        expected_keys=["success", "data"]
    )
    result.add_test("八字计算 (女性)", success, error)
    print(f"  {'✅' if success else '❌'} 八字计算 (女性): {'通过' if success else error}")


def test_formula_analysis(base_url: str, result: E2ETestResult):
    """测试公式分析接口"""
    print(f"\n{Colors.BLUE}测试公式分析接口{Colors.RESET}")
    
    success, error = test_endpoint(
        "公式分析",
        f"{base_url}/api/v1/bazi/formula-analysis",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success", "data"]
    )
    result.add_test("公式分析", success, error)
    print(f"  {'✅' if success else '❌'} 公式分析: {'通过' if success else error}")


def test_monthly_fortune(base_url: str, result: E2ETestResult):
    """测试月运势接口"""
    print(f"\n{Colors.BLUE}测试月运势接口{Colors.RESET}")
    
    success, error = test_endpoint(
        "月运势",
        f"{base_url}/api/v1/bazi/monthly-fortune",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success", "data"]
    )
    result.add_test("月运势", success, error)
    print(f"  {'✅' if success else '❌'} 月运势: {'通过' if success else error}")


def test_daily_fortune(base_url: str, result: E2ETestResult):
    """测试日运势接口"""
    print(f"\n{Colors.BLUE}测试日运势接口{Colors.RESET}")
    
    success, error = test_endpoint(
        "日运势",
        f"{base_url}/api/v1/bazi/daily-fortune",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success", "data"]
    )
    result.add_test("日运势", success, error)
    print(f"  {'✅' if success else '❌'} 日运势: {'通过' if success else error}")


def test_shengong_minggong(base_url: str, result: E2ETestResult):
    """测试身宫命宫接口"""
    print(f"\n{Colors.BLUE}测试身宫命宫接口{Colors.RESET}")
    
    success, error = test_endpoint(
        "身宫命宫",
        f"{base_url}/api/v1/bazi/shengong-minggong",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success", "data"]
    )
    result.add_test("身宫命宫", success, error)
    print(f"  {'✅' if success else '❌'} 身宫命宫: {'通过' if success else error}")


def test_smart_analyze(base_url: str, result: E2ETestResult):
    """测试智能分析接口"""
    print(f"\n{Colors.BLUE}测试智能分析接口{Colors.RESET}")
    
    # 测试财富意图
    question = "我的财运怎么样？"
    url = f"{base_url}/api/v1/smart-analyze?question={question}&solar_date=1990-01-15&solar_time=12:00&gender=male"
    
    success, error = test_endpoint(
        "智能分析 (财富)",
        url,
        method="GET",
        expected_keys=["success", "data"]
    )
    result.add_test("智能分析 (财富)", success, error)
    print(f"  {'✅' if success else '❌'} 智能分析 (财富): {'通过' if success else error}")


def test_hot_reload_status(base_url: str, result: E2ETestResult):
    """测试热更新状态接口"""
    print(f"\n{Colors.BLUE}测试热更新状态接口{Colors.RESET}")
    
    success, error = test_endpoint(
        "热更新状态",
        f"{base_url}/api/v1/hot-reload/status",
        expected_keys=["status"]
    )
    result.add_test("热更新状态", success, error)
    print(f"  {'✅' if success else '❌'} 热更新状态: {'通过' if success else error}")


def test_api_docs(base_url: str, result: E2ETestResult):
    """测试 API 文档接口"""
    print(f"\n{Colors.BLUE}测试 API 文档接口{Colors.RESET}")
    
    success, error = test_endpoint(
        "API 文档 (/docs)",
        f"{base_url}/docs",
        expected_status=200
    )
    result.add_test("API 文档 (/docs)", success, error)
    print(f"  {'✅' if success else '❌'} API 文档 (/docs): {'通过' if success else error}")


def run_e2e_tests(node1_url: str, node2_url: str) -> bool:
    """运行端到端测试"""
    print("=" * 80)
    print(f"{Colors.BOLD}生产环境端到端测试{Colors.RESET}")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Node1 URL: {node1_url}")
    print(f"Node2 URL: {node2_url}")
    print("=" * 80)
    
    # Node1 测试结果
    node1_result = E2ETestResult()
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== Node1 测试 ==={Colors.RESET}")
    
    test_health_check(node1_url, node1_result)
    test_bazi_calculate(node1_url, node1_result)
    test_formula_analysis(node1_url, node1_result)
    test_monthly_fortune(node1_url, node1_result)
    test_daily_fortune(node1_url, node1_result)
    test_shengong_minggong(node1_url, node1_result)
    test_smart_analyze(node1_url, node1_result)
    test_hot_reload_status(node1_url, node1_result)
    test_api_docs(node1_url, node1_result)
    
    print(f"\n{Colors.BOLD}Node1 测试结果:{Colors.RESET}")
    node1_success = node1_result.print_summary()
    
    # Node2 测试结果
    node2_result = E2ETestResult()
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== Node2 测试 ==={Colors.RESET}")
    
    test_health_check(node2_url, node2_result)
    test_bazi_calculate(node2_url, node2_result)
    test_formula_analysis(node2_url, node2_result)
    test_monthly_fortune(node2_url, node2_result)
    test_daily_fortune(node2_url, node2_result)
    test_shengong_minggong(node2_url, node2_result)
    test_smart_analyze(node2_url, node2_result)
    test_hot_reload_status(node2_url, node2_result)
    test_api_docs(node2_url, node2_result)
    
    print(f"\n{Colors.BOLD}Node2 测试结果:{Colors.RESET}")
    node2_success = node2_result.print_summary()
    
    # 总体结果
    total_result = E2ETestResult()
    total_result.total = node1_result.total + node2_result.total
    total_result.passed = node1_result.passed + node2_result.passed
    total_result.failed = node1_result.failed + node2_result.failed
    total_result.errors = node1_result.errors + node2_result.errors
    
    print(f"\n{Colors.BOLD}总体测试结果:{Colors.RESET}")
    all_success = total_result.print_summary()
    
    return all_success and node1_success and node2_success


def main():
    global TIMEOUT
    
    parser = argparse.ArgumentParser(description="生产环境端到端测试")
    parser.add_argument(
        "--node1-url",
        default=DEFAULT_NODE1_URL,
        help=f"Node1 URL (默认: {DEFAULT_NODE1_URL})"
    )
    parser.add_argument(
        "--node2-url",
        default=DEFAULT_NODE2_URL,
        help=f"Node2 URL (默认: {DEFAULT_NODE2_URL})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT,
        help=f"请求超时时间（秒，默认: {TIMEOUT}）"
    )
    
    args = parser.parse_args()
    
    TIMEOUT = args.timeout
    
    success = run_e2e_tests(args.node1_url, args.node2_url)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

