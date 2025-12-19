#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比生产环境和本地环境的规则匹配结果
"""

import sys
import os
import json
import requests
from typing import Dict, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def call_api(url: str, data: Dict) -> Dict:
    """调用 API"""
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        return {}


def compare_results(production_stats: Dict, local_stats: Dict):
    """对比结果"""
    print("\n" + "="*60)
    print("📊 对比结果")
    print("="*60)
    
    # 统计字段列表
    fields = [
        'total_matched', 'wealth_count', 'marriage_count', 'career_count',
        'children_count', 'character_count', 'summary_count', 'health_count',
        'peach_blossom_count', 'shishen_count', 'parents_count'
    ]
    
    print(f"\n{'字段':<20} {'生产环境':<15} {'本地环境':<15} {'差异':<15}")
    print("-" * 65)
    
    differences = []
    for field in fields:
        prod_val = production_stats.get(field, 0)
        local_val = local_stats.get(field, 0)
        diff = local_val - prod_val
        
        if diff != 0:
            differences.append((field, prod_val, local_val, diff))
            print(f"{field:<20} {prod_val:<15} {local_val:<15} {diff:+d}")
        else:
            print(f"{field:<20} {prod_val:<15} {local_val:<15} {'✓'}")
    
    if differences:
        print(f"\n⚠️  发现 {len(differences)} 个差异字段")
        print("\n💡 可能的原因:")
        print("  1. 数据库规则数量不一致")
        print("  2. 规则 enabled 状态不同")
        print("  3. 缓存影响（生产环境可能使用了旧缓存）")
        print("  4. 代码版本不一致")
        print("  5. 规则匹配逻辑差异")
    else:
        print("\n✅ 所有字段一致")


def main():
    """主函数"""
    print("="*60)
    print("🔍 生产环境 vs 本地环境规则匹配对比")
    print("="*60)
    
    # 测试数据
    test_data = {
        "solar_date": "1987-01-07",
        "solar_time": "09:00",
        "gender": "male"
    }
    
    # 1. 调用生产环境 API
    print("\n📡 调用生产环境 API...")
    prod_url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
    prod_response = call_api(prod_url, test_data)
    
    if not prod_response:
        print("❌ 无法获取生产环境数据")
        return
    
    prod_stats = prod_response.get('data', {}).get('statistics', {})
    print("✅ 生产环境数据获取成功")
    print(f"   总匹配数: {prod_stats.get('total_matched', 0)}")
    
    # 2. 调用本地环境 API（如果可用）
    print("\n📡 调用本地环境 API...")
    local_url = "http://localhost:8001/api/v1/bazi/formula-analysis"
    local_response = call_api(local_url, test_data)
    
    if not local_response:
        print("⚠️  本地服务未运行，跳过本地对比")
        print("\n💡 建议:")
        print("  1. 启动本地服务: python3 server/start.py")
        print("  2. 或直接检查生产环境数据库规则数量")
        return
    
    local_stats = local_response.get('data', {}).get('statistics', {})
    print("✅ 本地环境数据获取成功")
    print(f"   总匹配数: {local_stats.get('total_matched', 0)}")
    
    # 3. 对比结果
    compare_results(prod_stats, local_stats)
    
    # 4. 生成诊断建议
    print("\n" + "="*60)
    print("🔧 诊断建议")
    print("="*60)
    print("\n1. 检查生产环境数据库规则数量:")
    print("   ssh root@8.210.52.217")
    print("   docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi -e \\")
    print("     \"SELECT COUNT(*) FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%' AND enabled = 1;\"")
    
    print("\n2. 清除生产环境缓存:")
    print("   curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check")
    
    print("\n3. 检查生产环境代码版本:")
    print("   ssh root@8.210.52.217 'cd /opt/HiFate-bazi && git log --oneline -1'")
    
    print("\n4. 检查规则 enabled 状态:")
    print("   ssh root@8.210.52.217")
    print("   docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi -e \\")
    print("     \"SELECT rule_type, COUNT(*) as total, SUM(enabled) as enabled_count \\")
    print("      FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%' GROUP BY rule_type;\"")
    
    print("\n5. 如果规则数量一致但匹配结果不同，检查:")
    print("   - 规则匹配逻辑是否一致")
    print("   - 缓存是否影响")
    print("   - 八字计算是否一致")


if __name__ == '__main__':
    main()

