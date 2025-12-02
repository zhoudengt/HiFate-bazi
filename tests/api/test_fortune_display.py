#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试大运流年流月显示接口
"""

import requests
import json
import sys

# API配置
BASE_URL = "http://127.0.0.1:8001/api/v1"
TOKEN = None

# 尝试从文件读取token
try:
    with open('.token', 'r') as f:
        TOKEN = f.read().strip()
except:
    pass

def test_fortune_display():
    """测试大运流年流月接口"""
    
    url = f"{BASE_URL}/bazi/fortune/display"
    
    # 测试数据
    data = {
        "solar_date": "1987-09-16",
        "solar_time": "05:00",
        "gender": "male",
        "current_time": "2025-01-17 10:00"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    
    print("=" * 60)
    print("测试大运流年流月接口")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        print(f"状态码: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print("✅ 接口调用成功！")
                print()
                
                # 检查大运数据
                dayun = result.get('dayun', {})
                print(f"大运数据:")
                print(f"  - 当前大运: {dayun.get('current', {}).get('ganzhi', 'N/A')}")
                print(f"  - 大运列表数量: {len(dayun.get('list', []))}")
                
                if dayun.get('list'):
                    print(f"  - 前3个大运:")
                    for i, item in enumerate(dayun.get('list', [])[:3]):
                        ganzhi = item.get('ganzhi', '')
                        age = item.get('age_display', '')
                        year_range = item.get('year_range', {})
                        print(f"    {i+1}. {ganzhi} ({age}) {year_range.get('start', '')}-{year_range.get('end', '')}")
                
                print()
                
                # 检查流年数据
                liunian = result.get('liunian', {})
                print(f"流年数据:")
                print(f"  - 当前流年: {liunian.get('current', {}).get('year', 'N/A')}")
                print(f"  - 流年列表数量: {len(liunian.get('list', []))}")
                
                if liunian.get('list'):
                    print(f"  - 前5个流年:")
                    for i, item in enumerate(liunian.get('list', [])[:5]):
                        year = item.get('year', '')
                        ganzhi = item.get('ganzhi', '')
                        print(f"    {i+1}. {year}年 {ganzhi}")
                
                print()
                
                # 检查流月数据
                liuyue = result.get('liuyue', {})
                print(f"流月数据:")
                print(f"  - 当前流月: {liuyue.get('current', {}).get('month', 'N/A')}")
                print(f"  - 流月列表数量: {len(liuyue.get('list', []))}")
                
                if liuyue.get('list'):
                    print(f"  - 前3个流月:")
                    for i, item in enumerate(liuyue.get('list', [])[:3]):
                        month = item.get('month', '')
                        ganzhi = item.get('ganzhi', '')
                        solar_term = item.get('solar_term', '')
                        print(f"    {i+1}. {month}月 {solar_term} {ganzhi}")
                
                print()
                print("✅ 数据验证通过！")
                return True
            else:
                print(f"❌ 接口返回失败: {result.get('error', '未知错误')}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确保后端服务正在运行")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fortune_display()
    sys.exit(0 if success else 1)

