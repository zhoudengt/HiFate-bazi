#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能瓶颈分析脚本
详细分析智能运势分析API每个阶段的耗时
"""
import sys
import os
import time
import requests
import json

# ⭐ 设置测试环境（自动扩展虚拟环境路径）
from test_utils import setup_test_environment
project_root = setup_test_environment()

def analyze_performance():
    """分析性能瓶颈"""
    print("=" * 100)
    print("智能运势分析性能瓶颈分析")
    print("=" * 100)
    print()
    
    base_url = "http://127.0.0.1:8001"
    
    # 测试用例
    test_cases = [
        {
            "name": "基础分析（不含流年大运和LLM）",
            "params": {
                "question": "今年适合投资吗？",
                "year": 1990,
                "month": 5,
                "day": 15,
                "hour": 12,
                "gender": "male",
                "include_fortune_context": False
            }
        },
        {
            "name": "完整分析（含流年大运，不含LLM）",
            "params": {
                "question": "我明年的财运怎么样？",
                "year": 1990,
                "month": 5,
                "day": 15,
                "hour": 12,
                "gender": "male",
                "include_fortune_context": True
            }
        },
        {
            "name": "完整分析（含流年大运和LLM）",
            "params": {
                "question": "我后三年的财运如何？",
                "year": 1990,
                "month": 5,
                "day": 15,
                "hour": 12,
                "gender": "male",
                "include_fortune_context": True
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*100}")
        print(f"测试 {i}/{len(test_cases)}: {test_case['name']}")
        print(f"{'='*100}")
        print(f"问题: {test_case['params']['question']}")
        print()
        
        try:
            # 发送请求
            start_time = time.time()
            url = f"{base_url}/api/v1/smart-fortune/smart-analyze"
            response = requests.get(url, params=test_case['params'], timeout=60)
            total_time = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                print(f"❌ API调用失败: HTTP {response.status_code}")
                print(f"响应: {response.text}")
                continue
            
            result = response.json()
            
            if not result.get("success"):
                print(f"❌ API返回失败: {result.get('message', '未知错误')}")
                continue
            
            # 提取性能数据
            performance = result.get("performance", {})
            if not performance:
                print("⚠️ 未获取到性能数据")
                continue
            
            # 分析各阶段耗时
            print(f"总耗时: {total_time:.0f}ms ({total_time/1000:.2f}s)")
            print()
            print("各阶段详细耗时:")
            print("-" * 100)
            
            stages = performance.get("stages", [])
            stage_times = performance.get("stage_times", {})
            
            # 按耗时排序
            sorted_stages = sorted(
                stages,
                key=lambda x: x.get("duration_ms", 0),
                reverse=True
            )
            
            total_stage_time = 0
            for stage in sorted_stages:
                stage_name = stage.get("stage", "unknown")
                duration_ms = stage.get("duration_ms", 0)
                duration_sec = stage.get("duration_sec", 0)
                success = stage.get("success", True)
                description = stage.get("description", "")
                
                status = "✅" if success else "❌"
                percentage = (duration_ms / total_time * 100) if total_time > 0 else 0
                
                print(f"{status} {stage_name:30s} | {duration_ms:6d}ms ({duration_sec:6.3f}s) | {percentage:5.1f}% | {description}")
                
                total_stage_time += duration_ms
                
                # 显示指标
                metrics = {k: v for k, v in stage.items() if k.startswith("metric_")}
                if metrics:
                    for metric_name, metric_value in metrics.items():
                        print(f"    └─ {metric_name.replace('metric_', '')}: {metric_value}")
            
            print("-" * 100)
            print(f"阶段总耗时: {total_stage_time:.0f}ms")
            print(f"其他耗时: {total_time - total_stage_time:.0f}ms (网络传输、序列化等)")
            print()
            
            # 性能瓶颈分析
            bottlenecks = performance.get("bottlenecks", [])
            if bottlenecks:
                print("⚠️ 性能瓶颈（>1秒）:")
                for bottleneck in bottlenecks:
                    print(f"  - {bottleneck['stage']}: {bottleneck['duration_ms']}ms - {bottleneck['description']}")
                print()
            
            # 失败阶段
            failed_stages = performance.get("failed_stages", [])
            if failed_stages:
                print("❌ 失败的阶段:")
                for failed in failed_stages:
                    print(f"  - {failed['stage']}: {failed.get('error', '未知错误')}")
                print()
            
            # 性能建议
            print("💡 性能优化建议:")
            suggestions = []
            
            for stage in sorted_stages:
                duration_ms = stage.get("duration_ms", 0)
                stage_name = stage.get("stage", "")
                
                if stage_name == "intent_recognition" and duration_ms > 100:
                    suggestions.append(f"- 意图识别耗时 {duration_ms}ms，建议检查是否调用了LLM（应该<100ms）")
                
                if stage_name == "bazi_calculation" and duration_ms > 100:
                    suggestions.append(f"- 八字计算耗时 {duration_ms}ms，建议检查是否使用了gRPC微服务（应该<50ms）")
                
                if stage_name == "rule_matching" and duration_ms > 500:
                    suggestions.append(f"- 规则匹配耗时 {duration_ms}ms，建议优化数据库查询或添加缓存（应该<200ms）")
                
                if stage_name == "fortune_context" and duration_ms > 2000:
                    suggestions.append(f"- 流年大运分析耗时 {duration_ms}ms，建议优化数据库查询或添加缓存（应该<1000ms）")
                
                if stage_name == "llm_analysis" and duration_ms > 5000:
                    suggestions.append(f"- LLM深度解读耗时 {duration_ms}ms，这是正常现象，但可以考虑使用流式输出提升用户体验")
            
            if suggestions:
                for suggestion in suggestions:
                    print(suggestion)
            else:
                print("- 各阶段耗时都在合理范围内")
            
            print()
            
        except requests.exceptions.Timeout:
            print(f"❌ 请求超时（>60秒）")
        except requests.exceptions.ConnectionError:
            print(f"❌ 连接失败，请确保服务已启动在 {base_url}")
        except Exception as e:
            print(f"❌ 发生异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("=" * 100)
    print("分析完成")
    print("=" * 100)


if __name__ == "__main__":
    analyze_performance()

