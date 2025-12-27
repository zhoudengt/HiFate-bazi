#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
总评分析修复验证测试脚本
验证特殊流年和喜忌数据是否正确传递到 Coze Bot
"""

import requests
import json
import sys
import time

def test_general_review_stream():
    """测试总评分析流式接口"""
    url = "http://localhost:8001/api/v1/general-review/stream"
    
    payload = {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male"
    }
    
    print("=" * 80)
    print("总评分析修复验证测试")
    print("=" * 80)
    print(f"\n测试数据：{payload}\n")
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"❌ 请求失败：状态码 {response.status_code}")
            print(f"响应内容：{response.text}")
            return False
        
        print("✅ 请求成功，开始接收流式数据...\n")
        print("-" * 80)
        
        full_content = ""
        progress_count = 0
        complete_received = False
        error_received = False
        
        # 解析 SSE 流
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # 去掉 'data: ' 前缀
                try:
                    data = json.loads(data_str)
                    msg_type = data.get('type', '')
                    content = data.get('content', '')
                    
                    if msg_type == 'progress':
                        progress_count += 1
                        full_content += content
                        # 每100个进度消息打印一次
                        if progress_count % 100 == 0:
                            print(f"📊 已接收 {progress_count} 个进度消息...")
                    
                    elif msg_type == 'complete':
                        complete_received = True
                        full_content += content
                        print("\n✅ 收到完成消息")
                        print("-" * 80)
                        break
                    
                    elif msg_type == 'error':
                        error_received = True
                        print(f"\n❌ 收到错误消息：{content}")
                        print("-" * 80)
                        return False
                
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON 解析错误：{e}")
                    print(f"原始数据：{line_str}")
        
        print(f"\n📊 统计信息：")
        print(f"  - 进度消息数：{progress_count}")
        print(f"  - 完整内容长度：{len(full_content)} 字符")
        print(f"  - 是否完成：{complete_received}")
        print(f"  - 是否错误：{error_received}")
        
        # 验证关键内容
        print("\n" + "=" * 80)
        print("验证关键内容")
        print("=" * 80)
        
        checks = {
            "特殊流年（天克地冲）": ["天克地冲", "特殊流年"],
            "特殊流年（天合地合）": ["天合地合"],
            "特殊流年（岁运并临）": ["岁运并临"],
            "喜神五行": ["喜神五行", "喜用神"],
            "忌神五行": ["忌神五行", "忌神"],
        }
        
        all_passed = True
        for check_name, keywords in checks.items():
            found = any(keyword in full_content for keyword in keywords)
            status = "✅" if found else "❌"
            print(f"{status} {check_name}: {'找到' if found else '未找到'}")
            if not found:
                all_passed = False
        
        # 显示部分内容（用于验证）
        print("\n" + "=" * 80)
        print("内容预览（前500字符）")
        print("=" * 80)
        print(full_content[:500])
        print("...")
        
        # 检查是否包含特殊流年相关内容
        print("\n" + "=" * 80)
        print("特殊流年内容检查")
        print("=" * 80)
        
        # 查找特殊流年相关关键词
        special_keywords = ["天克地冲", "天合地合", "岁运并临", "特殊流年"]
        found_special = [kw for kw in special_keywords if kw in full_content]
        
        if found_special:
            print(f"✅ 找到特殊流年关键词：{', '.join(found_special)}")
            # 显示包含这些关键词的片段
            for keyword in found_special:
                idx = full_content.find(keyword)
                if idx >= 0:
                    snippet = full_content[max(0, idx-50):idx+200]
                    print(f"\n关键词 '{keyword}' 上下文：")
                    print(f"  ...{snippet}...")
        else:
            print("❌ 未找到特殊流年关键词")
            all_passed = False
        
        # 检查喜忌数据
        print("\n" + "=" * 80)
        print("喜忌数据检查")
        print("=" * 80)
        
        xishen_found = "喜神五行" in full_content or "喜用神" in full_content
        jishen_found = "忌神五行" in full_content or "忌神" in full_content
        
        print(f"{'✅' if xishen_found else '❌'} 喜神数据：{'找到' if xishen_found else '未找到'}")
        print(f"{'✅' if jishen_found else '❌'} 忌神数据：{'找到' if jishen_found else '未找到'}")
        
        if not xishen_found or not jishen_found:
            all_passed = False
        
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ 所有验证通过！修复成功！")
        else:
            print("❌ 部分验证失败，需要进一步检查")
        print("=" * 80)
        
        return all_passed
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时（120秒）")
        return False
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_general_review_stream()
    sys.exit(0 if success else 1)

