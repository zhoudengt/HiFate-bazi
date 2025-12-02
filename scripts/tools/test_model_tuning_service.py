#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型微调服务测试脚本
测试问题记录、训练批次创建等功能
"""
import sys
import os
import json

# ⭐ 设置测试环境（自动扩展虚拟环境路径）
from test_utils import setup_test_environment
project_root = setup_test_environment()

from server.services.intent_question_logger import get_question_logger
from services.model_tuning_service.service import ModelTuningService


def test_question_logging():
    """测试问题记录功能"""
    print("=" * 80)
    print("测试问题记录功能")
    print("=" * 80)
    
    logger = get_question_logger()
    
    # 模拟意图识别结果
    test_cases = [
        {
            "question": "今年适合投资吗？",
            "intent_result": {
                "intents": ["wealth"],
                "confidence": 0.95,
                "rule_types": ["FORMULA_WEALTH"],
                "time_intent": {"type": "this_year", "target_years": [2025]},
                "keywords": ["投资", "今年"],
                "method": "local_model",
                "response_time_ms": 40,
                "is_fortune_related": True,
                "is_ambiguous": False,
                "reasoning": "关键词分类：wealth"
            },
            "solar_date": "1990-05-15",
            "solar_time": "14:00",
            "gender": "male"
        },
        {
            "question": "我明年的财运怎么样？",
            "intent_result": {
                "intents": ["wealth"],
                "confidence": 0.85,
                "rule_types": ["FORMULA_WEALTH"],
                "time_intent": {"type": "next_year", "target_years": [2026]},
                "keywords": ["财运", "明年"],
                "method": "local_model",
                "response_time_ms": 35,
                "is_fortune_related": True,
                "is_ambiguous": False,
                "reasoning": "关键词分类：wealth"
            },
            "solar_date": "1990-05-15",
            "solar_time": "14:00",
            "gender": "male"
        }
    ]
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}/{len(test_cases)}: {test_case['question']}")
        success = logger.log_question(
            question=test_case['question'],
            intent_result=test_case['intent_result'],
            user_id="test_user",
            session_id="test_session_001",
            solar_date=test_case.get('solar_date'),
            solar_time=test_case.get('solar_time'),
            gender=test_case.get('gender')
        )
        
        if success:
            print(f"✅ 问题记录成功")
            success_count += 1
        else:
            print(f"❌ 问题记录失败")
    
    print(f"\n记录结果: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)


def test_get_unlabeled_questions():
    """测试获取未标注问题"""
    print("\n" + "=" * 80)
    print("测试获取未标注问题")
    print("=" * 80)
    
    logger = get_question_logger()
    questions = logger.get_unlabeled_questions(limit=10)
    
    print(f"获取到 {len(questions)} 条未标注问题")
    for i, q in enumerate(questions[:5], 1):
        print(f"\n问题 {i}:")
        print(f"  ID: {q.get('id')}")
        print(f"  问题: {q.get('question')}")
        print(f"  意图: {q.get('intents')}")
        print(f"  置信度: {q.get('confidence')}")
        print(f"  方法: {q.get('method')}")
    
    return len(questions) > 0


def test_training_service():
    """测试训练服务"""
    print("\n" + "=" * 80)
    print("测试训练服务")
    print("=" * 80)
    
    service = ModelTuningService()
    
    # 创建训练批次
    print("\n1. 创建训练批次...")
    result = service.create_training_batch(description="测试批次")
    if result.get("success"):
        batch_id = result.get("batch_id")
        print(f"✅ 批次创建成功: {batch_id}")
        return True
    else:
        print(f"❌ 批次创建失败: {result.get('error')}")
        return False


def test_keyword_extraction():
    """测试关键词提取"""
    print("\n" + "=" * 80)
    print("测试关键词提取")
    print("=" * 80)
    
    from services.model_tuning_service.keyword_extractor import KeywordRuleExtractor
    
    extractor = KeywordRuleExtractor()
    rules = extractor.extract_keywords_from_questions(min_confidence=0.8, limit=100)
    
    print(f"提取到 {len(rules)} 条关键词规则")
    for i, rule in enumerate(rules[:10], 1):
        print(f"\n规则 {i}:")
        print(f"  关键词: {rule['keyword']}")
        print(f"  意图: {rule['intent']}")
        print(f"  频率: {rule['frequency']}")
        print(f"  成功率: {rule['success_rate']:.2%}")
        print(f"  置信度加成: {rule['confidence_boost']:.2f}")
    
    return len(rules) > 0


if __name__ == "__main__":
    print("=" * 80)
    print("模型微调服务功能测试")
    print("=" * 80)
    
    # 测试1：问题记录
    test1_result = test_question_logging()
    
    # 测试2：获取未标注问题
    test2_result = test_get_unlabeled_questions()
    
    # 测试3：训练服务
    test3_result = test_training_service()
    
    # 测试4：关键词提取（需要先有数据）
    # test4_result = test_keyword_extraction()
    
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"问题记录: {'✅ 通过' if test1_result else '❌ 失败'}")
    print(f"获取未标注问题: {'✅ 通过' if test2_result else '❌ 失败'}")
    print(f"训练服务: {'✅ 通过' if test3_result else '❌ 失败'}")

