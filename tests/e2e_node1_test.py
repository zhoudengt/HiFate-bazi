#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node1 完整功能测试脚本（灰度发布专用）
测试所有前端调用的接口，提供详细的测试报告

使用方法：
    python3 tests/e2e_node1_test.py --node-url http://8.210.52.217:8001
    
选项：
    --node-url: Node1 的 URL
    --json-output: 以 JSON 格式输出错误信息（用于失败报告）
    --timeout: 请求超时时间（秒，默认30）
"""

import sys
import os
import json
import time
import argparse
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 默认配置
DEFAULT_NODE_URL = "http://8.210.52.217:8001"
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

TEST_DAILY_FORTUNE_CALENDAR_DATA = {
    "date": "2025-01-15",
    "user_solar_date": "1990-01-15",
    "user_solar_time": "12:00",
    "user_gender": "male"
}


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class TestResult:
    """单个测试结果"""
    def __init__(self, name: str, success: bool, error: str = None, response_time: float = 0):
        self.name = name
        self.success = success
        self.error = error
        self.response_time = response_time
    
    def to_dict(self) -> Dict:
        """转换为字典（用于 JSON 输出）"""
        return {
            "test_name": self.name,
            "success": self.success,
            "error": self.error,
            "response_time_ms": round(self.response_time * 1000, 2)
        }


class E2ETestResult:
    """测试结果汇总"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.results: List[TestResult] = []
        self.start_time = time.time()
        self.end_time = None
    
    def add_test(self, result: TestResult):
        """添加测试结果"""
        self.total += 1
        if result.success:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append(result)
    
    def finish(self):
        """完成测试"""
        self.end_time = time.time()
    
    def get_duration(self) -> float:
        """获取测试总耗时（秒）"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def print_summary(self, json_output: bool = False):
        """打印测试结果汇总"""
        self.finish()
        
        if json_output:
            # JSON 输出（用于失败报告）
            failed_tests = [r.to_dict() for r in self.results if not r.success]
            print(json.dumps({
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "success_rate": round(self.passed / self.total * 100, 2) if self.total > 0 else 0,
                "duration_seconds": round(self.get_duration(), 2),
                "failed_tests": failed_tests
            }, ensure_ascii=False, indent=2))
            return self.failed == 0
        
        # 文本输出
        print("\n" + "=" * 80)
        print(f"{Colors.BOLD}测试结果汇总{Colors.RESET}")
        print("=" * 80)
        print(f"总测试数: {self.total}")
        print(f"{Colors.GREEN}通过: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}失败: {self.failed}{Colors.RESET}")
        print(f"成功率: {self.passed / self.total * 100:.1f}%")
        print(f"总耗时: {self.get_duration():.2f} 秒")
        
        if self.failed > 0:
            print(f"\n{Colors.RED}失败的测试:{Colors.RESET}")
            for result in self.results:
                if not result.success:
                    print(f"  - {result.name}: {result.error}")
                    if result.response_time > 0:
                        print(f"    响应时间: {result.response_time * 1000:.2f}ms")
        
        # 性能统计
        if self.results:
            response_times = [r.response_time for r in self.results if r.response_time > 0]
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                print(f"\n性能统计:")
                print(f"  平均响应时间: {avg_time * 1000:.2f}ms")
                print(f"  最大响应时间: {max_time * 1000:.2f}ms")
        
        print("=" * 80)
        return self.failed == 0


def test_endpoint(
    name: str,
    url: str,
    method: str = "GET",
    data: Dict = None,
    expected_status: int = 200,
    expected_keys: List[str] = None,
    timeout: int = TIMEOUT,
    stream: bool = False
) -> TestResult:
    """
    测试单个端点
    
    Returns:
        TestResult: 测试结果
    """
    start_time = time.time()
    error = None
    success = False
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=timeout, stream=stream)
        elif method == "POST":
            response = requests.post(
                url, 
                json=data, 
                timeout=timeout, 
                headers={"Content-Type": "application/json"},
                stream=stream
            )
        else:
            error = f"不支持的 HTTP 方法: {method}"
            return TestResult(name, False, error, time.time() - start_time)
        
        response_time = time.time() - start_time
        
        if response.status_code != expected_status:
            error = f"状态码错误: 期望 {expected_status}, 实际 {response.status_code}"
            if response.text:
                error += f"\n响应内容: {response.text[:200]}"
            return TestResult(name, False, error, response_time)
        
        # 对于流式响应，只检查状态码
        if stream:
            success = True
        elif expected_keys:
            try:
                json_data = response.json()
                for key in expected_keys:
                    if key not in json_data:
                        error = f"响应中缺少字段: {key}"
                        return TestResult(name, False, error, response_time)
                success = True
            except json.JSONDecodeError:
                error = "响应不是有效的 JSON"
                return TestResult(name, False, error, response_time)
        else:
            success = True
        
        return TestResult(name, success, None, response_time)
    
    except requests.exceptions.Timeout:
        error = f"请求超时（>{timeout}秒）"
        return TestResult(name, False, error, time.time() - start_time)
    except requests.exceptions.ConnectionError:
        error = "连接错误，服务可能未启动"
        return TestResult(name, False, error, time.time() - start_time)
    except Exception as e:
        error = f"异常: {str(e)}"
        return TestResult(name, False, error, time.time() - start_time)


def test_health_check(base_url: str, result: E2ETestResult):
    """测试健康检查接口"""
    print(f"\n{Colors.BLUE}测试健康检查接口{Colors.RESET}")
    
    # 基本健康检查
    test_result = test_endpoint(
        "健康检查 (/)",
        f"{base_url}/health",
        expected_keys=["status"]
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 健康检查 (/): {'通过' if test_result.success else test_result.error}")
    
    # API 健康检查
    test_result = test_endpoint(
        "健康检查 (/api/v1/health)",
        f"{base_url}/api/v1/health",
        expected_keys=["status"]
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 健康检查 (/api/v1/health): {'通过' if test_result.success else test_result.error}")


def test_bazi_calculate(base_url: str, result: E2ETestResult):
    """测试八字计算接口"""
    print(f"\n{Colors.BLUE}测试八字计算接口{Colors.RESET}")
    
    # 男性八字计算
    test_result = test_endpoint(
        "八字计算 (男性)",
        f"{base_url}/api/v1/bazi/calculate",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success", "data"]
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 八字计算 (男性): {'通过' if test_result.success else test_result.error}")
    
    # 女性八字计算
    test_result = test_endpoint(
        "八字计算 (女性)",
        f"{base_url}/api/v1/bazi/calculate",
        method="POST",
        data=TEST_BAZI_DATA_FEMALE,
        expected_keys=["success", "data"]
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 八字计算 (女性): {'通过' if test_result.success else test_result.error}")


def test_formula_analysis(base_url: str, result: E2ETestResult):
    """测试公式分析接口"""
    print(f"\n{Colors.BLUE}测试公式分析接口{Colors.RESET}")
    
    test_result = test_endpoint(
        "公式分析",
        f"{base_url}/api/v1/bazi/formula-analysis",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success", "data"]
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 公式分析: {'通过' if test_result.success else test_result.error}")


def test_monthly_fortune(base_url: str, result: E2ETestResult):
    """测试月运势接口"""
    print(f"\n{Colors.BLUE}测试月运势接口{Colors.RESET}")
    
    # 月运势接口可能直接返回结果，不包含 data 字段
    test_result = test_endpoint(
        "月运势",
        f"{base_url}/api/v1/bazi/monthly-fortune",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success"]  # 只检查 success 字段
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 月运势: {'通过' if test_result.success else test_result.error}")


def test_daily_fortune(base_url: str, result: E2ETestResult):
    """测试日运势接口"""
    print(f"\n{Colors.BLUE}测试日运势接口{Colors.RESET}")
    
    # 日运势接口可能直接返回结果，不包含 data 字段
    test_result = test_endpoint(
        "日运势",
        f"{base_url}/api/v1/bazi/daily-fortune",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success"]  # 只检查 success 字段
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 日运势: {'通过' if test_result.success else test_result.error}")


def test_shengong_minggong(base_url: str, result: E2ETestResult):
    """测试身宫命宫接口"""
    print(f"\n{Colors.BLUE}测试身宫命宫接口{Colors.RESET}")
    
    test_result = test_endpoint(
        "身宫命宫",
        f"{base_url}/api/v1/bazi/shengong-minggong",
        method="POST",
        data=TEST_BAZI_DATA,
        expected_keys=["success", "data"]
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 身宫命宫: {'通过' if test_result.success else test_result.error}")


def test_smart_analyze(base_url: str, result: E2ETestResult):
    """测试智能分析接口"""
    print(f"\n{Colors.BLUE}测试智能分析接口{Colors.RESET}")
    
    # 测试财富意图（注意：接口需要 year, month, day, hour 参数，不是 solar_date）
    # 路由路径：/api/v1/smart-fortune/smart-analyze 或通过 grpc_gateway: /api/v1/smart-analyze
    question = "我的财运怎么样？"
    # 先尝试 grpc_gateway 路径
    url = f"{base_url}/api/v1/smart-analyze?question={question}&year=1990&month=1&day=15&hour=12&gender=male"
    
    test_result = test_endpoint(
        "智能分析 (财富)",
        url,
        method="GET",
        expected_keys=["success", "data"],
        timeout=60  # 智能分析可能需要更长时间
    )
    
    # 如果失败，尝试直接路由路径
    if not test_result.success and "404" in test_result.error:
        url2 = f"{base_url}/api/v1/smart-fortune/smart-analyze?question={question}&year=1990&month=1&day=15&hour=12&gender=male"
        test_result2 = test_endpoint(
            "智能分析 (财富-直接路由)",
            url2,
            method="GET",
            expected_keys=["success", "data"],
            timeout=60
        )
        if test_result2.success:
            test_result = test_result2
    
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 智能分析 (财富): {'通过' if test_result.success else test_result.error}")


def test_daily_fortune_calendar(base_url: str, result: E2ETestResult):
    """测试每日运势日历接口"""
    print(f"\n{Colors.BLUE}测试每日运势日历接口{Colors.RESET}")
    
    # 注意：路由是 /query，不是 /calendar
    test_result = test_endpoint(
        "每日运势日历",
        f"{base_url}/api/v1/daily-fortune-calendar/query",
        method="POST",
        data=TEST_DAILY_FORTUNE_CALENDAR_DATA,
        expected_keys=["success"]
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 每日运势日历: {'通过' if test_result.success else test_result.error}")


def test_action_suggestions_stream(base_url: str, result: E2ETestResult):
    """测试行动建议流式接口"""
    print(f"\n{Colors.BLUE}测试行动建议流式接口{Colors.RESET}")
    
    # 流式接口测试（需要 yi 和 ji 字段）
    action_data = {
        "yi": ["解除", "扫舍", "馀事勿取"],
        "ji": ["诸事不宜"]
    }
    test_result = test_endpoint(
        "行动建议流式",
        f"{base_url}/api/v1/daily-fortune-calendar/action-suggestions/stream",
        method="POST",
        data=action_data,
        stream=True,
        timeout=10  # 流式接口快速检查
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 行动建议流式: {'通过' if test_result.success else test_result.error}")


def test_hot_reload_status(base_url: str, result: E2ETestResult):
    """测试热更新状态接口"""
    print(f"\n{Colors.BLUE}测试热更新状态接口{Colors.RESET}")
    
    test_result = test_endpoint(
        "热更新状态",
        f"{base_url}/api/v1/hot-reload/status",
        expected_keys=["status"]
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} 热更新状态: {'通过' if test_result.success else test_result.error}")


def test_api_docs(base_url: str, result: E2ETestResult):
    """测试 API 文档接口"""
    print(f"\n{Colors.BLUE}测试 API 文档接口{Colors.RESET}")
    
    test_result = test_endpoint(
        "API 文档 (/docs)",
        f"{base_url}/docs",
        expected_status=200
    )
    result.add_test(test_result)
    print(f"  {'✅' if test_result.success else '❌'} API 文档 (/docs): {'通过' if test_result.success else test_result.error}")


def run_node1_tests(node_url: str, json_output: bool = False) -> bool:
    """运行 Node1 完整功能测试"""
    if not json_output:
        print("=" * 80)
        print(f"{Colors.BOLD}Node1 完整功能测试（灰度发布专用）{Colors.RESET}")
        print("=" * 80)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Node URL: {node_url}")
        print("=" * 80)
    
    result = E2ETestResult()
    
    # 执行所有测试
    test_health_check(node_url, result)
    test_bazi_calculate(node_url, result)
    test_formula_analysis(node_url, result)
    test_monthly_fortune(node_url, result)
    test_daily_fortune(node_url, result)
    test_shengong_minggong(node_url, result)
    test_smart_analyze(node_url, result)
    test_daily_fortune_calendar(node_url, result)
    test_action_suggestions_stream(node_url, result)
    test_hot_reload_status(node_url, result)
    test_api_docs(node_url, result)
    
    # 打印结果
    success = result.print_summary(json_output=json_output)
    
    return success


def main():
    global TIMEOUT
    
    parser = argparse.ArgumentParser(description="Node1 完整功能测试（灰度发布专用）")
    parser.add_argument(
        "--node-url",
        default=DEFAULT_NODE_URL,
        help=f"Node1 URL (默认: {DEFAULT_NODE_URL})"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="以 JSON 格式输出错误信息（用于失败报告）"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT,
        help=f"请求超时时间（秒，默认: {TIMEOUT}）"
    )
    
    args = parser.parse_args()
    
    TIMEOUT = args.timeout
    
    success = run_node1_tests(args.node_url, json_output=args.json_output)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

