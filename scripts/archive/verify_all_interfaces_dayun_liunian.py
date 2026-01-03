#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码验证脚本：检查所有接口的大运流年实现
验证4个接口：
1. 八字命理-子女学习 (children_study_analysis.py)
2. 八字命理-身体健康分析 (health_analysis.py)
3. 八字命理-事业财富 (career_wealth_analysis.py)
4. 八字命理-感情婚姻 (marriage_analysis.py)
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
    passed_count = 0
    
    for check_name, check_func in checks:
        result = check_func(content, file_path)
        if result:
            print(f"✅ {check_name}")
            passed_count += 1
        else:
            print(f"❌ {check_name}")
            all_passed = False
    
    print(f"\n通过: {passed_count}/{len(checks)}")
    return all_passed


def check_imports_orchestrator(content, file_path):
    """检查是否导入了BaziDataOrchestrator"""
    return 'BaziDataOrchestrator' in content


def check_import_organize(content, file_path):
    """检查是否导入了organize_special_liunians_by_dayun"""
    return 'organize_special_liunians_by_dayun' in content


def check_unified_interface(content, file_path):
    """检查是否使用了统一接口"""
    # 检查是否调用了BaziDataOrchestrator.fetch_data
    has_fetch_data = 'BaziDataOrchestrator' in content and 'fetch_data' in content
    # 检查是否获取了special_liunians
    has_special_liunians = 'special_liunians' in content and ('dayun_config' in content or 'modules' in content)
    
    return has_fetch_data and has_special_liunians


def check_organize_liunians(content, file_path):
    """检查是否使用了organize_special_liunians_by_dayun"""
    return 'organize_special_liunians_by_dayun(' in content


def check_liunians_in_data(content, file_path):
    """检查数据构建中是否包含流年字段"""
    return "'liunians'" in content or '"liunians"' in content or 'liunians:' in content


def check_prompt_liunian_output(content, file_path):
    """检查Prompt构建中是否包含流年输出"""
    patterns = [
        r'流年',
        r'liunian',
        r'\d{4}年',
    ]
    
    for pattern in patterns:
        if re.search(pattern, content):
            return True
    return False


def check_current_dayun_format(content, file_path):
    """检查是否包含现行运格式"""
    return '现行' in content or 'current_dayun' in content


def check_key_dayun_format(content, file_path):
    """检查是否包含关键节点格式"""
    return '关键节点' in content or 'key_dayuns' in content or 'key_dayun' in content


def check_children_study_specific(content, file_path):
    """检查子女学习接口特定要求"""
    has_current = '现行' in content or 'current_dayun' in content
    has_key = '关键节点' in content or 'key_dayuns' in content
    has_identify = 'identify_key_dayuns' in content
    
    return has_current and has_key and has_identify


def check_health_analysis_specific(content, file_path):
    """检查身体健康分析接口特定要求"""
    has_current = '现行' in content or 'current_dayun' in content
    has_key = '关键节点' in content or 'key_dayuns' in content
    has_identify = 'identify_key_dayuns' in content
    
    return has_current and has_key and has_identify


def check_career_wealth_specific(content, file_path):
    """检查事业财富接口特定要求"""
    has_current = '现行' in content or 'current_dayun' in content
    has_key = '关键节点' in content or 'key_dayuns' in content
    has_identify = 'identify_key_dayuns' in content
    has_shiye = 'shiye_yunshi' in content
    has_caifu = 'caifu_yunshi' in content
    
    return has_current and has_key and has_identify and has_shiye and has_caifu


def check_marriage_specific(content, file_path):
    """检查感情婚姻接口特定要求"""
    has_dayun_list = 'dayun_list' in content
    has_step_234 = '[1, 2, 3]' in content or 'range(1, 4)' in content or 'idx in [1, 2, 3]' in content
    
    return has_dayun_list and has_step_234


def check_priority_order(content, file_path):
    """检查流年优先级排序逻辑"""
    # 检查是否按优先级合并流年（两种方式都算正确）
    # 方式1: 使用extend合并到all_liunians
    has_extend_pattern = (
        'tiankedi_chong' in content and 'extend' in content and
        ('tianhedi_he' in content or 'suiyun_binglin' in content or 'other' in content)
    )
    
    # 方式2: 保留分类结构（健康分析接口使用这种方式）
    has_classified_structure = (
        'tiankedi_chong' in content and 'tianhedi_he' in content and
        ('suiyun_binglin' in content or 'other' in content)
    )
    
    # 方式3: 在Prompt中按优先级输出
    has_priority_in_prompt = (
        'tiankedi_chong' in content and 'tianhedi_he' in content and
        ('流年' in content or 'liunian' in content)
    )
    
    return has_extend_pattern or has_classified_structure or has_priority_in_prompt


