#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试胎神功能API
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.services.calendar_api_service import CalendarAPIService

def test_taishen():
    """测试胎神功能"""
    print("=" * 60)
    print("测试胎神功能")
    print("=" * 60)
    
    # 创建服务实例
    service = CalendarAPIService()
    
    # 测试日期
    test_dates = [
        "2025-01-15",
        "2025-02-20",
        "2025-03-25",
    ]
    
    for date in test_dates:
        print(f"\n测试日期: {date}")
        print("-" * 60)
        
        result = service.get_calendar(date=date)
        
        if result.get('success'):
            deities = result.get('deities', {})
            taishen = deities.get('taishen', '')
            taishen_explanation = deities.get('taishen_explanation', '')
            
            print(f"✅ 胎神方位: {taishen}")
            print(f"✅ 胎神解释: {taishen_explanation}")
            
            # 验证格式
            if taishen:
                print(f"✅ 胎神格式正确: {taishen}")
            else:
                print("⚠️  胎神为空，可能库不支持或计算失败")
        else:
            print(f"❌ 获取万年历失败: {result.get('error')}")

if __name__ == '__main__':
    test_taishen()

