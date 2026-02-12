#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

QA 多轮对话系统集成测试
测试完整对话流程、问题生成、流式处理、多轮对话意图理解
"""

import pytest; pytest.importorskip("grpc", reason="grpc not installed")
import sys
import os
import asyncio
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.services.qa_conversation_service import QAConversationService
from server.services.qa_question_generator import QAQuestionGenerator


async def test_start_conversation():
    """测试开始对话"""
    print("\n" + "=" * 60)
    print("测试1: 开始对话")
    print("=" * 60)
    
    service = QAConversationService()
    result = await service.start_conversation(
        user_id="test_user",
        solar_date="1990-05-15",
        solar_time="14:30",
        gender="male"
    )
    
    print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    assert result['success'] == True
    assert 'session_id' in result
    assert 'initial_question' in result
    assert 'categories' in result
    
    print("✅ 测试1通过")
    return result['session_id']


async def test_get_category_questions():
    """测试获取分类问题"""
    print("\n" + "=" * 60)
    print("测试2: 获取分类问题")
    print("=" * 60)
    
    service = QAConversationService()
    questions = await service.get_category_questions('career_wealth')
    
    print(f"问题数量: {len(questions)}")
    if questions:
        print(f"第一个问题: {questions[0]}")
    
    assert isinstance(questions, list)
    print("✅ 测试2通过")
    return questions


async def test_ask_question(session_id: str):
    """测试提问（流式）"""
    print("\n" + "=" * 60)
    print("测试3: 提问（流式）")
    print("=" * 60)
    
    service = QAConversationService()
    question = "我想了解一下我的事业运势"
    
    print(f"问题: {question}")
    print("流式响应:")
    
    chunks = []
    async for chunk in service.ask_question(session_id, question):
        chunks.append(chunk)
        chunk_type = chunk.get('type', 'unknown')
        content = chunk.get('content', '')
        
        if chunk_type == 'progress':
            print(f"  [进度] {content[:50]}...")
        elif chunk_type == 'complete':
            print(f"  [完成] {content[:50]}...")
        elif chunk_type == 'questions_before':
            print(f"  [提问前问题] {content}")
        elif chunk_type == 'questions_after':
            print(f"  [答案后问题] {content}")
        elif chunk_type == 'error':
            print(f"  [错误] {content}")
            break
    
    assert len(chunks) > 0
    print(f"✅ 测试3通过（收到 {len(chunks)} 个响应块）")
    return chunks


async def test_multi_turn_conversation():
    """测试多轮对话"""
    print("\n" + "=" * 60)
    print("测试4: 多轮对话")
    print("=" * 60)
    
    service = QAConversationService()
    
    # 1. 开始对话
    start_result = await service.start_conversation(
        user_id="test_user",
        solar_date="1990-05-15",
        solar_time="14:30",
        gender="male"
    )
    session_id = start_result['session_id']
    
    # 2. 第一轮提问
    print("\n第一轮提问:")
    question1 = "我想了解一下我的事业运势"
    chunks1 = []
    async for chunk in service.ask_question(session_id, question1):
        chunks1.append(chunk)
        if chunk.get('type') == 'error':
            print(f"  错误: {chunk.get('content')}")
            break
    
    # 3. 第二轮提问（基于第一轮的上下文）
    print("\n第二轮提问（基于上下文）:")
    question2 = "那我适合在哪个城市发展？"
    chunks2 = []
    async for chunk in service.ask_question(session_id, question2):
        chunks2.append(chunk)
        if chunk.get('type') == 'error':
            print(f"  错误: {chunk.get('content')}")
            break
    
    assert len(chunks1) > 0
    assert len(chunks2) > 0
    print(f"✅ 测试4通过（第一轮: {len(chunks1)} 个响应块，第二轮: {len(chunks2)} 个响应块）")


async def test_question_generator():
    """测试问题生成"""
    print("\n" + "=" * 60)
    print("测试5: 问题生成")
    print("=" * 60)
    
    generator = QAQuestionGenerator()
    
    # 测试提问后生成问题
    questions_before = await generator.generate_questions_after_question(
        user_question="我想了解一下我的事业运势",
        bazi_data={
            'bazi_pillars': {
                'year': {'stem': '庚', 'branch': '午'},
                'month': {'stem': '辛', 'branch': '巳'},
                'day': {'stem': '甲', 'branch': '子'},
                'hour': {'stem': '乙', 'branch': '丑'}
            }
        },
        intent_result={'intents': ['career']},
        conversation_history=[]
    )
    
    print(f"提问后生成的问题: {questions_before}")
    assert isinstance(questions_before, list)
    assert len(questions_before) <= 3
    
    # 测试答案后生成问题
    questions_after = await generator.generate_questions_after_answer(
        user_question="我想了解一下我的事业运势",
        answer="根据您的八字分析，您的事业运势...",
        bazi_data={
            'bazi_pillars': {
                'year': {'stem': '庚', 'branch': '午'},
                'month': {'stem': '辛', 'branch': '巳'},
                'day': {'stem': '甲', 'branch': '子'},
                'hour': {'stem': '乙', 'branch': '丑'}
            }
        },
        intent_result={'intents': ['career']},
        conversation_history=[]
    )
    
    print(f"答案后生成的问题: {questions_after}")
    assert isinstance(questions_after, list)
    assert len(questions_after) <= 3
    
    print("✅ 测试5通过")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("QA 多轮对话系统集成测试")
    print("=" * 60)
    
    try:
        # 测试1: 开始对话
        session_id = await test_start_conversation()
        
        # 测试2: 获取分类问题
        await test_get_category_questions()
        
        # 测试3: 提问（流式）
        await test_ask_question(session_id)
        
        # 测试4: 多轮对话
        await test_multi_turn_conversation()
        
        # 测试5: 问题生成
        await test_question_generator()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

