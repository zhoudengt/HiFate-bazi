#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能运势分析流式输出接口
"""

import sys
import os
import requests
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_smart_fortune_stream(base_url="http://127.0.0.1:8001"):
    """
    测试智能运势分析流式输出接口
    
    Args:
        base_url: API基础URL
    """
    url = f"{base_url}/api/v1/smart-fortune/smart-analyze-stream"
    
    # 测试参数
    params = {
        "question": "我今年的财运如何",
        "year": 1990,
        "month": 1,
        "day": 15,
        "hour": 12,
        "gender": "male",
        "user_id": "test_user_001"
    }
    
    print("=" * 80)
    print("智能运势分析流式输出接口测试")
    print("=" * 80)
    print(f"请求URL: {url}")
    print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n请求参数:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    print("\n" + "=" * 80)
    print("开始接收流式响应...\n")
    
    try:
        # 发送流式请求
        response = requests.get(url, params=params, stream=True, timeout=120)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"响应头 Cache-Control: {response.headers.get('Cache-Control', 'N/A')}")
        print(f"响应头 Connection: {response.headers.get('Connection', 'N/A')}")
        print("\n" + "-" * 80)
        
        if response.status_code != 200:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            return
        
        # 解析SSE流
        event_count = 0
        chunk_count = 0
        total_content_length = 0
        current_event = None
        
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            
            # SSE格式: "event: xxx" 或 "data: {...}"
            if line.startswith("event:"):
                current_event = line[6:].strip()
                print(f"\n📨 收到事件: {current_event}")
                event_count += 1
            elif line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    data = json.loads(data_str)
                    
                    if current_event == "status":
                        stage = data.get("stage", "unknown")
                        message = data.get("message", "")
                        print(f"  📊 状态更新: {stage} - {message}")
                    elif current_event == "basic_analysis":
                        print(f"  ✅ 基础分析完成")
                        print(f"     - 意图: {data.get('intent', {}).get('intents', [])}")
                        print(f"     - 匹配规则数: {data.get('matched_rules_count', 0)}")
                    elif current_event == "llm_start":
                        print(f"  🚀 LLM流式输出开始")
                    elif current_event == "llm_chunk":
                        content = data.get("content", "")
                        if content:
                            chunk_count += 1
                            total_content_length += len(content)
                            print(f"  📝 Chunk #{chunk_count}: {len(content)}字符 - {content[:50]}...")
                    elif current_event == "llm_end":
                        print(f"  ✅ LLM流式输出完成")
                        print(f"     - 总chunk数: {chunk_count}")
                        print(f"     - 总长度: {total_content_length}字符")
                    elif current_event == "llm_error":
                        error_msg = data.get("message", "未知错误")
                        print(f"  ❌ LLM错误: {error_msg}")
                    elif current_event == "performance":
                        print(f"  📊 性能摘要:")
                        stages = data.get("stages", [])
                        for stage in stages:
                            name = stage.get("name", "unknown")
                            duration = stage.get("duration_ms", 0)
                            success = stage.get("success", False)
                            status = "✅" if success else "❌"
                            print(f"     {status} {name}: {duration}ms")
                    elif current_event == "end":
                        print(f"  🏁 流式输出结束")
                    elif current_event == "error":
                        error_msg = data.get("message", "未知错误")
                        print(f"  ❌ 错误: {error_msg}")
                    else:
                        print(f"  📦 数据: {json.dumps(data, ensure_ascii=False)[:200]}...")
                
                except json.JSONDecodeError as e:
                    print(f"  ⚠️ JSON解析失败: {e}")
                    print(f"  原始数据: {data_str[:200]}")
        
        print("\n" + "=" * 80)
        print(f"测试完成!")
        print(f"  - 总事件数: {event_count}")
        print(f"  - LLM chunk数: {chunk_count}")
        print(f"  - 总内容长度: {total_content_length}字符")
        print("=" * 80)
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时（120秒）")
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确保服务正在运行")
        print(f"   尝试连接: {base_url}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试智能运势分析流式输出接口")
    parser.add_argument("--url", default="http://127.0.0.1:8001", help="API基础URL")
    args = parser.parse_args()
    
    test_smart_fortune_stream(args.url)

