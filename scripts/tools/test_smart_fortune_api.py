#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能运势分析API
"""

import sys
import os
import requests
import json
import time

# ⭐ 设置测试环境（自动扩展虚拟环境路径）
from test_utils import setup_test_environment
project_root = setup_test_environment()

def test_smart_fortune_stream():
    """测试流式API"""
    url = "http://localhost:8001/api/v1/smart-fortune/smart-analyze-stream"
    params = {
        "question": "我今年能发财吗",
        "year": 1990,
        "month": 1,
        "day": 15,
        "hour": 12,
        "gender": "male"
    }
    
    print("=" * 60)
    print("测试智能运势分析流式API")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"参数: {params}")
    print()
    
    try:
        # 使用stream=True接收SSE流
        response = requests.get(url, params=params, stream=True, timeout=120)
        
        print(f"HTTP状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print()
        
        if response.status_code != 200:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return
        
        print("📥 开始接收SSE流...")
        print("-" * 60)
        
        events_received = {
            'status': 0,
            'basic_analysis': 0,
            'llm_start': 0,
            'llm_chunk': 0,
            'llm_end': 0,
            'llm_error': 0,
            'error': 0,
            'end': 0
        }
        
        current_event = None
        buffer = ""
        
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            
            # SSE格式: "event: <event_type>" 或 "data: <json_data>"
            if line.startswith('event:'):
                current_event = line[6:].strip()
                print(f"\n📨 收到事件: {current_event}")
            elif line.startswith('data:'):
                data_str = line[5:].strip()
                try:
                    data = json.loads(data_str)
                    
                    if current_event:
                        events_received[current_event] = events_received.get(current_event, 0) + 1
                        
                        if current_event == 'status':
                            print(f"  stage: {data.get('stage')}, message: {data.get('message')}")
                            if data.get('stage') == 'llm':
                                print("  ⭐ 进入LLM阶段")
                        elif current_event == 'llm_start':
                            print("  ✅ LLM开始")
                        elif current_event == 'llm_chunk':
                            content = data.get('content', '')
                            if content:
                                print(f"  📝 收到chunk，长度: {len(content)}字符")
                                if len(content) < 100:
                                    print(f"  内容: {content[:100]}")
                        elif current_event == 'llm_end':
                            print("  ✅ LLM结束")
                        elif current_event == 'llm_error':
                            print(f"  ❌ LLM错误: {data.get('message')}")
                        elif current_event == 'error':
                            print(f"  ❌ 错误: {data.get('message')}")
                        elif current_event == 'end':
                            print("  ✅ 流结束")
                        
                        current_event = None
                except json.JSONDecodeError as e:
                    print(f"  ⚠️ JSON解析失败: {e}, 数据: {data_str[:100]}")
        
        print()
        print("-" * 60)
        print("📊 事件统计:")
        for event, count in events_received.items():
            if count > 0:
                print(f"  {event}: {count}次")
        
        print()
        if events_received['llm_start'] == 0 and events_received['llm_error'] == 0:
            print("⚠️ 问题：既没有收到llm_start，也没有收到llm_error")
        elif events_received['llm_error'] > 0:
            print("❌ 问题：收到了llm_error，但没有收到llm_start")
        elif events_received['llm_start'] > 0 and events_received['llm_chunk'] == 0:
            print("⚠️ 问题：收到了llm_start，但没有收到llm_chunk")
        else:
            print("✅ 看起来正常")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_smart_fortune_stream()

