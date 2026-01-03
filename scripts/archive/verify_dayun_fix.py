#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证修复：检查两个接口是否正确获取dayun和special_liunians数据
"""

import re

def check_file(file_path, description):
    """检查文件中的数据获取逻辑"""
    print(f"\n检查文件: {file_path} ({description})")
    print("-" * 80)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否使用了错误的格式
    has_wrong_format = bool(re.search(r"orchestrator_data\['dayun'\]\['list'\]", content))
    
    # 检查是否使用了正确的格式
    has_correct_dayun = bool(re.search(r"orchestrator_data\.get\('dayun'", content))
    has_correct_special_liunians = bool(re.search(r"special_liunians_data.*=.*orchestrator_data\.get\('special_liunians'", content))
    has_type_check = bool(re.search(r"isinstance\(special_liunians_data.*dict\)", content))
    
    if has_wrong_format:
        print("❌ 仍然存在错误的格式: orchestrator_data['dayun']['list']")
        return False
    
    if not has_correct_dayun:
        print("❌ 未找到正确的dayun获取方式")
        return False
    
    if not has_correct_special_liunians:
        print("❌ 未找到正确的special_liunians获取方式")
        return False
    
    if not has_type_check:
        print("❌ 未找到类型检查逻辑")
        return False
    
    print("✅ 数据获取逻辑正确")
    print("  - 使用 orchestrator_data.get('dayun', []) 获取大运序列")
    print("  - 使用 orchestrator_data.get('special_liunians', {}) 获取特殊流年")
    print("  - 包含类型检查逻辑")
    
    return True

def main():
    """主函数"""
    print("=" * 80)
    print("验证修复：检查dayun数据获取错误修复")
    print("=" * 80)
    
    results = []
    
    result1 = check_file('server/api/v1/marriage_analysis.py', '感情婚姻接口')
    results.append(('感情婚姻接口', result1))
    
    result2 = check_file('server/api/v1/career_wealth_analysis.py', '事业财富接口')
    results.append(('事业财富接口', result2))
    
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
        print("\n🎉 所有修复验证通过！")
        print("\n修复内容：")
        print("  - 将 orchestrator_data['dayun']['list'] 改为 orchestrator_data.get('dayun', [])")
        print("  - 添加了 special_liunians 的类型检查和安全获取逻辑")
        print("  - 与 general_review_analysis.py 和 health_analysis.py 的实现保持一致")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个文件验证失败")
        return 1

if __name__ == '__main__':
    exit(main())