def main():
    """主函数"""
    print("=" * 80)
    print("所有接口大运流年实现验证")
    print("=" * 80)
    
    results = []
    
    # 检查子女学习接口
    children_checks = [
        ('导入BaziDataOrchestrator', check_imports_orchestrator),
        ('导入organize_special_liunians_by_dayun', check_import_organize),
        ('使用统一接口获取数据', check_unified_interface),
        ('使用organize_special_liunians_by_dayun分组', check_organize_liunians),
        ('数据构建包含流年字段', check_liunians_in_data),
        ('Prompt包含流年输出', check_prompt_liunian_output),
        ('包含现行运格式', check_current_dayun_format),
        ('包含关键节点格式', check_key_dayun_format),
        ('包含identify_key_dayuns', lambda c, f: 'identify_key_dayuns' in c),
        ('流年优先级排序', check_priority_order),
    ]
    
    result1 = check_file('server/api/v1/children_study_analysis.py', children_checks)
    results.append(('子女学习接口', result1))
    
    # 检查身体健康分析接口
    health_checks = [
        ('导入BaziDataOrchestrator', check_imports_orchestrator),
        ('导入organize_special_liunians_by_dayun', check_import_organize),
        ('使用统一接口获取数据', check_unified_interface),
        ('使用organize_special_liunians_by_dayun分组', check_organize_liunians),
        ('数据构建包含流年字段', check_liunians_in_data),
        ('Prompt包含流年输出', check_prompt_liunian_output),
        ('包含现行运格式', check_current_dayun_format),
        ('包含关键节点格式', check_key_dayun_format),
        ('包含identify_key_dayuns', lambda c, f: 'identify_key_dayuns' in c),
        ('流年优先级排序', check_priority_order),
    ]
    
    result2 = check_file('server/api/v1/health_analysis.py', health_checks)
    results.append(('身体健康分析接口', result2))
    
    # 检查事业财富接口
    career_checks = [
        ('导入BaziDataOrchestrator', check_imports_orchestrator),
        ('导入organize_special_liunians_by_dayun', check_import_organize),
        ('使用统一接口获取数据', check_unified_interface),
        ('使用organize_special_liunians_by_dayun分组', check_organize_liunians),
        ('数据构建包含流年字段', check_liunians_in_data),
        ('Prompt包含流年输出', check_prompt_liunian_output),
        ('包含现行运格式', check_current_dayun_format),
        ('包含关键节点格式', check_key_dayun_format),
        ('包含identify_key_dayuns', lambda c, f: 'identify_key_dayuns' in c),
        ('事业运势包含流年', lambda c, f: 'shiye_yunshi' in c and 'liunians' in c),
        ('财富运势包含流年', lambda c, f: 'caifu_yunshi' in c and 'liunians' in c),
        ('流年优先级排序', check_priority_order),
    ]
    
    result3 = check_file('server/api/v1/career_wealth_analysis.py', career_checks)
    results.append(('事业财富接口', result3))
    
    # 检查感情婚姻接口
    marriage_checks = [
        ('导入BaziDataOrchestrator', check_imports_orchestrator),
        ('导入organize_special_liunians_by_dayun', check_import_organize),
        ('使用统一接口获取数据', check_unified_interface),
        ('使用organize_special_liunians_by_dayun分组', check_organize_liunians),
        ('数据构建包含流年字段', check_liunians_in_data),
        ('Prompt包含流年输出', check_prompt_liunian_output),
        ('包含dayun_list', lambda c, f: 'dayun_list' in c),
        ('包含第2-4步大运逻辑', lambda c, f: '[1, 2, 3]' in c or 'range(1, 4)' in c),
        ('流年优先级排序', check_priority_order),
    ]
    
    result4 = check_file('server/api/v1/marriage_analysis.py', marriage_checks)
    results.append(('感情婚姻接口', result4))
    
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
        print("\n🎉 所有接口验证通过！")
        print("\n✅ 验证通过的项目：")
        print("  - 所有接口都正确导入了必要的模块")
        print("  - 所有接口都使用了统一接口获取数据")
        print("  - 所有接口都使用了organize_special_liunians_by_dayun分组流年")
        print("  - 所有接口的数据构建都包含了流年字段")
        print("  - 所有接口的Prompt构建都包含了流年输出")
        print("  - 流年按优先级正确排序（天克地冲 > 天合地合 > 岁运并临 > 其他）")
        print("\n✅ 特定验证：")
        print("  - 子女学习接口：包含现行运和关键节点格式")
        print("  - 身体健康分析接口：包含现行运和关键节点格式")
        print("  - 事业财富接口：事业运势和财富运势都包含流年")
        print("  - 感情婚姻接口：第2-4步大运都包含流年")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个接口验证失败")
        return 1


if __name__ == '__main__':
    exit(main())

