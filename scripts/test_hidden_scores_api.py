#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试藏干数量对应分数配置表修改 - API测试
"""

import requests
import json


def test_bazi_calculate():
    """测试八字计算接口"""
    print("=" * 80)
    print("测试1: 八字计算接口（验证得地分使用新配置）")
    print("=" * 80)
    
    base_url = "http://127.0.0.1:8001"
    
    test_cases = [
        {"date": "1987-01-07", "time": "09:55", "gender": "male", "name": "测试案例1"},
        {"date": "1990-05-15", "time": "14:30", "gender": "male", "name": "测试案例2"},
        {"date": "1995-08-20", "time": "10:15", "gender": "female", "name": "测试案例3"},
    ]
    
    for case in test_cases:
        print(f"\n{case['name']}: {case['date']} {case['time']} ({case['gender']})")
        print("-" * 80)
        
        try:
            response = requests.post(
                f"{base_url}/api/v1/bazi/calculate",
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
                    wangshuai = data.get('data', {}).get('wangshuai', {})
                    print(f"✅ 计算成功")
                    print(f"  旺衰状态: {wangshuai.get('wangshuai')}")
                    print(f"  总分: {wangshuai.get('total_score')}")
                    scores = wangshuai.get('scores', {})
                    print(f"  得令分: {scores.get('de_ling')}")
                    de_di = scores.get('de_di')
                    print(f"  得地分: {de_di} (使用新配置)")
                    print(f"  得势分: {scores.get('de_shi')}")
                    
                    # 验证得地分是否为浮点数（如果使用了新配置）
                    if isinstance(de_di, float):
                        print(f"  ✅ 得地分使用了浮点数配置（新配置生效）")
                    elif de_di != 0:
                        print(f"  ⚠️  得地分为整数: {de_di}（可能未使用新配置）")
                    
                    print(f"  喜神五行: {wangshuai.get('xi_shen_elements', [])}")
                    print(f"  忌神五行: {wangshuai.get('ji_shen_elements', [])}")
                else:
                    print(f"❌ 计算失败: {data.get('error', '未知错误')}")
            else:
                print(f"❌ API返回错误: {response.status_code}")
                print(f"   响应: {response.text[:200]}")
                
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到API服务器，请确保服务已启动")
            return
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


def test_formula_analysis():
    """测试公式分析接口"""
    print("\n" + "=" * 80)
    print("测试2: 公式分析接口（验证规则匹配）")
    print("=" * 80)
    
    base_url = "http://127.0.0.1:8001"
    
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
                print("✅ 公式分析接口正常")
                result = data.get('data', {})
                print(f"  匹配规则数: {len(result.get('matched_rules', []))}")
                print(f"  旺衰状态: {result.get('wangshuai', {}).get('wangshuai')}")
            else:
                print(f"❌ 分析失败: {data.get('error', '未知错误')}")
        else:
            print(f"❌ API返回错误: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")


def test_smart_analyze():
    """测试智能分析接口"""
    print("\n" + "=" * 80)
    print("测试3: 智能分析接口（验证综合分析）")
    print("=" * 80)
    
    base_url = "http://127.0.0.1:8001"
    
    try:
        response = requests.get(
            f"{base_url}/api/v1/smart-analyze",
            params={
                "solar_date": "1987-01-07",
                "solar_time": "09:55",
                "gender": "male",
                "intent": "wealth"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 智能分析接口正常")
                result = data.get('data', {})
                print(f"  分析结果长度: {len(result.get('response', ''))}")
                print(f"  旺衰状态: {result.get('wangshuai', {}).get('wangshuai')}")
            else:
                print(f"❌ 分析失败: {data.get('error', '未知错误')}")
        else:
            print(f"❌ API返回错误: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    print("=" * 80)
    print("藏干数量对应分数配置表修改 - API测试")
    print("=" * 80)
    
    # 测试1: 八字计算
    test_bazi_calculate()
    
    # 测试2: 公式分析
    test_formula_analysis()
    
    # 测试3: 智能分析
    test_smart_analyze()
    
    print("\n" + "=" * 80)
    print("✅ 所有API测试完成")
    print("=" * 80)

