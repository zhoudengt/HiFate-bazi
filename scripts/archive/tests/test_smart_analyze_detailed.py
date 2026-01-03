#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细测试smart-analyze-stream的两个场景
"""
import requests
import json
import time

BASE_URL = "http://localhost:8001/api/v1/smart-fortune/smart-analyze-stream"

def test_scenario_1_detailed():
    """测试场景1：点击选择项"""
    print("\n" + "="*60)
    print("测试场景1：点击选择项（category有值，question为空）")
    print("="*60)
    
    params = {
        "category": "事业财富",
        "user_id": "test_user_001",
        "year": 1990,
        "month": 5,
        "day": 15,
        "hour": 14,
        "gender": "male"
    }
    
    print(f"\n请求参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.get(BASE_URL, params=params, stream=True, timeout=60)
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"错误: {response.text[:500]}")
            return False
        
        # 读取流式响应
        print("\n开始接收流式响应...")
        events = []
        full_content = ""
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    try:
                        data = json.loads(data_str)
                        events.append(data)
                        event_type = data.get('type', 'unknown')
                        
                        if event_type in ['brief_response_start', 'brief_response_chunk', 'brief_response_end']:
                            content = data.get('content', '')
                            if content:
                                full_content += content
                                print(f"  [{event_type}] {content[:50]}...")
                        elif event_type == 'preset_questions':
                            questions = data.get('questions', [])
                            print(f"\n  [预设问题] 共 {len(questions)} 个:")
                            for i, q in enumerate(questions[:5], 1):
                                print(f"    {i}. {q}")
                        elif event_type == 'error':
                            error_msg = data.get('message', data.get('error', '未知错误'))
                            print(f"\n  [错误] {error_msg}")
                            return False
                        elif event_type == 'end':
                            print("\n  [结束] 流式响应完成")
                            break
                    except json.JSONDecodeError as e:
                        print(f"  JSON解析失败: {data_str[:100]}")
                
                # 限制输出数量
                if len(events) >= 100:
                    print("\n... (限制输出)")
                    break
        
        print(f"\n✅ 场景1测试完成，收到 {len(events)} 个事件")
        print(f"简短答复内容长度: {len(full_content)} 字符")
        return True
        
    except Exception as e:
        print(f"\n❌ 场景1测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scenario_2_detailed():
    """测试场景2：点击预设问题/输入问题"""
    print("\n" + "="*60)
    print("测试场景2：点击预设问题/输入问题（category和question都有值）")
    print("="*60)
    
    # 先执行场景1，确保会话数据存在
    print("\n[步骤1] 先执行场景1，创建会话...")
    test_scenario_1_detailed()
    time.sleep(2)
    
    # 场景2：使用相同的user_id，传递question
    params = {
        "category": "事业财富",
        "user_id": "test_user_001",  # 使用相同的user_id
        "question": "我今年的事业运势如何？"
    }
    
    print(f"\n[步骤2] 请求参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.get(BASE_URL, params=params, stream=True, timeout=60)
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"错误: {response.text[:500]}")
            return False
        
        # 读取流式响应
        print("\n开始接收流式响应...")
        events = []
        full_content = ""
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    try:
                        data = json.loads(data_str)
                        events.append(data)
                        event_type = data.get('type', 'unknown')
                        
                        if event_type in ['analysis_start', 'analysis_chunk', 'analysis_end']:
                            content = data.get('content', '')
                            if content:
                                full_content += content
                                if len(full_content) < 200:
                                    print(f"  [{event_type}] {content[:50]}...")
                        elif event_type == 'related_questions':
                            questions = data.get('questions', [])
                            print(f"\n  [相关问题] 共 {len(questions)} 个:")
                            for i, q in enumerate(questions, 1):
                                print(f"    {i}. {q}")
                        elif event_type == 'error':
                            error_msg = data.get('message', data.get('error', '未知错误'))
                            print(f"\n  [错误] {error_msg}")
                            return False
                        elif event_type == 'end':
                            print("\n  [结束] 流式响应完成")
                            break
                    except json.JSONDecodeError as e:
                        print(f"  JSON解析失败: {data_str[:100]}")
                
                # 限制输出数量
                if len(events) >= 200:
                    print("\n... (限制输出)")
                    break
        
        print(f"\n✅ 场景2测试完成，收到 {len(events)} 个事件")
        print(f"详细回答内容长度: {len(full_content)} 字符")
        return True
        
    except Exception as e:
        print(f"\n❌ 场景2测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("="*60)
    print("Smart Analyze Stream 详细测试")
    print("="*60)
    
    # 测试场景1
    result1 = test_scenario_1_detailed()
    
    time.sleep(2)
    
    # 测试场景2
    result2 = test_scenario_2_detailed()
    
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"场景1: {'✅ 通过' if result1 else '❌ 失败'}")
    print(f"场景2: {'✅ 通过' if result2 else '❌ 失败'}")
    
    if result1 and result2:
        print("\n🎉 所有测试通过！")
        exit(0)
    else:
        print("\n⚠️ 部分测试失败，请检查")
        exit(1)

