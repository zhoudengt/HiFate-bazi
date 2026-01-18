#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旺衰分析功能测试脚本
"""

import sys
import os

# 添加项目根目录到路径（向上两级：tests/features -> 项目根目录）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from core.analyzers.wangshuai_analyzer import WangShuaiAnalyzer

def test_wangshuai():
    """测试旺衰分析"""
    print("=" * 60)
    print("旺衰分析功能测试")
    print("=" * 60)
    
    # 测试用例：1987-01-07 09:55 male
    solar_date = '1987-01-07'
    solar_time = '09:55'
    gender = 'male'
    
    print(f"\n📋 测试参数:")
    print(f"   日期: {solar_date}")
    print(f"   时间: {solar_time}")
    print(f"   性别: {gender}")
    print()
    
    try:
        analyzer = WangShuaiAnalyzer()
        result = analyzer.analyze(solar_date, solar_time, gender)
        
        print("\n" + "=" * 60)
        print("✅ 分析结果:")
        print("=" * 60)
        print(f"旺衰状态: {result['wangshuai']}")
        print(f"总分: {result['total_score']} 分")
        print(f"\n得分详情:")
        print(f"  得令分（月支权重）: {result['scores']['de_ling']} 分")
        print(f"  得地分（年日时支）: {result['scores']['de_di']} 分")
        print(f"  得势分（天干生扶）: {result['scores']['de_shi']} 分")
        print(f"\n喜神: {result['xi_shen']}")
        print(f"忌神: {result['ji_shen']}")
        print(f"\n喜神五行: {result['xi_shen_elements']}")
        print(f"忌神五行: {result['ji_shen_elements']}")
        print("\n" + "=" * 60)
        print("✅ 测试完成！")
        print("=" * 60)
        
        return result
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    test_wangshuai()

