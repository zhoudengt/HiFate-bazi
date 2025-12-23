#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试报告生成器
汇总所有测试结果，生成详细的测试报告
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tests.api.test_all_updated_endpoints import run_all_tests, TestResult


def generate_test_report(results: List[TestResult]) -> Dict[str, Any]:
    """生成测试报告"""
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    
    # 按接口分组
    endpoint_groups = {}
    for result in results:
        # 提取接口名称（从测试名称中）
        parts = result.name.split(' - ')
        if len(parts) >= 2:
            endpoint_name = parts[0]
            test_type = parts[1]
        else:
            endpoint_name = result.name
            test_type = "未知"
        
        if endpoint_name not in endpoint_groups:
            endpoint_groups[endpoint_name] = []
        endpoint_groups[endpoint_name].append({
            'test_type': test_type,
            'success': result.success,
            'error': result.error,
            'response_time': result.response_time
        })
    
    # 统计
    endpoint_stats = {}
    for endpoint, tests in endpoint_groups.items():
        endpoint_total = len(tests)
        endpoint_passed = sum(1 for t in tests if t['success'])
        endpoint_failed = endpoint_total - endpoint_passed
        endpoint_stats[endpoint] = {
            'total': endpoint_total,
            'passed': endpoint_passed,
            'failed': endpoint_failed,
            'pass_rate': f"{endpoint_passed/endpoint_total*100:.1f}%" if endpoint_total > 0 else "0%"
        }
    
    # 失败详情
    failed_tests = [r for r in results if not r.success]
    
    # 性能统计
    response_times = [r.response_time for r in results if r.success and r.response_time > 0]
    avg_time = sum(response_times) / len(response_times) if response_times else 0
    min_time = min(response_times) if response_times else 0
    max_time = max(response_times) if response_times else 0
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': f"{passed/total*100:.1f}%" if total > 0 else "0%"
        },
        'endpoint_stats': endpoint_stats,
        'failed_tests': [
            {
                'name': r.name,
                'error': r.error,
                'response_time': r.response_time
            }
            for r in failed_tests
        ],
        'performance': {
            'avg_response_time': f"{avg_time:.2f}s",
            'min_response_time': f"{min_time:.2f}s",
            'max_response_time': f"{max_time:.2f}s"
        }
    }
    
    return report


def print_test_report(report: Dict[str, Any]):
    """打印测试报告"""
    print("=" * 80)
    print("测试报告")
    print("=" * 80)
    print(f"生成时间: {report['timestamp']}")
    print()
    
    # 汇总
    summary = report['summary']
    print("测试汇总:")
    print(f"  总测试数: {summary['total']}")
    print(f"  通过: {summary['passed']} ({summary['pass_rate']})")
    print(f"  失败: {summary['failed']}")
    print()
    
    # 接口统计
    print("接口测试统计:")
    print("-" * 80)
    for endpoint, stats in sorted(report['endpoint_stats'].items()):
        status = "✅" if stats['failed'] == 0 else "❌"
        print(f"{status} {endpoint}: {stats['passed']}/{stats['total']} 通过 ({stats['pass_rate']})")
    print()
    
    # 失败详情
    if report['failed_tests']:
        print("失败的测试:")
        print("-" * 80)
        for test in report['failed_tests']:
            print(f"  ❌ {test['name']}")
            print(f"     错误: {test['error']}")
            print()
    
    # 性能统计
    perf = report['performance']
    print("性能统计:")
    print(f"  平均响应时间: {perf['avg_response_time']}")
    print(f"  最快: {perf['min_response_time']}")
    print(f"  最慢: {perf['max_response_time']}")
    print()


def main():
    """主函数"""
    print("运行所有测试...")
    print()
    
    # 运行测试（这里需要修改 test_all_updated_endpoints.py 以返回结果）
    # 暂时使用模拟数据
    results = run_all_tests()
    
    # 生成报告
    report = generate_test_report(results)
    
    # 打印报告
    print_test_report(report)
    
    # 保存报告到文件
    report_file = os.path.join(project_root, 'tests', 'api', 'test_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"测试报告已保存到: {report_file}")
    
    return 0 if report['summary']['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

