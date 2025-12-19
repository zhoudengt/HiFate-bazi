#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试藏干数量对应分数配置表修改
验证配置修改后的计算结果
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.data.wangshuai_config import WangShuaiConfigLoader
from src.analyzers.wangshuai_analyzer import WangShuaiAnalyzer


def test_config_loading():
    """测试配置加载"""
    print("=" * 80)
    print("测试1: 配置加载")
    print("=" * 80)
    
    config_loader = WangShuaiConfigLoader()
    config = config_loader.config
    
    hidden_scores = config.get('hidden_scores', [])
    print(f"\n✅ 配置加载成功，共 {len(hidden_scores)} 条规则")
    
    for rule in hidden_scores:
        count = rule.get('藏干数量')
        print(f"\n藏干数量: {count}")
        print(f"  第1个匹配: {rule.get('第1个匹配')}, 第1个不匹配: {rule.get('第1个不匹配')}")
        if count >= 2:
            print(f"  第2个匹配: {rule.get('第2个匹配')}, 第2个不匹配: {rule.get('第2个不匹配')}")
        if count >= 3:
            print(f"  第3个匹配: {rule.get('第3个匹配')}, 第3个不匹配: {rule.get('第3个不匹配')}")
    
    # 验证合计
    print("\n验证合计:")
    for rule in hidden_scores:
        count = rule.get('藏干数量')
        total = 0
        for i in range(1, count + 1):
            total += rule.get(f'第{i}个匹配', 0)
        print(f"  藏干数量 {count}: 合计 = {total} (应为 15)")
        assert total == 15, f"藏干数量 {count} 的合计应为 15，实际为 {total}"
    
    print("\n✅ 配置验证通过")


def test_wangshuai_analysis():
    """测试旺衰分析（使用新配置）"""
    print("\n" + "=" * 80)
    print("测试2: 旺衰分析（使用新配置）")
    print("=" * 80)
    
    test_cases = [
        {"date": "1987-01-07", "time": "09:55", "gender": "male", "name": "测试案例1"},
        {"date": "1990-05-15", "time": "14:30", "gender": "male", "name": "测试案例2"},
        {"date": "1995-08-20", "time": "10:15", "gender": "female", "name": "测试案例3"},
    ]
    
    analyzer = WangShuaiAnalyzer()
    
    for case in test_cases:
        print(f"\n{case['name']}: {case['date']} {case['time']} ({case['gender']})")
        print("-" * 80)
        
        try:
            result = analyzer.analyze(case['date'], case['time'], case['gender'])
            
            print(f"✅ 分析成功")
            print(f"  旺衰状态: {result.get('wangshuai')}")
            print(f"  总分: {result.get('total_score')}")
            print(f"  得令分: {result.get('scores', {}).get('de_ling')}")
            print(f"  得地分: {result.get('scores', {}).get('de_di')} (使用新配置)")
            print(f"  得势分: {result.get('scores', {}).get('de_shi')}")
            print(f"  喜神: {result.get('xi_shen_elements', [])}")
            print(f"  忌神: {result.get('ji_shen_elements', [])}")
            
            # 验证得地分是否为浮点数（如果使用了新配置）
            de_di_score = result.get('scores', {}).get('de_di', 0)
            if isinstance(de_di_score, float):
                print(f"  ✅ 得地分使用了浮点数配置: {de_di_score}")
            else:
                print(f"  ⚠️  得地分为整数: {de_di_score}")
            
        except Exception as e:
            print(f"❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()


def test_api_endpoint():
    """测试API端点"""
    print("\n" + "=" * 80)
    print("测试3: API端点测试")
    print("=" * 80)
    
    import requests
    
    base_url = "http://127.0.0.1:8001"
    
    # 测试八字计算接口
    print("\n测试八字计算接口...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/bazi/calculate",
            json={
                "solar_date": "1987-01-07",
                "solar_time": "09:55",
                "gender": "male"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 八字计算接口正常")
            if 'wangshuai' in data:
                wangshuai = data['wangshuai']
                print(f"  旺衰状态: {wangshuai.get('wangshuai')}")
                print(f"  总分: {wangshuai.get('total_score')}")
                print(f"  得地分: {wangshuai.get('scores', {}).get('de_di')}")
        else:
            print(f"❌ API返回错误: {response.status_code}")
            print(f"   响应: {response.text}")
    except requests.exceptions.ConnectionError:
        print("⚠️  无法连接到API服务器，请确保服务已启动")
    except Exception as e:
        print(f"❌ API测试失败: {e}")


if __name__ == "__main__":
    print("=" * 80)
    print("藏干数量对应分数配置表修改测试")
    print("=" * 80)
    
    # 测试1: 配置加载
    test_config_loading()
    
    # 测试2: 旺衰分析
    test_wangshuai_analysis()
    
    # 测试3: API端点（可选）
    test_api_endpoint()
    
    print("\n" + "=" * 80)
    print("✅ 所有测试完成")
    print("=" * 80)

