#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能运势分析直接测试脚本（不依赖服务启动）
直接调用函数并输出性能摘要
"""
import sys
import os
import json
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.api.v1.smart_fortune import smart_analyze
from server.utils.performance_monitor import PerformanceMonitor


async def test_direct():
    """直接测试智能运势分析函数"""
    print("=" * 80)
    print("智能运势分析 - 直接测试（端到端性能监控）")
    print("=" * 80)
    print()
    
    # 测试用例
    test_cases = [
        {
            "question": "我的财运怎么样？",
            "year": 1990,
            "month": 5,
            "day": 15,
            "hour": 12,
            "gender": "male",
            "include_fortune_context": False
        },
        {
            "question": "明年能升职吗？",
            "year": 1990,
            "month": 5,
            "day": 15,
            "hour": 12,
            "gender": "male",
            "include_fortune_context": False
        },
        {
            "question": "我后三年的财运如何？",
            "year": 1990,
            "month": 5,
            "day": 15,
            "hour": 12,
            "gender": "male",
            "include_fortune_context": True
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试用例 {i}/{len(test_cases)}")
        print(f"{'='*80}")
        print(f"问题: {test_case['question']}")
        print(f"出生信息: {test_case['year']}-{test_case['month']:02d}-{test_case['day']:02d} {test_case['hour']:02d}:00, {test_case['gender']}")
        print(f"包含流年大运: {test_case['include_fortune_context']}")
        print()
        
        try:
            # 调用函数
            result = await smart_analyze(**test_case)
            
            # 提取性能摘要
            performance = result.get("performance", {})
            
            print("\n" + "=" * 80)
            print("📊 性能摘要")
            print("=" * 80)
            print(f"总耗时: {performance.get('total_duration_ms', 0)}ms ({performance.get('total_duration_sec', 0):.3f}s)")
            print(f"阶段数: {len(performance.get('stages', []))}")
            print()
            
            print("各阶段耗时:")
            stages = performance.get("stages", [])
            for stage in stages:
                stage_name = stage.get("stage", "unknown")
                duration_ms = stage.get("duration_ms", 0)
                success = stage.get("success", True)
                status = "✅" if success else "❌"
                description = stage.get("description", "")
                
                # 显示额外指标
                metrics = []
                for key, value in stage.items():
                    if key.startswith("metric_"):
                        metrics.append(f"{key[7:]}: {value}")
                
                metrics_str = f" ({', '.join(metrics)})" if metrics else ""
                error_str = f" - 错误: {stage.get('error')}" if not success else ""
                
                print(f"  {status} {stage_name}: {duration_ms}ms{metrics_str}{error_str}")
                if description:
                    print(f"     描述: {description}")
            
            # 性能瓶颈分析
            bottlenecks = performance.get("bottlenecks", [])
            if bottlenecks:
                print()
                print("⚠️ 性能瓶颈（>1秒）:")
                for bottleneck in bottlenecks:
                    print(f"  - {bottleneck['stage']}: {bottleneck['duration_ms']}ms - {bottleneck['description']}")
            
            # 失败阶段
            failed_stages = performance.get("failed_stages", [])
            if failed_stages:
                print()
                print("❌ 失败的阶段:")
                for failed in failed_stages:
                    print(f"  - {failed['stage']}: {failed['error']}")
            
            print("=" * 80)
            print()
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_direct())

