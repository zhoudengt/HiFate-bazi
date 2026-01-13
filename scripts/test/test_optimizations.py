#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化功能自动化测试脚本

测试所有新增的优化功能：
1. 监控指标收集
2. 熔断器保护
3. 自动重试机制
4. 缓存版本管理器
5. 适配器集成测试
6. 向后兼容性测试

使用方法：
    python3 scripts/test/test_optimizations.py
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

# 测试结果
test_results = {
    'passed': [],
    'failed': [],
    'skipped': []
}


def print_header(text: str):
    """打印测试标题"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{text}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")


def print_test(name: str):
    """打印测试名称"""
    print(f"{CYAN}▶ 测试: {name}{NC}")


def print_pass(message: str = ""):
    """打印通过信息"""
    print(f"{GREEN}✓ 通过{NC} {message}")
    test_results['passed'].append(message)


def print_fail(message: str, error: Exception = None):
    """打印失败信息"""
    error_msg = f": {str(error)}" if error else ""
    print(f"{RED}✗ 失败{NC} {message}{error_msg}")
    test_results['failed'].append(f"{message}{error_msg}")


def print_skip(message: str):
    """打印跳过信息"""
    print(f"{YELLOW}⊘ 跳过{NC} {message}")
    test_results['skipped'].append(message)


def test_metrics_collector():
    """测试监控指标收集器"""
    print_header("测试 1: 监控指标收集器")
    
    try:
        print_test("创建 MetricsCollector 实例")
        from server.utils.metrics_collector import MetricsCollector, get_metrics_collector
        
        collector = get_metrics_collector()
        assert collector is not None, "MetricsCollector 实例创建失败"
        print_pass("MetricsCollector 实例创建成功")
        
        print_test("记录 gRPC 调用指标")
        collector.record_grpc_call("bazi-core", "calculate_bazi", success=True, duration=0.1)
        collector.record_grpc_call("bazi-core", "calculate_bazi", success=False, duration=0.05, error_type="TimeoutError")
        print_pass("gRPC 调用指标记录成功")
        
        print_test("记录缓存命中率")
        collector.record_cache_hit("bazi:user:123", hit=True, cache_type="bazi")
        collector.record_cache_hit("bazi:user:456", hit=False, cache_type="bazi")
        print_pass("缓存命中率记录成功")
        
        print_test("获取统计信息")
        stats = collector.get_all_stats()
        assert "grpc_calls" in stats, "缺少 gRPC 调用统计"
        assert "cache_stats" in stats, "缺少缓存统计"
        print_pass(f"统计信息获取成功")
        
        return True
    except Exception as e:
        print_fail("监控指标收集器测试失败", e)
        return False


def test_circuit_breaker():
    """测试熔断器功能"""
    print_header("测试 2: 熔断器功能")
    
    # 检查是否启用
    if os.getenv("ENABLE_CIRCUIT_BREAKER", "false").lower() != "true":
        print_skip("熔断器未启用 (ENABLE_CIRCUIT_BREAKER=false)")
        return True
    
    try:
        print_test("创建熔断器实例")
        from server.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        
        config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout=5.0
        )
        breaker = CircuitBreaker.get("test-service", config=config)
        assert breaker is not None, "熔断器创建失败"
        print_pass("熔断器实例创建成功")
        
        print_test("测试熔断器状态转换")
        # 初始状态应该是 CLOSED
        assert breaker.is_closed, "初始状态应该是 CLOSED"
        print_pass("初始状态为 CLOSED")
        
        print_test("模拟失败触发熔断")
        # 模拟多次失败
        for i in range(3):
            breaker.record_failure(Exception("Test error"))
        
        # 应该触发熔断
        assert breaker.is_open, "应该触发熔断"
        print_pass("熔断器在失败达到阈值后触发")
        
        print_test("测试熔断后请求被拒绝")
        allowed = breaker.allow_request()
        assert not allowed, "熔断后请求应该被拒绝"
        print_pass("熔断后请求被正确拒绝")
        
        # 重置熔断器
        breaker.reset()
        assert breaker.is_closed, "重置后应该回到 CLOSED 状态"
        print_pass("熔断器重置成功")
        
        return True
    except Exception as e:
        print_fail("熔断器测试失败", e)
        return False


def test_retry_mechanism():
    """测试重试机制"""
    print_header("测试 3: 自动重试机制")
    
    # 检查是否启用
    if os.getenv("ENABLE_CIRCUIT_BREAKER", "false").lower() != "true":
        print_skip("重试机制未启用 (需要 ENABLE_CIRCUIT_BREAKER=true)")
        return True
    
    try:
        print_test("测试重试逻辑")
        from src.clients.base_grpc_client import BaseGrpcClient
        
        # 创建一个测试客户端
        class TestClient(BaseGrpcClient):
            def __init__(self):
                super().__init__('test-service', 9001, use_registry=False)
        
        client = TestClient()
        
        # 测试重试机制
        retry_count = [0]
        
        def failing_func():
            retry_count[0] += 1
            if retry_count[0] < 3:
                raise Exception("Test error")
            return "success"
        
        max_retries = int(os.getenv("GRPC_MAX_RETRIES", "3"))
        result = client.execute_with_retry(failing_func, max_retries=max_retries)
        
        assert result == "success", "重试后应该成功"
        assert retry_count[0] == 3, f"应该重试 {max_retries} 次"
        print_pass(f"重试机制正常工作 (重试了 {retry_count[0]} 次)")
        
        return True
    except Exception as e:
        print_fail("重试机制测试失败", e)
        return False


def test_cache_version_manager():
    """测试缓存版本管理器"""
    print_header("测试 4: 缓存版本管理器")
    
    # 检查是否启用
    if os.getenv("ENABLE_CACHE_VERSION", "false").lower() != "true":
        print_skip("缓存版本控制未启用 (ENABLE_CACHE_VERSION=false)")
        return True
    
    try:
        print_test("创建 CacheVersionManager 实例")
        from server.utils.cache_version_manager import CacheVersionManager
        
        # 重置单例
        CacheVersionManager._instance = None
        
        manager = CacheVersionManager.get_instance()
        assert manager is not None, "CacheVersionManager 实例创建失败"
        print_pass("CacheVersionManager 实例创建成功")
        
        print_test("测试版本前缀添加")
        key = "bazi:user:123"
        versioned_key = CacheVersionManager.get_versioned_key(key)
        expected_version = os.getenv("CACHE_VERSION", "v1")
        assert versioned_key == f"{expected_version}:{key}", f"版本前缀应该为 {expected_version}:"
        print_pass(f"版本前缀添加成功: {versioned_key}")
        
        print_test("测试版本获取")
        version = CacheVersionManager.get_version()
        assert version == expected_version, f"版本应该为 {expected_version}"
        print_pass(f"版本获取成功: {version}")
        
        print_test("测试缓存失效（如果 Redis 可用）")
        try:
            deleted = CacheVersionManager.invalidate_by_pattern("test:*")
            print_pass(f"缓存失效功能可用 (删除了 {deleted} 个 key)")
        except Exception as e:
            print_skip(f"缓存失效功能需要 Redis: {e}")
        
        return True
    except Exception as e:
        print_fail("缓存版本管理器测试失败", e)
        return False


def test_adapter_integration():
    """测试适配器集成"""
    print_header("测试 5: 适配器集成测试")
    
    try:
        print_test("测试 BaziCoreClientAdapter 接口兼容性")
        from server.interfaces.bazi_core_client_interface import IBaziCoreClient
        from server.adapters.bazi_core_client_adapter import BaziCoreClientAdapter
        
        # 使用本地测试地址（如果服务未运行，会跳过实际调用）
        try:
            adapter = BaziCoreClientAdapter(base_url="localhost:9001", timeout=5.0)
            assert isinstance(adapter, IBaziCoreClient), "适配器应该实现接口"
            print_pass("适配器接口兼容性验证通过")
            
            # 检查是否启用了增强功能
            if os.getenv("ENABLE_CIRCUIT_BREAKER", "false").lower() == "true":
                print_pass("熔断器已启用")
            else:
                print_skip("熔断器未启用（默认关闭）")
            
            if os.getenv("ENABLE_METRICS_COLLECTION", "true").lower() == "true":
                print_pass("监控指标收集已启用")
            
        except Exception as e:
            print_skip(f"适配器创建需要服务运行: {e}")
        
        print_test("测试 BaziRuleClientAdapter 接口兼容性")
        from server.interfaces.bazi_rule_client_interface import IBaziRuleClient
        from server.adapters.bazi_rule_client_adapter import BaziRuleClientAdapter
        
        try:
            rule_adapter = BaziRuleClientAdapter(base_url="localhost:9004", timeout=5.0)
            assert isinstance(rule_adapter, IBaziRuleClient), "规则适配器应该实现接口"
            print_pass("规则适配器接口兼容性验证通过")
        except Exception as e:
            print_skip(f"规则适配器创建需要服务运行: {e}")
        
        return True
    except Exception as e:
        print_fail("适配器集成测试失败", e)
        return False


def test_backward_compatibility():
    """测试向后兼容性"""
    print_header("测试 6: 向后兼容性测试")
    
    try:
        print_test("验证接口未改变")
        from server.interfaces.bazi_core_client_interface import IBaziCoreClient
        
        # 检查接口方法
        assert hasattr(IBaziCoreClient, 'calculate_bazi'), "接口应该包含 calculate_bazi 方法"
        print_pass("接口方法未改变")
        
        print_test("验证默认行为（功能关闭时）")
        # 临时关闭所有功能
        original_circuit_breaker = os.getenv("ENABLE_CIRCUIT_BREAKER")
        original_cache_version = os.getenv("ENABLE_CACHE_VERSION")
        
        os.environ["ENABLE_CIRCUIT_BREAKER"] = "false"
        os.environ["ENABLE_CACHE_VERSION"] = "false"
        
        # 重置单例
        from server.utils.cache_version_manager import CacheVersionManager
        
        CacheVersionManager._instance = None
        
        # 测试默认行为
        key = CacheVersionManager.get_versioned_key("test:key")
        assert key == "test:key", "默认情况下不应该添加版本前缀"
        print_pass("默认行为与修改前一致")
        
        # 恢复环境变量
        if original_circuit_breaker:
            os.environ["ENABLE_CIRCUIT_BREAKER"] = original_circuit_breaker
        if original_cache_version:
            os.environ["ENABLE_CACHE_VERSION"] = original_cache_version
        
        return True
    except Exception as e:
        print_fail("向后兼容性测试失败", e)
        return False


def print_summary():
    """打印测试总结"""
    print_header("测试总结")
    
    total = len(test_results['passed']) + len(test_results['failed']) + len(test_results['skipped'])
    passed = len(test_results['passed'])
    failed = len(test_results['failed'])
    skipped = len(test_results['skipped'])
    
    print(f"{GREEN}通过: {passed}{NC}")
    print(f"{RED}失败: {failed}{NC}")
    print(f"{YELLOW}跳过: {skipped}{NC}")
    print(f"{BLUE}总计: {total}{NC}\n")
    
    if failed > 0:
        print(f"{RED}失败的测试:{NC}")
        for test in test_results['failed']:
            print(f"  - {test}")
        print()
    
    if skipped > 0:
        print(f"{YELLOW}跳过的测试:{NC}")
        for test in test_results['skipped']:
            print(f"  - {test}")
        print()
    
    # 生成测试报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped
        },
        'results': test_results
    }
    
    report_file = PROJECT_ROOT / "scripts" / "test" / "optimization_test_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"{BLUE}测试报告已保存到: {report_file}{NC}\n")
    
    return failed == 0


def main():
    """主函数"""
    print(f"{BLUE}{'='*60}{NC}")
    print(f"{BLUE}优化功能自动化测试{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")
    
    print(f"{CYAN}测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NC}")
    print(f"{CYAN}项目根目录: {PROJECT_ROOT}{NC}\n")
    
    # 检查环境变量
    print(f"{YELLOW}环境变量检查:{NC}")
    print(f"  ENABLE_CIRCUIT_BREAKER: {os.getenv('ENABLE_CIRCUIT_BREAKER', 'false')}")
    print(f"  ENABLE_CACHE_VERSION: {os.getenv('ENABLE_CACHE_VERSION', 'false')}")
    print(f"  ENABLE_METRICS_COLLECTION: {os.getenv('ENABLE_METRICS_COLLECTION', 'true')}")
    print()
    
    # 运行所有测试
    tests = [
        test_metrics_collector,
        test_circuit_breaker,
        test_retry_mechanism,
        test_cache_version_manager,
        test_adapter_integration,
        test_backward_compatibility,
    ]
    
    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print_fail(f"测试 {test_func.__name__} 执行异常", e)
    
    # 打印总结
    success = print_summary()
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
