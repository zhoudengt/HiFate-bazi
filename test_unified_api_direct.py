#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试统一数据获取接口（不依赖FastAPI）
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from server.services.bazi_data_orchestrator import BaziDataOrchestrator


async def test_unified_api_direct():
    """直接测试编排服务"""
    print("=" * 80)
    print("测试统一数据获取接口（直接调用编排服务）")
    print("=" * 80)
    print(f"请求参数:")
    print(f"  日期: 1979-07-22")
    print(f"  时间: 07:15")
    print(f"  性别: male")
    print()
    
    # 构建模块配置
    modules = {
        "bazi": True,
        "wangshuai": True,
        "xishen_jishen": True,
        "dayun": {
            "mode": "count",
            "count": 8
        },
        "special_liunian": {
            "count": 8
        }
    }
    
    print(f"模块配置: {json.dumps(modules, ensure_ascii=False, indent=2)}")
    print()
    
    # 调用编排服务
    try:
        data = await BaziDataOrchestrator.fetch_data(
            solar_date="1979-07-22",
            solar_time="07:15",
            gender="male",
            modules=modules,
            use_cache=True,
            parallel=True,
            current_time=datetime.now()
        )
        
        # 1. 显示喜忌数据
        print("\n" + "=" * 80)
        print("1. 喜忌数据 (xishen_jishen)")
        print("=" * 80)
        if 'xishen_jishen' in data:
            xishen_jishen = data['xishen_jishen']
            if hasattr(xishen_jishen, 'data'):
                xj_data = xishen_jishen.data
                print(f"  喜神五行: {xj_data.get('xi_shen_elements', [])}")
                print(f"  忌神五行: {xj_data.get('ji_shen_elements', [])}")
                print(f"  十神命格: {xj_data.get('shishen_mingge', '')}")
                print(f"  旺衰: {xj_data.get('wangshuai', '')}")
            elif isinstance(xishen_jishen, dict):
                print(f"  喜神五行: {xishen_jishen.get('xi_shen_elements', [])}")
                print(f"  忌神五行: {xishen_jishen.get('ji_shen_elements', [])}")
            else:
                print(f"  数据格式: {type(xishen_jishen)}")
                print(f"  数据内容: {xishen_jishen}")
        else:
            print("  ❌ 未找到喜忌数据")
        
        # 2. 显示大运数据
        print("\n" + "=" * 80)
        print("2. 大运数据 (dayun) - 前8个")
        print("=" * 80)
        if 'dayun' in data:
            dayun_list = data['dayun']
            if isinstance(dayun_list, list):
                print(f"  大运数量: {len(dayun_list)}")
                for idx, dayun in enumerate(dayun_list[:8], 1):
                    ganzhi = dayun.get('ganzhi', f"{dayun.get('stem', '')}{dayun.get('branch', '')}")
                    step = dayun.get('step', '')
                    age_display = dayun.get('age_display', '')
                    year_start = dayun.get('year_start', '')
                    year_end = dayun.get('year_end', '')
                    print(f"  大运{idx}: {ganzhi} (第{step}步, {age_display}, {year_start}-{year_end}年)")
            else:
                print(f"  ❌ 大运数据格式错误: {type(dayun_list)}")
        else:
            print("  ❌ 未找到大运数据")
        
        # 3. 显示特殊流年数据
        print("\n" + "=" * 80)
        print("3. 特殊流年数据 (special_liunian)")
        print("=" * 80)
        if 'special_liunian' in data:
            special_liunian_list = data['special_liunian']
            if isinstance(special_liunian_list, list):
                print(f"  特殊流年数量: {len(special_liunian_list)}")
                if len(special_liunian_list) > 0:
                    for idx, liunian in enumerate(special_liunian_list[:20], 1):  # 最多显示20个
                        year = liunian.get('year', '')
                        ganzhi = liunian.get('ganzhi', f"{liunian.get('stem', '')}{liunian.get('branch', '')}")
                        relations = liunian.get('relations', [])
                        dayun_step = liunian.get('dayun_step', '')
                        dayun_ganzhi = liunian.get('dayun_ganzhi', '')
                        
                        relations_str = ', '.join([r.get('type', '') for r in relations]) if relations else '无'
                        print(f"  {idx}. {year}年 {ganzhi} (大运: 第{dayun_step}步 {dayun_ganzhi}) - 关系: {relations_str}")
                else:
                    print("  ⚠️ 特殊流年列表为空")
            else:
                print(f"  ❌ 特殊流年数据格式错误: {type(special_liunian_list)}")
        else:
            print("  ❌ 未找到特殊流年数据")
        
        # 4. 显示数据统计
        print("\n" + "=" * 80)
        print("4. 数据统计")
        print("=" * 80)
        print(f"  返回的数据模块: {list(data.keys())}")
        print(f"  数据模块数量: {len(data)}")
        
        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_unified_api_direct())

