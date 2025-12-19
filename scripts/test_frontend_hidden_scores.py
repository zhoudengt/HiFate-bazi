#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端页面 - 验证藏干数量对应分数配置表修改
"""

import requests
import json
import time


def test_formula_analysis_page():
    """测试公式分析页面功能"""
    print("=" * 80)
    print("测试1: 公式分析页面功能")
    print("=" * 80)
    
    base_url = "http://127.0.0.1:8001"
    
    # 测试API接口
    print("\n测试公式分析API接口...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/bazi/formula-analysis",
            json={
                "solar_date": "1987-01-07",
                "solar_time": "09:55",
                "gender": "male"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                result = data.get('data', {})
                print("✅ 公式分析API正常")
                print(f"  匹配规则数: {len(result.get('matched_rules', []))}")
                
                # 检查旺衰信息
                wangshuai = result.get('wangshuai', {})
                if wangshuai:
                    print(f"  旺衰状态: {wangshuai.get('wangshuai')}")
                    print(f"  总分: {wangshuai.get('total_score')}")
                    scores = wangshuai.get('scores', {})
                    de_di = scores.get('de_di')
                    print(f"  得地分: {de_di}")
                    
                    # 验证得地分是否为浮点数（如果使用了新配置）
                    if isinstance(de_di, float):
                        print(f"  ✅ 得地分使用了浮点数配置（新配置生效）")
                    elif de_di is not None and de_di != 0:
                        print(f"  ⚠️  得地分为整数: {de_di}（可能未使用新配置）")
                else:
                    print("  ⚠️  未找到旺衰信息")
                
                # 检查统计信息
                statistics = result.get('statistics', {})
                if statistics:
                    print(f"  统计信息: {json.dumps(statistics, ensure_ascii=False, indent=2)}")
            else:
                print(f"❌ 分析失败: {data.get('error', '未知错误')}")
        else:
            print(f"❌ API返回错误: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_frontend_page_access():
    """测试前端页面访问"""
    print("\n" + "=" * 80)
    print("测试2: 前端页面访问")
    print("=" * 80)
    
    base_url = "http://127.0.0.1:8001"
    
    pages = [
        "/local_frontend/formula-analysis.html",
        "/local_frontend/index.html",
    ]
    
    for page in pages:
        print(f"\n测试页面: {page}")
        try:
            response = requests.get(f"{base_url}{page}", timeout=5)
            if response.status_code == 200:
                print(f"✅ 页面可访问")
                if "formula-analysis" in page:
                    # 检查页面是否包含关键元素
                    if "开始分析" in response.text or "analyzeBtn" in response.text:
                        print(f"  ✅ 页面包含关键元素")
            else:
                print(f"❌ 页面访问失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")


def test_multiple_cases():
    """测试多个案例"""
    print("\n" + "=" * 80)
    print("测试3: 多个案例测试（验证配置修改影响）")
    print("=" * 80)
    
    base_url = "http://127.0.0.1:8001"
    
    test_cases = [
        {"date": "1987-01-07", "time": "09:55", "gender": "male", "name": "案例1"},
        {"date": "1990-05-15", "time": "14:30", "gender": "male", "name": "案例2"},
        {"date": "1995-08-20", "time": "10:15", "gender": "female", "name": "案例3"},
    ]
    
    for case in test_cases:
        print(f"\n{case['name']}: {case['date']} {case['time']} ({case['gender']})")
        try:
            response = requests.post(
                f"{base_url}/api/v1/bazi/formula-analysis",
                json={
                    "solar_date": case['date'],
                    "solar_time": case['time'],
                    "gender": case['gender']
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    result = data.get('data', {})
                    wangshuai = result.get('wangshuai', {})
                    if wangshuai:
                        scores = wangshuai.get('scores', {})
                        de_di = scores.get('de_di')
                        print(f"  ✅ 得地分: {de_di} (类型: {type(de_di).__name__})")
                        if isinstance(de_di, float):
                            print(f"     ✅ 使用了浮点数配置")
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")


if __name__ == "__main__":
    print("=" * 80)
    print("前端页面测试 - 验证藏干数量对应分数配置表修改")
    print("=" * 80)
    
    # 测试1: 公式分析页面功能
    test_formula_analysis_page()
    
    # 测试2: 前端页面访问
    test_frontend_page_access()
    
    # 测试3: 多个案例测试
    test_multiple_cases()
    
    print("\n" + "=" * 80)
    print("✅ 所有前端测试完成")
    print("=" * 80)
    print("\n💡 提示: 请在浏览器中访问 http://127.0.0.1:8001/local_frontend/formula-analysis.html")
    print("   进行手动测试，验证页面功能是否正常")

