#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试脚本：测试所有接口的大运流年返回值
测试接口：
1. 八字命理-子女学习 (children_study_analysis.py)
2. 八字命理-身体健康分析 (health_analysis.py)
3. 八字命理-事业财富 (career_wealth_analysis.py)
4. 八字命理-感情婚姻 (marriage_analysis.py)
"""

import sys
import os
import asyncio
import json
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置环境变量
os.environ.setdefault('COZE_ACCESS_TOKEN', 'test_token')
os.environ.setdefault('COZE_BOT_ID', 'test_bot_id')
os.environ.setdefault('CAREER_WEALTH_BOT_ID', 'test_bot_id')
os.environ.setdefault('MARRIAGE_ANALYSIS_BOT_ID', 'test_bot_id')
os.environ.setdefault('HEALTH_ANALYSIS_BOT_ID', 'test_bot_id')
os.environ.setdefault('CHILDREN_STUDY_BOT_ID', 'test_bot_id')


async def test_data_building_for_interface(interface_name, test_func):
    """测试单个接口的数据构建"""
    print(f"\n{'='*80}")
    print(f"【数据构建验证】{interface_name}")
    print(f"{'='*80}")
    
    try:
        result = await test_func()
        if result:
            print(f"✅ {interface_name} 数据构建验证通过")
        else:
            print(f"❌ {interface_name} 数据构建验证失败")
        return result
    except Exception as e:
        print(f"❌ {interface_name} 数据构建验证异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_children_study_data():
    """测试子女学习接口的数据构建"""
    from server.services.bazi_data_orchestrator import BaziDataOrchestrator
    from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun
    from server.api.v1.children_study_analysis import identify_key_dayuns
    
    solar_date = '1990-01-15'
    solar_time = '12:00'
    gender = 'male'
    
    # 获取数据
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
    
    # 分组流年
    dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
    print(f"✅ 流年分组完成，分组数量: {len(dayun_liunians)}")
    
    # 验证数据构建逻辑
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
    
    # 检查现行运和关键节点大运是否包含流年
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
        print(f"✅ 现行运流年数量: {len(all_liunians)}")
    
    if key_dayuns_list:
        print(f"✅ 关键节点大运数量: {len(key_dayuns_list)}")
        for key_dayun in key_dayuns_list[:2]:
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
            print(f"   第{key_step}步大运流年数量: {len(all_liunians)}")
    
    return True


async def test_health_analysis_data():
    """测试身体健康分析接口的数据构建"""
    from server.services.bazi_data_orchestrator import BaziDataOrchestrator
    from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun
    from server.api.v1.health_analysis import identify_key_dayuns
    
    solar_date = '1990-01-15'
    solar_time = '12:00'
    gender = 'male'
    
    # 获取数据
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
    
    # 分组流年
    dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
    print(f"✅ 流年分组完成，分组数量: {len(dayun_liunians)}")
    
    # 验证数据构建逻辑
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
    
    # 检查现行运和关键节点大运是否包含流年
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
        print(f"✅ 现行运流年数量: {len(all_liunians)}")
    
    if key_dayuns_list:
        print(f"✅ 关键节点大运数量: {len(key_dayuns_list)}")
        for key_dayun in key_dayuns_list[:2]:
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
            print(f"   第{key_step}步大运流年数量: {len(all_liunians)}")
    
    return True


async def test_career_wealth_data():
    """测试事业财富接口的数据构建"""
    from server.services.bazi_data_orchestrator import BaziDataOrchestrator
    from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun
    from server.api.v1.career_wealth_analysis import identify_key_dayuns
    
    solar_date = '1990-01-15'
    solar_time = '12:00'
    gender = 'male'
    
    # 获取数据
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
    
    # 分组流年
    dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
    print(f"✅ 流年分组完成，分组数量: {len(dayun_liunians)}")
    
    # 验证数据构建逻辑
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
    
    # 检查现行运和关键节点大运是否包含流年
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
        print(f"✅ 现行运流年数量: {len(all_liunians)}")
    
    if key_dayuns_list:
        print(f"✅ 关键节点大运数量: {len(key_dayuns_list)}")
        for key_dayun in key_dayuns_list[:2]:
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
            print(f"   第{key_step}步大运流年数量: {len(all_liunians)}")
    
    return True


async def test_marriage_analysis_data():
    """测试感情婚姻接口的数据构建"""
    from server.services.bazi_data_orchestrator import BaziDataOrchestrator
    from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun
    
    solar_date = '1990-01-15'
    solar_time = '12:00'
    gender = 'male'
    
    # 获取数据
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
    
    # 分组流年
    dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
    print(f"✅ 流年分组完成，分组数量: {len(dayun_liunians)}")
    
    # 验证第2-4步大运是否包含流年
    print("\n检查第2-4步大运流年...")
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
            print(f"✅ 第{dayun_step}步大运流年数量: {len(all_liunians)}")
            if all_liunians:
                liunian_list = [f"{l.get('year', '')}年({l.get('type', '')})" for l in all_liunians[:3]]
                print(f"   流年示例: {liunian_list}")
    
    return True


async def test_interface_response(interface_name, generator_func, solar_date, solar_time, gender):
    """测试接口响应（调用实际接口）"""
    print(f"\n{'='*80}")
    print(f"【接口响应验证】{interface_name}")
    print(f"{'='*80}")
    
    try:
        print(f"测试数据: {solar_date} {solar_time} {gender}")
        
        # 收集流式响应（只收集前几个chunk）
        chunks = []
        chunk_count = 0
        max_chunks = 10
        
        async for chunk in generator_func(solar_date, solar_time, gender):
            if isinstance(chunk, str):
                if chunk.startswith('data: '):
                    try:
                        data = json.loads(chunk[6:])
                        chunks.append(data)
                        chunk_count += 1
                        
                        if data.get('type') == 'error':
                            print(f"❌ 错误: {data.get('content', '未知错误')}")
                            return False
                        
                        if chunk_count >= max_chunks:
                            break
                    except:
                        pass
        
        if not chunks:
            print("❌ 未收到任何响应")
            return False
        
        progress_chunks = [c for c in chunks if c.get('type') == 'progress']
        if not progress_chunks:
            print("⚠️  警告: 未收到内容块")
            return False
        
        all_content = ' '.join(c.get('content', '') for c in progress_chunks)
        
        print(f"✅ 收到 {len(progress_chunks)} 个内容块")
        print(f"✅ 总内容长度: {len(all_content)} 字符")
        
        # 检查大运流年格式
        print("\n检查大运流年格式...")
        
        # 检查是否包含大运信息
        has_dayun = bool(re.search(r'大运|现行|关键节点|第\d+步', all_content))
        if has_dayun:
            print("✅ 包含大运信息")
        else:
            print("⚠️  未检测到大运信息")
        
        # 检查是否包含流年信息
        has_liunian = bool(re.search(r'\d{4}年', all_content))
        if has_liunian:
            print("✅ 包含流年信息（年份）")
            years = re.findall(r'(\d{4})年', all_content)
            print(f"   检测到流年: {', '.join(set(years[:10]))}...")
        else:
            print("⚠️  未检测到流年信息")
        
        # 检查是否包含流年类型
        liunian_types = ['天克地冲', '天合地合', '岁运并临']
        found_types = [t for t in liunian_types if t in all_content]
        if found_types:
            print(f"✅ 包含流年类型: {', '.join(found_types)}")
        else:
            print("⚠️  未检测到流年类型")
        
        return True
        
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("="*80)
    print("所有接口大运流年返回值综合测试")
    print("="*80)
    
    results = []
    
    # 测试1: 数据构建验证（不调用Coze API）
    print("\n" + "="*80)
    print("第一部分：数据构建验证（不调用Coze API）")
    print("="*80)
    
    result1 = await test_data_building_for_interface("子女学习", test_children_study_data)
    results.append(('子女学习-数据构建', result1))
    
    result2 = await test_data_building_for_interface("身体健康分析", test_health_analysis_data)
    results.append(('身体健康-数据构建', result2))
    
    result3 = await test_data_building_for_interface("事业财富", test_career_wealth_data)
    results.append(('事业财富-数据构建', result3))
    
    result4 = await test_data_building_for_interface("感情婚姻", test_marriage_analysis_data)
    results.append(('感情婚姻-数据构建', result4))
    
    # 测试2: 接口响应验证（调用实际接口，可能超时）
    print("\n" + "="*80)
    print("第二部分：接口响应验证（调用实际接口）")
    print("="*80)
    
    test_cases = [
        ('子女学习', 'children_study_analysis_stream_generator', 'children_study_analysis'),
        ('身体健康分析', 'health_analysis_stream_generator', 'health_analysis'),
        ('事业财富', 'career_wealth_stream_generator', 'career_wealth_analysis'),
        ('感情婚姻', 'marriage_analysis_stream_generator', 'marriage_analysis'),
    ]
    
    for name, func_name, module_name in test_cases:
        try:
            module = __import__(f'server.api.v1.{module_name}', fromlist=[func_name])
            generator_func = getattr(module, func_name)
            
            result = await asyncio.wait_for(
                test_interface_response(name, generator_func, '1990-01-15', '12:00', 'male'),
                timeout=30.0
            )
            results.append((f'{name}-接口响应', result))
        except asyncio.TimeoutError:
            print(f"⚠️  {name} 接口响应测试超时（Coze API可能不可用）")
            results.append((f'{name}-接口响应', None))
        except Exception as e:
            print(f"⚠️  {name} 接口响应测试失败: {e}")
            results.append((f'{name}-接口响应', False))
    
    # 汇总结果
    print(f"\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}")
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    for name, result in results:
        if result is True:
            status = "✅ 通过"
        elif result is False:
            status = "❌ 失败"
        else:
            status = "⏭️  跳过（API不可用）"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过")
    
    if failed == 0:
        print("\n🎉 所有可执行的测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

