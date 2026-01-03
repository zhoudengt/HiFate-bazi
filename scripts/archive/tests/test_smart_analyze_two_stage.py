#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能运势分析两阶段交互流程
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
    
    print(f"\n请求URL: {url}")
    print(f"请求参数: {params}")
    print("\n开始接收SSE流...\n")
    
    try:
        response = requests.get(url, params=params, stream=True, timeout=60)
        response.raise_for_status()
        
        brief_response = ""
        preset_questions = None
        received_events = []
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            
            if line.startswith('event:'):
                event_type = line[6:].strip()
                received_events.append(event_type)
                
                if event_type == 'brief_response_start':
                    print("📝 开始接收简短答复...")
                elif event_type == 'brief_response_chunk':
                    pass  # 在data行处理
                elif event_type == 'brief_response_end':
                    print(f"\n✅ 简短答复完成（{len(brief_response)}字）")
                    print(f"内容: {brief_response[:200]}...")
                elif event_type == 'preset_questions':
                    print("\n📋 收到预设问题列表")
                elif event_type == 'error':
                    print("\n❌ 收到错误")
                elif event_type == 'end':
                    print("\n✅ 流式输出完成")
            
            elif line.startswith('data:'):
                data_str = line[5:].strip()
                try:
                    data = json.loads(data_str)
                    
                    if 'brief_response_chunk' in received_events[-1:]:
                        content = data.get('content', '')
                        if content:
                            brief_response += content
                            print(content, end='', flush=True)
                    
                    if 'preset_questions' in received_events[-1:]:
                        preset_questions = data.get('questions', [])
                        print(f"\n预设问题数量: {len(preset_questions)}")
                        for i, q in enumerate(preset_questions, 1):
                            print(f"  {i}. {q}")
                    
                    if 'error' in received_events[-1:]:
                        error_msg = data.get('message', '未知错误')
                        print(f"\n错误: {error_msg}")
                
                except json.JSONDecodeError:
                    pass
        
        print(f"\n\n收到的所有事件: {received_events}")
        
        # 验证结果
        assert 'brief_response_start' in received_events, "缺少brief_response_start事件"
        assert 'brief_response_end' in received_events, "缺少brief_response_end事件"
        assert 'preset_questions' in received_events, "缺少preset_questions事件"
        assert len(brief_response) > 0, "简短答复为空"
        assert preset_questions is not None, "预设问题列表为空"
        assert len(preset_questions) > 0, "预设问题列表为空"
        
        print("\n✅ 场景1测试通过！")
        return True, preset_questions
        
    except Exception as e:
        print(f"\n❌ 场景1测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_scenario_2(preset_question=None):
    """测试场景2：点击预设问题/输入问题 → 详细流式回答 + 3个相关问题"""
    print("\n" + "=" * 80)
    print("测试场景2：点击预设问题/输入问题 → 详细流式回答 + 3个相关问题")
    print("=" * 80)
    
    url = "http://localhost:8001/api/v1/smart-fortune/smart-analyze-stream"
    params = {
        "category": "事业财富",
        "question": preset_question or "我明年的财运怎么样？",
        "user_id": "test_user_001"
    }
    
    print(f"\n请求URL: {url}")
    print(f"请求参数: {params}")
    print("\n开始接收SSE流...\n")
    
    try:
        response = requests.get(url, params=params, stream=True, timeout=60)
        response.raise_for_status()
        
        full_response = ""
        related_questions = None
        received_events = []
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            
            if line.startswith('event:'):
                event_type = line[6:].strip()
                received_events.append(event_type)
                
                if event_type == 'llm_start':
                    print("📝 开始接收详细回答...")
                elif event_type == 'llm_chunk':
                    pass  # 在data行处理
                elif event_type == 'llm_end':
                    print(f"\n✅ 详细回答完成（{len(full_response)}字）")
                elif event_type == 'related_questions':
                    print("\n📋 收到相关问题列表")
                elif event_type == 'error':
                    print("\n❌ 收到错误")
                elif event_type == 'end':
                    print("\n✅ 流式输出完成")
            
            elif line.startswith('data:'):
                data_str = line[5:].strip()
                try:
                    data = json.loads(data_str)
                    
                    if 'llm_chunk' in received_events[-1:]:
                        content = data.get('content', '')
                        if content:
                            full_response += content
                            print(content, end='', flush=True)
                    
                    if 'related_questions' in received_events[-1:]:
                        related_questions = data.get('questions', [])
                        print(f"\n相关问题数量: {len(related_questions)}")
                        for i, q in enumerate(related_questions, 1):
                            print(f"  {i}. {q}")
                    
                    if 'error' in received_events[-1:]:
                        error_msg = data.get('message', '未知错误')
                        print(f"\n错误: {error_msg}")
                
                except json.JSONDecodeError:
                    pass
        
        print(f"\n\n收到的所有事件: {received_events}")
        
        # 验证结果
        assert 'llm_start' in received_events or 'llm_chunk' in received_events, "缺少LLM流式输出事件"
        assert len(full_response) > 0, "详细回答为空"
        assert related_questions is not None, "相关问题列表为空"
        assert len(related_questions) > 0, "相关问题列表为空"
        
        print("\n✅ 场景2测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 场景2测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("开始测试智能运势分析两阶段交互流程\n")
    
    # 测试场景1
    success1, preset_questions = test_scenario_1()
    
    if success1 and preset_questions:
        # 等待一下，确保会话已保存
        import time
        time.sleep(1)
        
        # 测试场景2（使用第一个预设问题）
        test_question = preset_questions[0] if preset_questions else "我明年的财运怎么样？"
        success2 = test_scenario_2(test_question)
        
        if success1 and success2:
            print("\n" + "=" * 80)
            print("✅ 所有测试通过！")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n" + "=" * 80)
            print("❌ 部分测试失败")
            print("=" * 80)
            sys.exit(1)
    else:
        print("\n" + "=" * 80)
        print("❌ 场景1测试失败，跳过场景2")
        print("=" * 80)
        sys.exit(1)

