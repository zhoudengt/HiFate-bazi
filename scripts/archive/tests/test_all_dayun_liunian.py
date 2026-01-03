#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试脚本：验证所有接口的大运流年格式（数据构建测试）
"""

import sys
import os
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置环境变量（避免需要实际配置）
os.environ.setdefault('COZE_ACCESS_TOKEN', 'test_token')
os.environ.setdefault('COZE_BOT_ID', 'test_bot_id')

from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun


async def test_data_structure(solar_date, solar_time, gender):
    """测试数据构建结构"""
    print(f"\n{'='*80}")
    print(f"测试数据构建: {solar_date} {solar_time} {gender}")
    print(f"{'='*80}")
    
    try:
        # 使用统一接口获取所有数据
        orchestrator_data = await BaziDataOrchestrator.fetch_data(
            solar_date, solar_time, gender,
            modules={
                'bazi': True, 'wangshuai': True, 'detail': True,
                'dayun': {'mode': 'count', 'count': 13},
                'special_liunians': {'dayun_config': {'mode': 'count', 'count': 13}, 'count': 200}
            }
        )
        
        dayun_sequence = orchestrator_data['dayun']['list']
        special_liunians = orchestrator_data['special_liunians']['list']
        
        print(f"✅ 获取到大运数量: {len(dayun_sequence)}")
        print(f"✅ 获取到特殊流年数量: {len(special_liunians)}")
        
        # 按大运分组特殊流年
        dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
        
        print(f"\n大运流年分组结果:")
        print(f"  分组数量: {len(dayun_liunians)}")
        
        # 检查每个大运的流年
        for step, data in sorted(dayun_liunians.items()):
            dayun_info = data.get('dayun_info', {})
            step_display = dayun_info.get('step', step)
            stem = dayun_info.get('stem', '')
            branch = dayun_info.get('branch', '')
            age_display = dayun_info.get('age_display', '')
            
            tiankedi = len(data.get('tiankedi_chong', []))
            tianhedi = len(data.get('tianhedi_he', []))
            suiyun = len(data.get('suiyun_binglin', []))
            other = len(data.get('other', []))
            total = tiankedi + tianhedi + suiyun + other
            
            if total > 0:
                print(f"  第{step_display}步大运 {stem}{branch}（{age_display}）: {total}个流年")
                print(f"    - 天克地冲: {tiankedi}")
                print(f"    - 天合地合: {tianhedi}")
                print(f"    - 岁运并临: {suiyun}")
                print(f"    - 其他: {other}")
        
        # 检查第2-4步大运（感情婚姻接口使用）
        print(f"\n第2-4步大运流年检查（感情婚姻接口）:")
        for idx in [1, 2, 3]:
            if idx < len(dayun_sequence):
                dayun = dayun_sequence[idx]
                step = dayun.get('step', idx)
                dayun_liunian_data = dayun_liunians.get(step, {})
                all_liunians = []
                if dayun_liunian_data.get('tiankedi_chong'): all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
                if dayun_liunian_data.get('tianhedi_he'): all_liunians.extend(dayun_liunian_data['tianhedi_he'])
                if dayun_liunian_data.get('suiyun_binglin'): all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
                if dayun_liunian_data.get('other'): all_liunians.extend(dayun_liunian_data['other'])
                
                print(f"  第{step}步大运: {len(all_liunians)}个流年")
                if all_liunians:
                    for liunian in all_liunians[:3]:  # 只显示前3个
                        year = liunian.get('year', '')
                        liunian_type = liunian.get('type', '')
                        print(f"    - {year}年（{liunian_type}）")
        
        return True
        
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("="*80)
    print("大运流年格式综合测试（数据构建验证）")
    print("="*80)
    
    # 测试数据
    test_cases = [
        ('1990-01-15', '12:00', 'male'),
        ('1995-05-20', '14:30', 'female'),
    ]
    
    results = []
    for solar_date, solar_time, gender in test_cases:
        result = await test_data_structure(solar_date, solar_time, gender)
        results.append(result)
    
    # 汇总结果
    print(f"\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        return 1


if __name__ == '__main__':
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
