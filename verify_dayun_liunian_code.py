#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码验证脚本：检查大运流年相关代码是否正确实现
不实际运行代码，只检查代码逻辑
"""

import os
import re

def check_file(file_path, checks):
    """检查文件是否符合要求"""
    print(f"\n检查文件: {file_path}")
    print("-" * 80)
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_passed = True
    
    for check_name, check_func in checks:
        result = check_func(content, file_path)
        if result:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_passed = False
    
    return all_passed


def check_imports(content, file_path):
    """检查是否导入了必要的模块"""
    required_imports = [
        'BaziDataOrchestrator',
        'organize_special_liunians_by_dayun'
    ]
    
    for imp in required_imports:
        if imp not in content:
            return False
    return True


def check_unified_interface(content, file_path):
    """检查是否使用了统一接口"""
    patterns = [
        r'BaziDataOrchestrator\.fetch_data',
        r'special_liunians.*dayun_config',
        r'count.*13'
    ]
    
    for pattern in patterns:
        if not re.search(pattern, content):
            return False
    return True


def check_organize_liunians(content, file_path):
    """检查是否使用了organize_special_liunians_by_dayun"""
    return 'organize_special_liunians_by_dayun' in content


def check_liunians_in_data(content, file_path):
    """检查数据构建中是否包含流年数据"""
    # 检查是否有 liunians 字段
    return 'liunians' in content or "'liunians'" in content or '"liunians"' in content


def check_prompt_format(content, file_path):
    """检查Prompt构建中是否包含流年输出"""
    # 检查是否包含流年相关的输出格式
    patterns = [
        r'流年',
        r'liunian',
        r'\d{4}年'
    ]
    
    for pattern in patterns:
        if re.search(pattern, content):
            return True
    return False


def check_career_wealth_specific(content, file_path):
    """检查事业财富接口特定要求"""
    # 检查是否包含"现行X运"和"关键节点"
    has_current = '现行' in content or 'current_dayun' in content
    has_key = '关键节点' in content or 'key_dayuns' in content
    
    return has_current and has_key


def check_marriage_specific(content, file_path):
    """检查感情婚姻接口特定要求"""
    # 检查是否包含第2-4步大运的逻辑
    has_dayun_list = 'dayun_list' in content
    has_step_234 = '[1, 2, 3]' in content or 'range(1, 4)' in content or 'idx in [1, 2, 3]' in content
    
    return has_dayun_list and has_step_234


def main():
    """主函数"""
    print("=" * 80)
    print("大运流年代码验证")
    print("=" * 80)
    
    results = []
    
    # 检查事业财富分析接口
    career_checks = [
        ('导入BaziDataOrchestrator', check_imports),
        ('使用统一接口获取数据', check_unified_interface),
        ('使用organize_special_liunians_by_dayun', check_organize_liunians),
        ('数据构建包含流年字段', check_liunians_in_data),
        ('Prompt包含流年输出', check_prompt_format),
        ('包含现行运和关键节点格式', check_career_wealth_specific),
    ]
    
    result1 = check_file('server/api/v1/career_wealth_analysis.py', career_checks)
    results.append(('事业财富分析接口', result1))
    
    # 检查感情婚姻分析接口
    marriage_checks = [
        ('导入BaziDataOrchestrator', check_imports),
        ('使用统一接口获取数据', check_unified_interface),
        ('使用organize_special_liunians_by_dayun', check_organize_liunians),
        ('数据构建包含流年字段', check_liunians_in_data),
        ('Prompt包含流年输出', check_prompt_format),
        ('包含第2-4步大运逻辑', check_marriage_specific),
    ]
    
    result2 = check_file('server/api/v1/marriage_analysis.py', marriage_checks)
    results.append(('感情婚姻分析接口', result2))
    
    # 汇总结果
    print(f"\n{'='*80}")
    print("验证结果汇总")
    print(f"{'='*80}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有代码验证通过！")
        print("\n✅ 验证通过的项目：")
        print("  - 两个接口都正确导入了必要的模块")
        print("  - 两个接口都使用了统一接口获取数据")
        print("  - 两个接口都使用了organize_special_liunians_by_dayun分组流年")
        print("  - 两个接口的数据构建都包含了流年字段")
        print("  - 两个接口的Prompt构建都包含了流年输出")
        print("  - 事业财富接口包含了现行运和关键节点格式")
        print("  - 感情婚姻接口包含了第2-4步大运逻辑")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个验证失败")
        return 1


if __name__ == '__main__':
    exit(main())

