#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试格式定义加载器
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from server.config.input_format_loader import get_format_loader

def test_format_loader():
    """测试格式定义加载器"""
    print("🧪 测试格式定义加载器...")
    
    format_loader = get_format_loader()
    
    # 测试加载所有格式定义
    format_names = [
        'fortune_analysis_full',
        'fortune_analysis_minimal',
        'fortune_analysis_simple',
        'marriage_analysis',
        'career_wealth_analysis',
        'children_study_analysis',
        'health_analysis',
        'general_review_analysis',
        'qa_conversation'
    ]
    
    for format_name in format_names:
        print(f"\n📋 测试格式: {format_name}")
        format_def = format_loader.load_format(format_name)
        if format_def:
            print(f"  ✓ 格式定义加载成功")
            print(f"  - 意图: {format_def.get('intent')}")
            print(f"  - 类型: {format_def.get('format_type')}")
            print(f"  - 版本: {format_def.get('version')}")
            print(f"  - 字段数: {len(format_def.get('structure', {}).get('fields', {}))}")
        else:
            print(f"  ❌ 格式定义加载失败")
    
    print("\n✅ 测试完成")

if __name__ == '__main__':
    test_format_loader()

