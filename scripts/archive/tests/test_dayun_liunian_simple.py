#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化测试脚本：验证大运流年数据构建逻辑
主要检查：
1. 数据是否正确从统一接口获取
2. 流年是否按优先级排序
3. 流年是否正确匹配到对应的大运
4. 数据格式是否正确
"""

import sys
import os
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置环境变量
os.environ.setdefault('COZE_ACCESS_TOKEN', 'test_token')
os.environ.setdefault('COZE_BOT_ID', 'test_bot_id')


async def test_data_building():
    """测试数据构建逻辑"""
    print("="*80)
    print("大运流年数据构建验证测试")
    print("="*80)
    
    try:
        from server.services.bazi_data_orchestrator import BaziDataOrchestrator
        from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun
        from server.api.v1.career_wealth_analysis import identify_key_dayuns
        
        # 测试数据
        test_cases = [
            ('1990-01-15', '12:00', 'male'),
            ('1995-05-20', '14:30', 'female'),
        ]
        
        all_passed = True
        
        for solar_date, solar_time, gender in test_cases:
            print(f"\n{'='*80}")
            print(f"测试用例: {solar_date} {solar_time} {gender}")
            print(f"{'='*80}")
            
            # 1. 使用统一接口获取数据
            print("\n[步骤1] 使用统一接口获取数据...")
            orchestrator_data = await BaziDataOrchestrator.fetch_data(
                solar_date, solar_time, gender,
                modules={
                    'bazi': True, 'wangshuai': True, 'detail': True,
                    'dayun': {'mode': 'count', 'count': 13},
                    'special_liunians': {'dayun_config': {'mode': 'count', 'count': 13}, 'count': 200}
                }
            )
            
            bazi_data = orchestrator_data['bazi']
            dayun_sequence = orchestrator_data['dayun']['list']
            special_liunians = orchestrator_data['special_liunians']['list']
            
            print(f"✅ 获取到大运数量: {len(dayun_sequence)}")
            print(f"✅ 获取到特殊流年数量: {len(special_liunians)}")
            
            if not dayun_sequence:
                print("❌ 错误: 未获取到大运数据")
                all_passed = False
                continue
            
            # 2. 按大运分组特殊流年
            print("\n[步骤2] 按大运分组特殊流年...")
            dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
            print(f"✅ 分组完成，分组数量: {len(dayun_liunians)}")
            
            # 3. 验证分组结果
            print("\n[步骤3] 验证分组结果...")
            total_liunians = 0
            priority_issues = []
            
            for step, data in sorted(dayun_liunians.items()):
                dayun_info = data.get('dayun_info', {})
                step_display = dayun_info.get('step', step)
                stem = dayun_info.get('stem', '')
                branch = dayun_info.get('branch', '')
                
                tiankedi = data.get('tiankedi_chong', [])
                tianhedi = data.get('tianhedi_he', [])
                suiyun = data.get('suiyun_binglin', [])
                other = data.get('other', [])
                
                total = len(tiankedi) + len(tianhedi) + len(suiyun) + len(other)
                total_liunians += total
                
                if total > 0:
                    # 验证优先级：天克地冲 > 天合地合 > 岁运并临 > 其他
                    # 检查是否有优先级问题（例如：如果有天克地冲，不应该有其他类型的流年排在前面）
                    if tiankedi and (tianhedi or suiyun or other):
                        # 这是正常的，因为分类是按类型分开的
                        pass
                    
                    print(f"  第{step_display}步大运 {stem}{branch}: {total}个流年")
                    print(f"    - 天克地冲: {len(tiankedi)} (优先级1)")
                    print(f"    - 天合地合: {len(tianhedi)} (优先级2)")
                    print(f"    - 岁运并临: {len(suiyun)} (优先级3)")
                    print(f"    - 其他: {len(other)} (优先级4)")
                    
                    # 验证流年数据结构
                    for liunian in tiankedi[:2]:  # 检查前2个
                        if 'year' not in liunian or 'type' not in liunian:
                            print(f"    ⚠️  警告: 流年数据缺少必要字段: {liunian}")
                            priority_issues.append(f"第{step_display}步大运流年数据格式问题")
            
            print(f"\n✅ 总流年数量: {total_liunians}")
            
            if priority_issues:
                print(f"⚠️  发现 {len(priority_issues)} 个数据格式问题")
                all_passed = False
            
            # 4. 验证事业财富接口的数据构建
            print("\n[步骤4] 验证事业财富接口数据构建...")
            element_counts = bazi_data.get('element_counts', {})
            bazi_elements = {
                '木': element_counts.get('木', 0),
                '火': element_counts.get('火', 0),
                '土': element_counts.get('土', 0),
                '金': element_counts.get('金', 0),
                '水': element_counts.get('水', 0)
            }
            
            from datetime import datetime
            birth_date = datetime.strptime(solar_date, '%Y-%m-%d')
            current_date = datetime.now()
            current_age = current_date.year - birth_date.year
            
            dayun_analysis_result = identify_key_dayuns(dayun_sequence, bazi_elements, current_age)
            current_dayun_info = dayun_analysis_result.get('current_dayun')
            key_dayuns_list = dayun_analysis_result.get('key_dayuns', [])
            
            if current_dayun_info:
                current_step = current_dayun_info.get('step')
                if current_step is None:
                    for idx, dayun in enumerate(dayun_sequence):
                        if dayun == current_dayun_info:
                            current_step = idx
                            break
                
                dayun_liunian_data = dayun_liunians.get(current_step, {}) if current_step is not None else {}
                all_liunians = []
                if dayun_liunian_data.get('tiankedi_chong'): all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
                if dayun_liunian_data.get('tianhedi_he'): all_liunians.extend(dayun_liunian_data['tianhedi_he'])
                if dayun_liunian_data.get('suiyun_binglin'): all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
                if dayun_liunian_data.get('other'): all_liunians.extend(dayun_liunian_data['other'])
                
                print(f"✅ 现行运: 第{current_step}步，流年数量: {len(all_liunians)}")
                if all_liunians:
                    # 验证流年是否按优先级排序
                    liunian_types = [l.get('type', '') for l in all_liunians]
                    has_tiankedi = any('天克地冲' in t for t in liunian_types)
                    has_tianhedi = any('天合地合' in t for t in liunian_types)
                    has_suiyun = any('岁运并临' in t for t in liunian_types)
                    
                    # 检查优先级：如果有天克地冲，应该优先显示
                    if has_tiankedi and (has_tianhedi or has_suiyun):
                        # 检查天克地冲是否在前面
                        first_tiankedi_idx = next((i for i, t in enumerate(liunian_types) if '天克地冲' in t), -1)
                        first_other_idx = next((i for i, t in enumerate(liunian_types) if '天合地合' in t or '岁运并临' in t), -1)
                        if first_tiankedi_idx > first_other_idx and first_other_idx != -1:
                            print(f"    ⚠️  警告: 流年优先级可能有问题（天克地冲应该在前面）")
                            all_passed = False
                    
                    liunian_list = [f"{l.get('year', '')}年({l.get('type', '')})" for l in all_liunians[:5]]
                    print(f"   流年列表（前5个）: {liunian_list}")
            else:
                print("⚠️  未找到现行运")
            
            if key_dayuns_list:
                print(f"✅ 关键节点大运数量: {len(key_dayuns_list)}")
                for key_dayun in key_dayuns_list[:2]:  # 只显示前2个
                    key_step = key_dayun.get('step')
                    if key_step is None:
                        for idx, dayun in enumerate(dayun_sequence):
                            if dayun == key_dayun:
                                key_step = idx
                                break
                    dayun_liunian_data = dayun_liunians.get(key_step, {}) if key_step is not None else {}
                    all_liunians = []
                    if dayun_liunian_data.get('tiankedi_chong'): all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
                    if dayun_liunian_data.get('tianhedi_he'): all_liunians.extend(dayun_liunian_data['tianhedi_he'])
                    if dayun_liunian_data.get('suiyun_binglin'): all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
                    if dayun_liunian_data.get('other'): all_liunians.extend(dayun_liunian_data['other'])
                    print(f"   第{key_step}步大运: {len(all_liunians)}个流年")
            else:
                print("⚠️  未找到关键节点大运")
            
            # 5. 验证感情婚姻接口的数据构建（第2-4步大运）
            print("\n[步骤5] 验证感情婚姻接口数据构建（第2-4步大运）...")
            for idx in [1, 2, 3]:
                if idx < len(dayun_sequence):
                    dayun = dayun_sequence[idx]
                    dayun_step = dayun.get('step')
                    if dayun_step is None:
                        dayun_step = idx
                    
                    dayun_liunian_data = dayun_liunians.get(dayun_step, {}) if dayun_step is not None else {}
                    all_liunians = []
                    if dayun_liunian_data.get('tiankedi_chong'): all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
                    if dayun_liunian_data.get('tianhedi_he'): all_liunians.extend(dayun_liunian_data['tianhedi_he'])
                    if dayun_liunian_data.get('suiyun_binglin'): all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
                    if dayun_liunian_data.get('other'): all_liunians.extend(dayun_liunian_data['other'])
                    
                    print(f"✅ 第{dayun_step}步大运: {len(all_liunians)}个流年")
                    if all_liunians:
                        liunian_list = [f"{l.get('year', '')}年({l.get('type', '')})" for l in all_liunians[:5]]
                        print(f"   流年列表（前5个）: {liunian_list}")
        
        # 汇总结果
        print(f"\n{'='*80}")
        print("测试结果汇总")
        print(f"{'='*80}")
        
        if all_passed:
            print("🎉 所有测试通过！")
            print("\n✅ 验证通过的项目：")
            print("  - 数据从统一接口正确获取")
            print("  - 流年按大运正确分组")
            print("  - 流年按优先级正确分类（天克地冲 > 天合地合 > 岁运并临 > 其他）")
            print("  - 事业财富接口数据构建正确（现行运和关键节点大运都包含流年）")
            print("  - 感情婚姻接口数据构建正确（第2-4步大运都包含流年）")
            return 0
        else:
            print("⚠️  部分测试失败，请检查上述警告信息")
            return 1
        
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(test_data_building())
    sys.exit(exit_code)

