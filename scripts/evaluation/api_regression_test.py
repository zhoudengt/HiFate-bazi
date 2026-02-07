#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 回归测试脚本

每次代码修改后运行此脚本，确保所有接口正常工作。

「测试」默认范围（基本+流式+支付）：
    - 基本接口：基本信息、排盘、身宫命宫、六十甲子等
    - 流式接口：每日运势、五行占比、喜神忌神、婚姻/事业/健康/子女/总评/年运、智能分析、
                面相分析(流式)、办公桌风水(流式)
    - 支付接口：支付渠道状态、Stripe 创建订单、PayerMax 创建订单、Stripe 验证支付、PayerMax 验证支付

使用方法：
    # 生产环境完整测试（基本+流式+支付，推荐）
    python scripts/evaluation/api_regression_test.py --env production --category basic --category stream --category payment --parallel

    # 测试所有类别（含管理接口）
    python scripts/evaluation/api_regression_test.py --env production

    # 只测试特定类别
    python scripts/evaluation/api_regression_test.py --env production --category basic
    python scripts/evaluation/api_regression_test.py --env production --category stream --parallel
    python scripts/evaluation/api_regression_test.py --env production --category payment

测试类别：
    - basic: 基础接口（非流式）
    - stream: 流式接口（含面相、办公桌风水）
    - payment: 支付接口（Stripe + PayerMax）
    - admin: 管理接口
    - all: 所有接口（不指定 --category 时）
