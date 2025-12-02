#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能运势分析性能测试脚本
测试端到端流程并输出每个阶段的时间
"""
import sys
import os
import json
import time
import requests
from typing import Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")


def test_smart_analyze(
    question: str,
    year: int = 1990,
    month: int = 5,
    day: int = 15,
    hour: int = 12,
    gender: str = "male",
    include_fortune_context: bool = False
) -> Dict[str, Any]:
    """
    测试智能运势分析API
    
    Returns:
        包含性能摘要的完整结果
    """
    print("=" * 80)
    print(f"测试智能运势分析")
    print("=" * 80)
    print(f"问题: {question}")
    print(f"出生信息: {year}-{month:02d}-{day:02d} {hour:02d}:00, {gender}")
    print(f"包含流年大运: {include_fortune_context}")
    print("=" * 80)
    print()
    
    url = f"{BASE_URL}/api/v1/smart-fortune/smart-analyze"
    params = {
        "question": question,
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "gender": gender,
        "include_fortune_context": include_fortune_context
    }
    
    start_time = time.time()
    
    try:
        response = requests.get(url, params=params, timeout=60)
        total_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            # 提取性能摘要
            performance = result.get("performance", {})
            
            print("\n" + "=" * 80)
            print("📊 性能摘要")
            print("=" * 80)
            print(f"总耗时: {performance.get('total_duration_ms', 0)}ms ({performance.get('total_duration_sec', 0):.3f}s)")
            print(f"请求总耗时: {int(total_time * 1000)}ms ({total_time:.3f}s)")
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
            
            # 返回结果
            return {
                "success": True,
                "result": result,
                "performance": performance,
                "total_request_time_ms": int(total_time * 1000)
            }
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"响应: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "response": response.text
            }
    
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（>60秒）")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="智能运势分析性能测试")
    parser.add_argument("--question", "-q", type=str, default="我的财运怎么样？", help="用户问题")
    parser.add_argument("--year", "-y", type=int, default=1990, help="出生年份")
    parser.add_argument("--month", "-m", type=int, default=5, help="出生月份")
    parser.add_argument("--day", "-d", type=int, default=15, help="出生日期")
    parser.add_argument("--hour", "-H", type=int, default=12, help="出生时辰")
    parser.add_argument("--gender", "-g", type=str, default="male", choices=["male", "female"], help="性别")
    parser.add_argument("--fortune", "-f", action="store_true", help="包含流年大运分析")
    parser.add_argument("--url", "-u", type=str, default="http://127.0.0.1:8001", help="API基础URL")
    
    args = parser.parse_args()
    
    global BASE_URL
    BASE_URL = args.url
    
    # 执行测试
    result = test_smart_analyze(
        question=args.question,
        year=args.year,
        month=args.month,
        day=args.day,
        hour=args.hour,
        gender=args.gender,
        include_fortune_context=args.fortune
    )
    
    if result.get("success"):
        print("✅ 测试完成")
    else:
        print(f"❌ 测试失败: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

