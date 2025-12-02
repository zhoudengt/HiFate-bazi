#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能运势分析 LLM 功能
"""

import os
import sys
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 加载环境变量
try:
    from dotenv import load_dotenv
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"✓ 已加载环境变量文件: {env_path}")
    else:
        print(f"⚠️  环境变量文件不存在: {env_path}")
except ImportError:
    print("⚠️  python-dotenv 未安装，使用系统环境变量")

print("\n=== 测试 FortuneLLMClient ===")

try:
    from server.services.fortune_llm_client import get_fortune_llm_client
    
    print("1. 初始化客户端...")
    client = get_fortune_llm_client()
    print(f"   ✓ 初始化成功")
    print(f"   Bot ID: {client.bot_id}")
    print(f"   API Base: {client.api_base}")
    
    print("\n2. 测试流式调用...")
    
    # 构建测试数据
    test_input = {
        "intent": "wealth",
        "question": "我今年能发财吗？",
        "bazi": {
            "pillars": {
                "year": {"stem": "庚", "branch": "午"},
                "month": {"stem": "辛", "branch": "巳"},
                "day": {"stem": "庚", "branch": "辰"},
                "hour": {"stem": "癸", "branch": "未"}
            },
            "day_stem": "庚"
        },
        "liunian": {
            "year": 2025,
            "stem": "乙", "branch": "巳",
            "stem_element": "木", "branch_element": "火",
            "stem_shishen": "正财", "branch_shishen": "七杀",
            "balance_summary": "金(偏旺),火(偏旺)过旺；木(偏弱),水(极弱)不足",
            "relation_summary": "天干乙合庚，地支巳生辰"
        },
        "dayun": {
            "stem": "甲", "branch": "申"
        },
        "xi_ji": {
            "xi_shen": ["水", "木"],
            "ji_shen": ["火", "金"]
        },
        "wangshuai": "偏旺",
        "matched_rules": {
            "wealth": [
                "规则1：流年见正财，主财运",
                "规则2：身旺财弱，求财需努力"
            ]
        },
        "rules_count": {
            "wealth": 2,
            "career": 0,
            "health": 0
        }
    }
    
    print("   调用 analyze_fortune (stream=True)...")
    chunk_count = 0
    has_error = False
    
    for chunk in client.analyze_fortune(
        intent="wealth",
        question="我今年能发财吗？",
        bazi_data=test_input["bazi"],
        fortune_context={
            "time_analysis": {
                "liunian_list": [test_input["liunian"]],
                "dayun": test_input["dayun"]
            },
            "xi_ji": test_input["xi_ji"],
            "wangshuai": test_input["wangshuai"]
        },
        matched_rules=[{"rule_type": "wealth", "content": {"text": "测试规则"}}],
        stream=True
    ):
        chunk_type = chunk.get('type')
        chunk_count += 1
        
        if chunk_type == 'start':
            print(f"   ✓ 收到start事件")
        elif chunk_type == 'chunk':
            content = chunk.get('content', '')
            if content:
                print(f"   ✓ 收到chunk #{chunk_count}, 长度: {len(content)}字符")
                if chunk_count <= 3:
                    print(f"      内容预览: {content[:50]}...")
        elif chunk_type == 'end':
            print(f"   ✓ 收到end事件，共收到{chunk_count}个chunk")
            break
        elif chunk_type == 'error':
            error_msg = chunk.get('error', '未知错误')
            print(f"   ✗ 收到error事件: {error_msg}")
            has_error = True
            break
    
    if not has_error and chunk_count > 0:
        print(f"\n✅ 测试成功！共收到{chunk_count}个chunk")
    elif has_error:
        print(f"\n❌ 测试失败：收到错误事件")
    else:
        print(f"\n⚠️  测试异常：未收到任何chunk")
        
except ValueError as e:
    print(f"\n❌ 初始化失败: {e}")
    print("\n解决方案：")
    print("  在 .env 文件中添加:")
    print("  FORTUNE_ANALYSIS_BOT_ID=7576211240901509174")
except Exception as e:
    print(f"\n❌ 测试异常: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 测试完成 ===")