"""

import os
import sys
import json
import time
import argparse
import requests
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class TestCategory(Enum):
    BASIC = "basic"
    STREAM = "stream"
    PAYMENT = "payment"
    ADMIN = "admin"


# 最小 1x1 PNG（用于面相/风水等需要上传图片的流式接口占位）
_MINIMAL_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


@dataclass
class TestCase:
    """测试用例"""
    name: str
    category: TestCategory
    method: str
    endpoint: str
    payload: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, str]] = None
    expected_keys: Optional[List[str]] = None
    timeout: int = 30
    is_stream: bool = False
    description: str = ""
    # 流式 + 文件上传：表单文件字段名，如 "image"。测试时使用最小占位图
    stream_form_file_key: Optional[str] = None
    stream_form_data: Optional[Dict[str, str]] = None  # 其他 Form 字段
    allow_success_false: bool = False  # 允许 success=false（如验证过期/无效订单，接口本身正常）


# 环境配置
ENVIRONMENTS = {
    "local": "http://localhost:8001",
    "production": "http://8.210.52.217:8001",
    "node2": "http://47.243.160.43:8001"
}

# 通用测试数据
TEST_DATA = {
    "bazi_1990": {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male"
    },
    "bazi_1992": {
        "solar_date": "1992-01-15",
        "solar_time": "12:00",
        "gender": "male"
    },
    "bazi_1995": {
        "solar_date": "1995-01-15",
        "solar_time": "12:00",
        "gender": "male"
    },
    "daily_fortune": {
        "date": "2025-01-27",
        "solar_date": "1992-01-15",
        "solar_time": "12:00",
        "gender": "male"
    }
}

# 所有测试用例
TEST_CASES: List[TestCase] = [
    # ==================== 基础接口 ====================
    TestCase(
        name="基本信息",
        category=TestCategory.BASIC,
        method="POST",
        endpoint="/api/v1/bazi/interface",
        payload=TEST_DATA["bazi_1990"],
        expected_keys=["success", "data"],
        description="八字基本信息接口"
    ),
    TestCase(
        name="基本排盘",
        category=TestCategory.BASIC,
        method="POST",
        endpoint="/api/v1/bazi/pan/display",
        payload=TEST_DATA["bazi_1992"],
        expected_keys=["success"],
        description="基本排盘显示"
    ),
    TestCase(
        name="专业排盘-大运流年流月",
        category=TestCategory.BASIC,
        method="POST",
        endpoint="/api/v1/bazi/fortune/display",
        payload=TEST_DATA["bazi_1990"],
        expected_keys=["success"],
        description="专业排盘-大运流年流月"
    ),
    TestCase(
        name="身宫命宫胎元",
        category=TestCategory.BASIC,
        method="POST",
        endpoint="/api/v1/bazi/shengong-minggong",
        payload=TEST_DATA["bazi_1995"],
        expected_keys=["success"],
        description="专业排盘-身宫命宫胎元"
    ),
    TestCase(
        name="日元六十甲子",
        category=TestCategory.BASIC,
        method="POST",
        endpoint="/api/v1/bazi/rizhu-liujiazi",
        payload=TEST_DATA["bazi_1990"],
        expected_keys=["success"],
        description="八字命理-日元-六十甲子"
    ),
    
    # ==================== 流式接口 ====================
    TestCase(
        name="每日运势日历(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v1/daily-fortune-calendar/stream",
        payload=TEST_DATA["daily_fortune"],
        timeout=100,
        is_stream=True,
        description="每日运势日历流式接口"
    ),
    TestCase(
        name="五行占比(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v1/bazi/wuxing-proportion/stream",
        payload=TEST_DATA["bazi_1992"],
        timeout=100,
        is_stream=True,
        description="八字命理-五行占比流式分析"
    ),
    TestCase(
        name="喜神忌神(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v1/bazi/xishen-jishen/stream",
        payload=TEST_DATA["bazi_1990"],
        timeout=100,
        is_stream=True,
        description="八字命理-喜神忌神流式分析"
    ),
    TestCase(
        name="感情婚姻(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v1/bazi/marriage-analysis/stream",
        payload=TEST_DATA["bazi_1990"],
        timeout=100,
        is_stream=True,
        description="八字命理-感情婚姻流式分析"
    ),
    TestCase(
        name="事业财富(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v1/career-wealth/stream",
        payload=TEST_DATA["bazi_1990"],
        timeout=100,
        is_stream=True,
        description="八字命理-事业财富流式分析"
    ),
    TestCase(
        name="子女学习(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v1/children-study/stream",
        payload=TEST_DATA["bazi_1990"],
        timeout=100,
        is_stream=True,
        description="八字命理-子女学习流式分析"
    ),
    TestCase(
        name="身体健康(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v1/health/stream",
        payload=TEST_DATA["bazi_1990"],
        timeout=100,
        is_stream=True,
        description="八字命理-身体健康流式分析"
    ),
    TestCase(
        name="总评分析(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v1/general-review/stream",
        payload=TEST_DATA["bazi_1995"],
        timeout=100,
        is_stream=True,
        description="八字命理-总评分析流式"
    ),
    TestCase(
        name="年运报告(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v1/annual-report/stream",
        payload=TEST_DATA["bazi_1990"],
        timeout=100,
        is_stream=True,
        description="八字命理-年运报告流式"
    ),
    TestCase(
        name="智能分析-类别(流式)",
        category=TestCategory.STREAM,
        method="GET",
        endpoint="/api/v1/smart-fortune/smart-analyze-stream",
        params={
            "category": "事业财富",
            "year": "1990",
            "month": "5",
            "day": "15",
            "hour": "14",
            "gender": "male",
            "user_id": "test_user_001"
        },
        timeout=100,
        is_stream=True,
        description="智能分析-按类别"
    ),
    TestCase(
        name="智能分析-问题(流式)",
        category=TestCategory.STREAM,
        method="GET",
        endpoint="/api/v1/smart-fortune/smart-analyze-stream",
        params={
            "question": "我今年的事业运势如何？",
            "year": "1990",
            "month": "5",
            "day": "15",
            "hour": "14",
            "gender": "male",
            "user_id": "test_user_001"
        },
        timeout=100,
        is_stream=True,
        description="智能分析-按问题"
    ),
    TestCase(
        name="面相分析(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v2/face/analyze/stream",
        timeout=90,
        is_stream=True,
        stream_form_file_key="image",
        stream_form_data={"analysis_types": "gongwei,liuqin"},
        description="面相综合分析-流式"
    ),
    TestCase(
        name="办公桌风水(流式)",
        category=TestCategory.STREAM,
        method="POST",
        endpoint="/api/v2/desk-fengshui/analyze/stream",
        timeout=90,
        is_stream=True,
        stream_form_file_key="image",
        stream_form_data={},
        description="办公桌风水分析-流式"
    ),
    
    # ==================== 支付接口 ====================
    TestCase(
        name="Stripe创建订单",
        category=TestCategory.PAYMENT,
        method="POST",
        endpoint="/api/v1/payment/unified/create",
        payload={
            "provider": "stripe",
            "amount": "4.10",
            "currency": "USD",
            "product_name": "Stripe测试产品",
            "customer_email": "test@example.com",
            "success_url": "http://localhost:5173/payment/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "http://localhost:5173/payment/cancel"
        },
        expected_keys=["success"],
        timeout=45,
        description="Stripe支付订单创建"
    ),
    TestCase(
        name="支付渠道状态",
        category=TestCategory.PAYMENT,
        method="GET",
        endpoint="/api/v1/payment/providers",
        expected_keys=["success"],
        timeout=30,  # 留出余量（冷启动+批量配置后应秒出）
        description="获取支付渠道状态（Stripe + PayerMax）"
    ),
    TestCase(
        name="PayerMax创建订单",
        category=TestCategory.PAYMENT,
        method="POST",
        endpoint="/api/v1/payment/unified/create",
        payload={
            "provider": "payermax",
            "amount": "19.90",
            "currency": "USD",
            "product_name": "PayerMax测试",
            "customer_email": "test@example.com",
            "success_url": "http://localhost:5173/payment/success",
            "cancel_url": "http://localhost:5173/payment/cancel"
        },
        expected_keys=["success"],
        timeout=60,  # 留出余量（服务端 API timeout=30s + 冷启动/DB）
        description="PayerMax支付订单创建"
    ),
    TestCase(
        name="Stripe验证支付",
        category=TestCategory.PAYMENT,
        method="POST",
        endpoint="/api/v1/payment/unified/verify",
        payload={
            "provider": "stripe",
            "session_id": "cs_test_a1DJKIgGajESSae6O5lAziGPZBqkZ4itG0Ic7SZzMQ64BvJsh1qzP4ZR49"
        },
        expected_keys=["success", "provider"],
        timeout=15,
        allow_success_false=True,  # 测试订单可能已过期，接口正常返回即算通过
        description="Stripe支付状态验证"
    ),
    TestCase(
        name="PayerMax验证支付",
        category=TestCategory.PAYMENT,
        method="POST",
        endpoint="/api/v1/payment/unified/verify",
        payload={
            "provider": "payermax",
            "order_id": "PAYERMAX_1770444279059"
        },
        expected_keys=["success", "provider"],
        timeout=15,
        allow_success_false=True,  # 测试订单可能已过期，接口正常返回即算通过
        description="PayerMax支付状态验证"
    ),
    
    # ==================== 管理接口 ====================
    TestCase(
        name="首页内容列表",
        category=TestCategory.ADMIN,
        method="GET",
        endpoint="/api/v1/homepage/contents",
        expected_keys=["success"],
        description="获取首页内容列表"
    ),
]


class APITester:
    """API 测试器"""
    
    def __init__(self, base_url: str, verbose: bool = True):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.results: List[Dict[str, Any]] = []
    
    def log(self, message: str, level: str = "INFO"):
        """输出日志"""
        if self.verbose:
            prefix = {
                "INFO": "ℹ️ ",
                "SUCCESS": "✅",
                "ERROR": "❌",
                "WARNING": "⚠️ "
            }.get(level, "")
            print(f"{prefix} {message}")
    
    def test_basic_endpoint(self, case: TestCase) -> Tuple[bool, str, float]:
        """测试基础（非流式）接口"""
        url = f"{self.base_url}{case.endpoint}"
        start_time = time.time()
        
        try:
            if case.method == "GET":
                response = requests.get(url, params=case.params, timeout=case.timeout)
            else:
                response = requests.post(url, json=case.payload, timeout=case.timeout)
            
            elapsed = time.time() - start_time
            
            if response.status_code != 200:
                return False, f"HTTP {response.status_code}: {response.text[:200]}", elapsed
            
            try:
                data = response.json()
            except:
                return False, f"响应不是有效的 JSON: {response.text[:200]}", elapsed
            
            # 检查必要字段
            if case.expected_keys:
                missing = [k for k in case.expected_keys if k not in data]
                if missing:
                    return False, f"缺少字段: {missing}", elapsed
            
            # 检查 success 字段
            if 'success' in data and not data['success'] and not case.allow_success_false:
                error = data.get('error', data.get('message', '未知错误'))
                return False, f"接口返回失败: {error}", elapsed
            
            return True, "OK", elapsed
            
        except requests.Timeout:
            return False, f"请求超时 ({case.timeout}s)", time.time() - start_time
        except Exception as e:
            return False, f"请求异常: {str(e)}", time.time() - start_time
    
    def test_stream_endpoint(self, case: TestCase) -> Tuple[bool, str, float]:
        """测试流式接口（支持普通 JSON 或 multipart/form-data 文件上传）"""
        url = f"{self.base_url}{case.endpoint}"
        start_time = time.time()
        
        try:
            if case.method == "GET":
                response = requests.get(url, params=case.params, timeout=case.timeout, stream=True)
            elif getattr(case, 'stream_form_file_key', None):
                # 流式 + 文件上传（面相/风水等）
                import base64
                raw = base64.b64decode(_MINIMAL_PNG_BASE64)
                files = {case.stream_form_file_key: ("test.png", raw, "image/png")}
                data = getattr(case, 'stream_form_data', None) or {}
                response = requests.post(url, files=files, data=data, timeout=case.timeout, stream=True)
            else:
                response = requests.post(url, json=case.payload, timeout=case.timeout, stream=True)
            
            if response.status_code != 200:
                return False, f"HTTP {response.status_code}", time.time() - start_time
            
            # 读取流式响应
            has_data = False
            has_progress = False
            has_complete = False
            has_error = False
            error_content = ""
            chunk_count = 0
            content_length = 0
            
            current_event = None
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                
                # 支持 event: xxx 格式（智能分析接口使用）
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                    continue
                    
                if line.startswith("data: "):
                    chunk_count += 1
                    try:
                        data = json.loads(line[6:])
                        
                        # 优先使用 event 字段，其次使用 data 中的 type 字段
                        msg_type = current_event or data.get('type')
                        content = data.get('content', data.get('message', ''))
                        
                        if msg_type == 'data':
                            has_data = True
                        elif msg_type in ('progress', 'status', 'stream'):
                            has_progress = True
                            if isinstance(content, str):
                                content_length += len(content)
                        elif msg_type in ('complete', 'done', 'end'):
                            has_complete = True
                        elif msg_type == 'error':
                            has_error = True
                            error_content = content[:100] if isinstance(content, str) else str(content)[:100]
                        else:
                            # 未知类型也算进度
                            has_progress = True
                            
                        current_event = None  # 重置
                    except:
                        pass
                
                # 限制读取数量，避免等待太久
                if chunk_count > 100 or has_complete or has_error:
                    break
            
            elapsed = time.time() - start_time
            
            if has_error:
                # 面相接口用占位图时返回「未检测到人脸」，视为接口可用
                if "未检测到人脸" in (error_content or ""):
                    return True, "OK (接口可用，占位图无人脸)", elapsed
                return False, f"流式错误: {error_content}", elapsed
            
            # 检查是否有有效响应
            # 有些接口没有 data 类型，直接返回 progress，这也是正常的
            if not has_data and not has_progress:
                return False, "没有收到任何有效消息", elapsed
            
            if chunk_count == 0:
                return False, "没有收到任何 SSE 消息", elapsed
            
            # 构建状态信息
            parts = []
            if has_data:
                parts.append("data")
            if has_progress:
                parts.append(f"progress({content_length}字)")
            if has_complete:
                parts.append("complete")
            
            status = f"OK ({', '.join(parts)})"
            return True, status, elapsed
            
        except requests.Timeout:
            return False, f"请求超时 ({case.timeout}s)", time.time() - start_time
        except Exception as e:
            return False, f"请求异常: {str(e)}", time.time() - start_time
    
    def run_test(self, case: TestCase) -> Dict[str, Any]:
        """运行单个测试"""
        self.log(f"测试 {case.name} ({case.endpoint})...")
        
        if case.is_stream:
            success, message, elapsed = self.test_stream_endpoint(case)
        else:
            success, message, elapsed = self.test_basic_endpoint(case)
        
        result = {
            "name": case.name,
            "category": case.category.value,
            "endpoint": case.endpoint,
            "success": success,
            "message": message,
            "elapsed": round(elapsed, 2),
            "description": case.description
        }
        
        if success:
            self.log(f"{case.name}: {message} ({elapsed:.2f}s)", "SUCCESS")
        else:
            self.log(f"{case.name}: {message}", "ERROR")
        
        self.results.append(result)
        return result
    
    def run_all(self, categories: Optional[List[TestCategory]] = None, parallel: bool = False) -> List[Dict[str, Any]]:
        """运行所有测试"""
        self.results = []
        
        cases = TEST_CASES
        if categories:
            cases = [c for c in cases if c.category in categories]
        
        print(f"\n{'='*60}")
        print(f"API 回归测试 - {self.base_url}")
        print(f"测试用例数: {len(cases)}")
        print(f"执行模式: {'并行' if parallel else '串行'}")
        print(f"{'='*60}\n")
        
        if parallel:
            # 分离流式和非流式测试
            stream_cases = [c for c in cases if c.is_stream]
            basic_cases = [c for c in cases if not c.is_stream]
            
            # 先串行执行基础测试（通常很快）
            if basic_cases:
                print(">>> 执行基础接口测试（串行）...")
                for case in basic_cases:
                    self.run_test(case)
                print()
            
            # 并行执行流式测试
            if stream_cases:
                print(f">>> 执行流式接口测试（并行，{len(stream_cases)} 个）...")
                self._run_parallel(stream_cases)
        else:
            for case in cases:
                self.run_test(case)
                print()  # 空行分隔
        
        return self.results
    
    def _run_parallel(self, cases: List[TestCase], max_workers: int = 5):
        """并行执行测试"""
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_case = {executor.submit(self._run_test_sync, case): case for case in cases}
            
            # 收集结果
            for future in as_completed(future_to_case):
                case = future_to_case[future]
                try:
                    result = future.result()
                    self.results.append(result)
                    
                    if result['success']:
                        self.log(f"{result['name']}: {result['message']} ({result['elapsed']:.2f}s)", "SUCCESS")
                    else:
                        self.log(f"{result['name']}: {result['message']}", "ERROR")
                except Exception as e:
                    self.log(f"{case.name}: 执行异常 - {str(e)}", "ERROR")
                    self.results.append({
                        "name": case.name,
                        "category": case.category.value,
                        "endpoint": case.endpoint,
                        "success": False,
                        "message": f"执行异常: {str(e)}",
                        "elapsed": 0,
                        "description": case.description
                    })
        
        total_time = time.time() - start_time
        print(f"\n>>> 并行测试完成，总耗时: {total_time:.2f}s\n")
    
    def _run_test_sync(self, case: TestCase) -> Dict[str, Any]:
        """同步执行单个测试（用于并行）"""
        if case.is_stream:
            success, message, elapsed = self.test_stream_endpoint(case)
        else:
            success, message, elapsed = self.test_basic_endpoint(case)
        
        return {
            "name": case.name,
            "category": case.category.value,
            "endpoint": case.endpoint,
            "success": success,
            "message": message,
            "elapsed": round(elapsed, 2),
            "description": case.description
        }
    
    def print_summary(self):
        """打印测试摘要"""
        if not self.results:
            print("没有测试结果")
            return
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = total - passed
        
        print(f"\n{'='*60}")
        print(f"测试摘要")
        print(f"{'='*60}")
        print(f"总计: {total} | 通过: {passed} | 失败: {failed}")
        print(f"通过率: {passed/total*100:.1f}%")
        
        if failed > 0:
            print(f"\n失败的测试:")
            for r in self.results:
                if not r['success']:
                    print(f"  ❌ {r['name']}: {r['message']}")
        
        print(f"{'='*60}\n")
        
        return failed == 0


def main():
    parser = argparse.ArgumentParser(description="API 回归测试")
    parser.add_argument("--env", choices=["local", "production", "node2"], default="local",
                        help="测试环境 (默认: local)")
    parser.add_argument("--url", help="自定义基础 URL (覆盖 --env)")
    parser.add_argument("--category", choices=["basic", "stream", "payment", "admin", "all"], 
                        action="append", default=None,
                        help="测试类别，可多次指定。不指定或 all = 全部；指定多个则只测这些（如 --category basic --category stream --category payment）")
    parser.add_argument("--parallel", "-p", action="store_true", 
                        help="并行执行流式接口测试（大幅减少测试时间）")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")
    
    args = parser.parse_args()
    
    # 确定基础 URL
    base_url = args.url or ENVIRONMENTS.get(args.env, ENVIRONMENTS["local"])
    
    # 确定测试类别（支持多选；不指定或含 all = 全部）
    categories = None
    if args.category and "all" not in args.category:
        categories = [TestCategory(c) for c in args.category]
    
    # 运行测试
    tester = APITester(base_url, verbose=not args.quiet)
    tester.run_all(categories, parallel=args.parallel)
    
    # 打印摘要
    all_passed = tester.print_summary()
    
    # 返回退出码
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
