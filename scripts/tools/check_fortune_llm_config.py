#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查智能运势分析 LLM 配置
"""

import os
import sys

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

# 检查环境变量
print("\n=== 环境变量检查 ===")
coze_token = os.getenv("COZE_ACCESS_TOKEN")
fortune_bot_id = os.getenv("FORTUNE_ANALYSIS_BOT_ID")
coze_bot_id = os.getenv("COZE_BOT_ID")

print(f"COZE_ACCESS_TOKEN: {'✓ 已设置' if coze_token else '✗ 缺失'}")
if coze_token:
    print(f"  Token前缀: {coze_token[:10]}...")

print(f"FORTUNE_ANALYSIS_BOT_ID: {'✓ 已设置' if fortune_bot_id else '✗ 缺失'}")
if fortune_bot_id:
    print(f"  Bot ID: {fortune_bot_id}")

print(f"COZE_BOT_ID: {'✓ 已设置' if coze_bot_id else '✗ 缺失'}")
if coze_bot_id:
    print(f"  Bot ID: {coze_bot_id}")

# 尝试初始化客户端
print("\n=== 客户端初始化检查 ===")
try:
    from server.services.fortune_llm_client import get_fortune_llm_client
    client = get_fortune_llm_client()
    print("✓ FortuneLLMClient 初始化成功")
    print(f"  Bot ID: {client.bot_id}")
    print(f"  API Base: {client.api_base}")
except ValueError as e:
    print(f"✗ 初始化失败: {e}")
    print("\n解决方案：")
    if "COZE_ACCESS_TOKEN" in str(e):
        print("  1. 在 .env 文件中添加: COZE_ACCESS_TOKEN=your_token")
    if "FORTUNE_ANALYSIS_BOT_ID" in str(e):
        print("  2. 在 .env 文件中添加: FORTUNE_ANALYSIS_BOT_ID=7576211240901509174")
except Exception as e:
    print(f"✗ 初始化异常: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 检查完成 ===")

