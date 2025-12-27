#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试总评分析接口（基于统一接口）
"""

import requests
import json

# 测试参数
test_params = {
    "solar_date": "1979-07-22",
    "solar_time": "07:30",
    "gender": "male"
}

print("=" * 80)
print("测试总评分析接口（基于统一接口）")
print("=" * 80)
print(f"测试参数: {json.dumps(test_params, ensure_ascii=False, indent=2)}")
print()

# 1. 测试调试接口
print("1️⃣ 测试调试接口 /general-review/debug...")
try:
    response = requests.post(
        "http://localhost:8001/api/v1/general-review/debug",
        json=test_params,
        timeout=30
    )
    response.raise_for_status()
    debug_data = response.json()
    
    if debug_data.get("success"):
        print("✅ 调试接口调用成功")
        print(f"   - input_data 存在: {'input_data' in debug_data}")
        print(f"   - prompt 存在: {'prompt' in debug_data}")
        print(f"   - prompt 长度: {len(debug_data.get('prompt', ''))}")
        
        # 检查关键数据
        input_data = debug_data.get("input_data", {})
        if input_data:
            print(f"   - 命盘核心格局: {'mingpan_hexin_geju' in input_data}")
            print(f"   - 性格特质: {'xingge_tezhi' in input_data}")
            print(f"   - 事业财运: {'shiye_caiyun' in input_data}")
            print(f"   - 关键大运: {'guanjian_dayun' in input_data}")
            
            # 检查特殊流年
            guanjian_dayun = input_data.get('guanjian_dayun', {})
            key_liunian = guanjian_dayun.get('key_liunian', [])
            print(f"   - 关键流年数量: {len(key_liunian)}")
            
            # 检查是否有2026, 2044, 2045, 2055年
            key_years = [2026, 2044, 2045, 2055]
            found_years = []
            for liunian in key_liunian:
                year = liunian.get('year')
                if year in key_years:
                    found_years.append(year)
            print(f"   - 关键年份检查: {found_years} / {key_years}")
    else:
        print(f"❌ 调试接口返回失败: {debug_data.get('error', '未知错误')}")
        
except Exception as e:
    print(f"❌ 调试接口调用失败: {e}")

print()

# 2. 测试流式接口（只测试前几个响应块）
print("2️⃣ 测试流式接口 /general-review/stream（前5个响应块）...")
try:
    response = requests.post(
        "http://localhost:8001/api/v1/general-review/stream",
        json=test_params,
        stream=True,
        timeout=30
    )
    response.raise_for_status()
    
    chunk_count = 0
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # 移除 'data: ' 前缀
                try:
                    chunk = json.loads(data_str)
                    chunk_type = chunk.get('type', 'unknown')
                    chunk_count += 1
                    
                    if chunk_count == 1:
                        print(f"✅ 收到第一个响应块，类型: {chunk_type}")
                    
                    if chunk_type == 'error':
                        print(f"❌ 收到错误响应: {chunk.get('content', '')}")
                        break
                    elif chunk_type == 'complete':
                        print(f"✅ 收到完成响应")
                        break
                    
                    if chunk_count >= 5:
                        print(f"✅ 已收到 {chunk_count} 个响应块，停止测试")
                        break
                except json.JSONDecodeError:
                    pass
                    
except Exception as e:
    print(f"❌ 流式接口调用失败: {e}")

print()
print("=" * 80)
print("测试完成")
print("=" * 80)

