#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图识别性能测试脚本
测试修复后的性能改进
"""
import sys
import os
import time
import json

# ⭐ 设置测试环境（自动扩展虚拟环境路径）
from test_utils import setup_test_environment
project_root = setup_test_environment()

from services.intent_service.classifier import IntentClassifier


def test_intent_classification():
    """测试意图分类性能"""
    print("=" * 80)
    print("意图识别性能测试")
    print("=" * 80)
    print()
    
    classifier = IntentClassifier()
    
    test_cases = [
        {
            "question": "今年适合投资吗？",
            "expected_intent": "wealth",
            "expected_skip_llm": True
        },
        {
            "question": "我明年的财运怎么样？",
            "expected_intent": "wealth",
            "expected_skip_llm": True
        },
        {
            "question": "我后三年的财运如何？",
            "expected_intent": "wealth",
            "expected_skip_llm": True
        },
        {
            "question": "我的事业运势如何？",
            "expected_intent": "career",
            "expected_skip_llm": True
        },
        {
            "question": "我什么时候会结婚？",
            "expected_intent": "marriage",
            "expected_skip_llm": True
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}/{len(test_cases)}: {test_case['question']}")
        print("-" * 80)
        
        start_time = time.time()
        try:
            result = classifier.classify(test_case['question'], use_cache=False)
            elapsed_ms = (time.time() - start_time) * 1000
            
            intents = result.get("intents", [])
            confidence = result.get("confidence", 0)
            method = result.get("method", "unknown")
            time_intent = result.get("time_intent", {})
            skipped_llm = "llm_fallback" not in method
            
            print(f"✅ 分类成功")
            print(f"   意图: {intents}")
            print(f"   置信度: {confidence:.2f}")
            print(f"   方法: {method}")
            print(f"   时间意图: {time_intent.get('type', 'N/A')} - {time_intent.get('description', 'N/A')}")
            print(f"   耗时: {elapsed_ms:.0f}ms")
            print(f"   跳过LLM: {'✅ 是' if skipped_llm else '❌ 否'}")
            
            # 验证结果
            success = True
            if test_case['expected_skip_llm'] and not skipped_llm:
                print(f"   ⚠️ 警告: 期望跳过LLM，但实际调用了LLM")
                success = False
            if test_case['expected_intent'] not in intents:
                print(f"   ⚠️ 警告: 期望意图 {test_case['expected_intent']}，实际 {intents}")
                success = False
            
            results.append({
                "question": test_case['question'],
                "success": success,
                "elapsed_ms": elapsed_ms,
                "intents": intents,
                "confidence": confidence,
                "method": method,
                "skipped_llm": skipped_llm
            })
            
        except Exception as e:
            print(f"❌ 分类失败: {e}")
            results.append({
                "question": test_case['question'],
                "success": False,
                "error": str(e)
            })
    
    # 统计结果
    print("\n" + "=" * 80)
    print("测试结果统计")
    print("=" * 80)
    
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    skipped_llm_count = sum(1 for r in results if r.get("skipped_llm", False))
    avg_time = sum(r.get("elapsed_ms", 0) for r in results) / total if total > 0 else 0
    
    print(f"总测试数: {total}")
    print(f"成功数: {successful}")
    print(f"跳过LLM数: {skipped_llm_count}")
    print(f"平均耗时: {avg_time:.0f}ms")
    
    # 性能分析
    print("\n性能分析:")
    fast_results = [r for r in results if r.get("elapsed_ms", 0) < 100]
    medium_results = [r for r in results if 100 <= r.get("elapsed_ms", 0) < 500]
    slow_results = [r for r in results if r.get("elapsed_ms", 0) >= 500]
    
    print(f"  <100ms: {len(fast_results)} 个")
    print(f"  100-500ms: {len(medium_results)} 个")
    print(f"  >=500ms: {len(slow_results)} 个")
    
    if slow_results:
        print("\n⚠️ 慢请求:")
        for r in slow_results:
            print(f"  - {r['question']}: {r.get('elapsed_ms', 0):.0f}ms")
    
    return results


if __name__ == "__main__":
    test_intent_classification()

