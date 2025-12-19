#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证藏干数量对应分数配置表修改是否生效
"""

import requests
import json


def test_wangshuai_with_details():
    """测试旺衰计算，查看详细得分"""
    print("=" * 80)
    print("验证藏干数量对应分数配置表修改")
    print("=" * 80)
    
    base_url = "http://127.0.0.1:8001"
    
    test_cases = [
        {"date": "1987-01-07", "time": "09:55", "gender": "male", "name": "案例1"},
        {"date": "1990-05-15", "time": "14:30", "gender": "male", "name": "案例2"},
        {"date": "1995-08-20", "time": "10:15", "gender": "female", "name": "案例3"},
        {"date": "2000-03-10", "time": "08:00", "gender": "male", "name": "案例4"},
        {"date": "1985-11-25", "time": "16:45", "gender": "female", "name": "案例5"},
    ]
    
    print("\n测试旺衰计算接口，验证得地分是否使用新配置（浮点数）...")
    print("-" * 80)
    
    for case in test_cases:
        print(f"\n{case['name']}: {case['date']} {case['time']} ({case['gender']})")
        try:
            response = requests.post(
                f"{base_url}/api/v1/bazi/wangshuai",
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
                    scores = result.get('scores', {})
                    de_di = scores.get('de_di')
                    
                    print(f"  得令分: {scores.get('de_ling')}")
                    print(f"  得地分: {de_di} (类型: {type(de_di).__name__})")
                    print(f"  得势分: {scores.get('de_shi')}")
                    print(f"  总分: {result.get('total_score')}")
                    print(f"  旺衰状态: {result.get('wangshuai')}")
                    
                    # 验证得地分是否为浮点数（如果使用了新配置）
                    if isinstance(de_di, float):
                        print(f"  ✅ 得地分使用了浮点数配置（新配置生效）")
                        # 检查是否有小数部分
                        if de_di != int(de_di):
                            print(f"  ✅ 得地分包含小数部分，确认使用新配置")
                        else:
                            print(f"  ⚠️  得地分是整数，但类型为float（可能是巧合）")
                    else:
                        print(f"  ⚠️  得地分为整数类型: {de_di}")
                        print(f"  ⚠️  可能未使用新配置，或该案例的得地分恰好是整数")
                else:
                    print(f"  ❌ 计算失败: {data.get('error', '未知错误')}")
            else:
                print(f"  ❌ API返回错误: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
    
    print("\n" + "=" * 80)
    print("配置验证说明:")
    print("=" * 80)
    print("新配置值:")
    print("  1个藏干: 15/-15")
    print("  2个藏干: 10.5/-10.5, 4.5/-4.5")
    print("  3个藏干: 9/-9, 4.5/-4.5, 1.5/-1.5")
    print("\n如果得地分是浮点数（如 10.5, 4.5, 1.5 等），说明新配置已生效")
    print("如果得地分都是整数，可能是该案例的藏干匹配结果恰好是整数")


if __name__ == "__main__":
    test_wangshuai_with_details()
    
    print("\n" + "=" * 80)
    print("✅ 验证完成")
    print("=" * 80)
    print("\n💡 提示:")
    print("1. 如果看到浮点数得地分（如 10.5, 4.5, 1.5），说明新配置已生效")
    print("2. 如果都是整数，请检查服务是否已重新加载配置（可能需要重启或热更新）")
    print("3. 可以在浏览器中访问 http://127.0.0.1:8001/local_frontend/formula-analysis.html")
    print("   进行手动测试，验证前端功能是否正常")

