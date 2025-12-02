#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试Coze API，查看实际返回格式
"""

import sys
import os
import json
import requests

# ⭐ 设置测试环境（自动扩展虚拟环境路径）
from test_utils import setup_test_environment
project_root = setup_test_environment()

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv('.env', override=True)
except:
    pass

# 尝试从config/services.env加载
services_env_path = 'config/services.env'
if os.path.exists(services_env_path):
    with open(services_env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[7:].strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key == 'FORTUNE_ANALYSIS_BOT_ID' and value:
                        os.environ['FORTUNE_ANALYSIS_BOT_ID'] = value
                    if key == 'COZE_ACCESS_TOKEN' and value:
                        os.environ['COZE_ACCESS_TOKEN'] = value

access_token = os.getenv("COZE_ACCESS_TOKEN")
bot_id = os.getenv("FORTUNE_ANALYSIS_BOT_ID")

print("=" * 60)
print("直接测试Coze API")
print("=" * 60)
print(f"Bot ID: {bot_id}")
print(f"Access Token: {access_token[:20] if access_token else 'None'}...")
print()

if not access_token or not bot_id:
    print("❌ 缺少环境变量")
    sys.exit(1)

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
        "stem_shishen": "正财", "branch_shishen": "七杀"
    },
    "dayun": {"stem": "甲", "branch": "申"},
    "xi_ji": {"xi_shen": ["水", "木"], "ji_shen": ["火", "金"]},
    "wangshuai": "偏旺",
    "matched_rules": {"wealth": ["规则1：测试规则"]},
    "rules_count": {"wealth": 1}
}

input_json = json.dumps(test_input, ensure_ascii=False)

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream'
}

payload = {
    'bot_id': bot_id,
    'user_id': 'system',
    'stream': True,
    'additional_messages': [
        {
            'role': 'user',
            'content': input_json,
            'content_type': 'text'
        }
    ]
}

print("📤 发送请求...")
print(f"URL: https://api.coze.cn/v3/chat")
print(f"Payload: {json.dumps(payload, ensure_ascii=False)[:200]}...")
print()

try:
    response = requests.post(
        "https://api.coze.cn/v3/chat",
        headers=headers,
        json=payload,
        stream=True,
        timeout=60
    )
    
    print(f"📥 响应状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    print()
    
    if response.status_code != 200:
        print(f"❌ 请求失败: {response.text}")
        sys.exit(1)
    
    print("📥 开始接收SSE流...")
    print("-" * 60)
    
    buffer = ""
    line_count = 0
    data_count = 0
    
    for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
        if not chunk:
            continue
        
        buffer += chunk
        lines = buffer.split('\n')
        buffer = lines[-1]
        
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
            
            line_count += 1
            
            if line.startswith('event:'):
                event_name = line[6:].strip()
                print(f"\n📨 事件: {event_name}")
            elif line.startswith('data:'):
                data_str = line[5:].strip()
                data_count += 1
                
                if data_str == '[DONE]':
                    print(f"  ✅ [DONE]")
                    break
                
                try:
                    data = json.loads(data_str)
                    print(f"  📦 数据 #{data_count}:")
                    print(f"     类型: {type(data)}")
                    print(f"     Keys: {list(data.keys())[:10]}")
                    print(f"     内容: {json.dumps(data, ensure_ascii=False)[:300]}")
                    
                    # 检查是否有content字段
                    if 'content' in data:
                        print(f"     ⭐ 发现content字段: {type(data['content'])}, 长度: {len(str(data['content']))}")
                    if 'delta' in data:
                        print(f"     ⭐ 发现delta字段: {type(data['delta'])}, 内容: {data['delta']}")
                    
                except json.JSONDecodeError as e:
                    print(f"  ⚠️ JSON解析失败: {e}")
                    print(f"     原始数据: {data_str[:200]}")
            
            if line_count > 100:  # 限制输出
                print("\n... (已输出100行，停止)")
                break
        
        if line_count > 100:
            break
    
    print()
    print("-" * 60)
    print(f"📊 统计: 共收到 {line_count} 行，{data_count} 个data事件")
    
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    traceback.print_exc()

