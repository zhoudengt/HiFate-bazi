#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能运势流式API
"""
import requests
import json
import sys

def test_scenario_1():
    """测试场景1：点击选择项 → 简短答复 + 预设问题列表"""
    print("=" * 80)
    print("测试场景1：点击选择项 → 简短答复 + 预设问题列表")
    print("=" * 80)
    
    url = "http://localhost:8001/api/v1/smart-fortune/smart-analyze-stream"
    params = {
        "category": "事业财富",
        "year": 1990,
        "month": 5,
        "day": 15,
        "hour": 14,
        "gender": "male",
        "user_id": "test_user_001"
    }
    
    print(f"请求URL: {url}")
    print(f"请求参数: {params}")
    print("\n开始接收SSE流...\n")
    
    try:
        response = requests.get(url, params=params, stream=True, timeout=30)
        response.raise_for_status()
        
        brief_response = ""
        preset_questions = None
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # 移除 'data: ' 前缀
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type', 'unknown')
                    
                    if event_type == 'brief_response_start':
                        print("✅ 收到 brief_response_start 事件")
                        brief_response = ""
                    elif event_type == 'brief_response_chunk':
                        content = data.get('content', '')
                        brief_response += content
                        print(f"📝 简短答复片段: {content[:50]}...")
                    elif event_type == 'brief_response_end':
                        print(f"\n✅ 简短答复完成（总长度: {len(brief_response)}字符）")
                        print(f"简短答复内容: {brief_response}\n")
                    elif event_type == 'preset_questions':
                        preset_questions = data.get('questions', [])
                        print(f"✅ 收到预设问题列表（{len(preset_questions)}个问题）")
                        for i, q in enumerate(preset_questions, 1):
                            print(f"  {i}. {q}")
                    elif event_type == 'error':
                        error_msg = data.get('message', '未知错误')
                        print(f"❌ 错误: {error_msg}")
                        break
                    elif event_type == 'end':
                        print("\n✅ 流式输出结束")
                        break
                    else:
                        print(f"📨 其他事件: {event_type}")
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON解析失败: {e}, 原始数据: {data_str[:100]}")
        
        print("\n" + "=" * 80)
        print("场景1测试结果:")
        print(f"  简短答复: {'✅ 已接收' if brief_response else '❌ 未接收'}")
        print(f"  预设问题: {'✅ 已接收' if preset_questions else '❌ 未接收'}")
        if preset_questions:
            print(f"  预设问题数量: {len(preset_questions)}")
        print("=" * 80)
        
        return brief_response and preset_questions
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scenario_2():
    """测试场景2：点击预设问题/输入问题 → 详细流式回答 + 3个相关问题"""
    print("\n" + "=" * 80)
    print("测试场景2：点击预设问题/输入问题 → 详细流式回答 + 3个相关问题")
    print("=" * 80)
    
    url = "http://localhost:8001/api/v1/smart-fortune/smart-analyze-stream"
    params = {
        "category": "事业财富",
        "question": "我的事业运势如何？",
        "user_id": "test_user_001"
        # 注意：场景2应该从会话缓存获取生辰信息，但如果没有缓存，需要提供
        # 这里先测试有缓存的情况
    }
    
    print(f"请求URL: {url}")
    print(f"请求参数: {params}")
    print("\n开始接收SSE流...\n")
    
    try:
        response = requests.get(url, params=params, stream=True, timeout=60)
        response.raise_for_status()
        
        detailed_response = ""
        related_questions = None
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # 移除 'data: ' 前缀
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type', 'unknown')
                    
                    if event_type == 'llm_start':
                        print("✅ 收到 llm_start 事件")
                        detailed_response = ""
                    elif event_type == 'llm_chunk':
                        content = data.get('content', '')
                        detailed_response += content
                        if len(detailed_response) < 200:  # 只打印前200字符
                            print(f"📝 详细回答片段: {content[:50]}...")
                    elif event_type == 'llm_end':
                        print(f"\n✅ 详细回答完成（总长度: {len(detailed_response)}字符）")
                        print(f"详细回答预览: {detailed_response[:200]}...\n")
                    elif event_type == 'related_questions':
                        related_questions = data.get('questions', [])
                        print(f"✅ 收到相关问题列表（{len(related_questions)}个问题）")
                        for i, q in enumerate(related_questions, 1):
                            print(f"  {i}. {q}")
                    elif event_type == 'error':
                        error_msg = data.get('message', '未知错误')
                        print(f"❌ 错误: {error_msg}")
                        break
                    elif event_type == 'end':
                        print("\n✅ 流式输出结束")
                        break
                    else:
                        if event_type not in ['status', 'basic_analysis', 'performance']:
                            print(f"📨 其他事件: {event_type}")
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON解析失败: {e}, 原始数据: {data_str[:100]}")
        
        print("\n" + "=" * 80)
        print("场景2测试结果:")
        print(f"  详细回答: {'✅ 已接收' if detailed_response else '❌ 未接收'}")
        print(f"  相关问题: {'✅ 已接收' if related_questions else '❌ 未接收'}")
        if related_questions:
            print(f"  相关问题数量: {len(related_questions)}")
        print("=" * 80)
        
        return detailed_response and related_questions
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("开始端到端测试...\n")
    
    # 测试场景1
    result1 = test_scenario_1()
    
    # 测试场景2（需要场景1先执行，以便创建会话缓存）
    result2 = test_scenario_2()
    
    print("\n" + "=" * 80)
    print("测试总结:")
    print(f"  场景1（点击选择项）: {'✅ 通过' if result1 else '❌ 失败'}")
    print(f"  场景2（点击预设问题）: {'✅ 通过' if result2 else '❌ 失败'}")
    print("=" * 80)
    
    sys.exit(0 if (result1 and result2) else 1)

