#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后回归测试脚本
确保所有优化不影响现有功能
"""

import sys
import os
import requests
import json
from typing import Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

BASE_URL = "http://127.0.0.1:8001"

def test_formula_analysis():
    """测试算法公式分析API"""
    print("\n=== 测试算法公式分析 ===")
    url = f"{BASE_URL}/api/v1/bazi/formula-analysis"
    data = {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male",
        "rule_types": ["wealth", "marriage", "character"]
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        assert result.get("success") == True, "API应该返回成功"
        assert "data" in result, "应该包含data字段"
        assert "matched_rules" in result["data"], "应该包含matched_rules"
        assert "statistics" in result["data"], "应该包含statistics"
        
        print("✅ 算法公式分析API测试通过")
        return True
    except Exception as e:
        print(f"❌ 算法公式分析API测试失败: {e}")
        return False

def test_bazi_calculate():
    """测试八字计算API"""
    print("\n=== 测试八字计算 ===")
    url = f"{BASE_URL}/api/v1/bazi/calculate"
    data = {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male"
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        assert result.get("success") == True, "API应该返回成功"
        assert "data" in result, "应该包含data字段"
        
        print("✅ 八字计算API测试通过")
        return True
    except Exception as e:
        print(f"❌ 八字计算API测试失败: {e}")
        return False

def test_daily_fortune():
    """测试今日运势API"""
    print("\n=== 测试今日运势 ===")
    url = f"{BASE_URL}/api/v1/fortune/daily"
    params = {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        assert result.get("success") == True, "API应该返回成功"
        
        print("✅ 今日运势API测试通过")
        return True
    except Exception as e:
        print(f"❌ 今日运势API测试失败: {e}")
        return False

def test_rule_matching():
    """测试规则匹配API"""
    print("\n=== 测试规则匹配 ===")
    url = f"{BASE_URL}/api/v1/bazi/rules/match"
    data = {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male",
        "rule_types": ["wealth", "marriage"]
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        assert result.get("success") == True, "API应该返回成功"
        assert "matched_rules" in result, "应该包含matched_rules"
        
        print("✅ 规则匹配API测试通过")
        return True
    except Exception as e:
        print(f"❌ 规则匹配API测试失败: {e}")
        return False

def test_health_check():
    """测试健康检查"""
    print("\n=== 测试健康检查 ===")
    url = f"{BASE_URL}/health"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        assert result.get("status") == "ok", "健康检查应该返回ok"
        
        print("✅ 健康检查通过")
        return True
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("优化后回归测试")
    print("=" * 60)
    
    # 检查服务是否运行
    if not test_health_check():
        print("\n❌ 服务未运行，请先启动服务：python3 server/start.py")
        return False
    
    results = []
    
    # 运行所有测试
    results.append(("健康检查", test_health_check()))
    results.append(("八字计算", test_bazi_calculate()))
    results.append(("算法公式分析", test_formula_analysis()))
    results.append(("规则匹配", test_rule_matching()))
    results.append(("今日运势", test_daily_fortune()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！优化未影响现有功能。")
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
