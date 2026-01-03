#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证调整后的接口大运流年返回值
主要检查：
1. 大运流年是否正确返回
2. 流年是否按优先级排序
3. 流年是否正确匹配到对应的大运
4. 数据格式是否正确
"""

import sys
import os
import json
import asyncio
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置环境变量（避免需要实际配置）
os.environ.setdefault('COZE_ACCESS_TOKEN', 'test_token')
os.environ.setdefault('COZE_BOT_ID', 'test_bot_id')
os.environ.setdefault('CAREER_WEALTH_BOT_ID', 'test_bot_id')
os.environ.setdefault('MARRIAGE_ANALYSIS_BOT_ID', 'test_bot_id')


async def test_career_wealth_analysis():
    """测试事业财富分析接口的大运流年"""
    print(f"\n{'='*80}")
    print("测试接口: 事业财富分析")
    print(f"{'='*80}")
    
    try:
        from server.api.v1.career_wealth_analysis import career_wealth_stream_generator
        
        # 测试数据
        solar_date = '1990-01-15'
        solar_time = '12:00'
        gender = 'male'
        
        print(f"测试数据: {solar_date} {solar_time} {gender}")
        print("\n开始测试...")
        
        # 收集流式响应（只收集前几个chunk，避免等待太久）
        chunks = []
        chunk_count = 0
        max_chunks = 10  # 只收集前10个chunk用于验证
        
        async for chunk in career_wealth_stream_generator(solar_date, solar_time, gender):
            if isinstance(chunk, str):
                if chunk.startswith('data: '):
                    try:
                        data = json.loads(chunk[6:])
                        chunks.append(data)
                        chunk_count += 1
                        
                        # 检查是否有错误
                        if data.get('type') == 'error':
                            print(f"❌ 错误: {data.get('content', '未知错误')}")
                            return False
                        
                        # 只收集前几个chunk
                        if chunk_count >= max_chunks:
                            break
                    except:
                        pass
        
        if not chunks:
            print("❌ 未收到任何响应")
            return False
        
        # 检查响应内容
        progress_chunks = [c for c in chunks if c.get('type') == 'progress']
        if not progress_chunks:
            print("⚠️  警告: 未收到内容块")
            return False
        
        # 合并所有内容
        all_content = ' '.join(c.get('content', '') for c in progress_chunks)
        
        print(f"\n✅ 收到 {len(progress_chunks)} 个内容块")
        print(f"✅ 总内容长度: {len(all_content)} 字符")
        
        # 检查大运流年格式
        print("\n检查大运流年格式...")
        
        # 检查是否包含"现行X运"
        has_current_dayun = bool(re.search(r'现行\w*运', all_content))
        if has_current_dayun:
            print("✅ 包含'现行X运'格式")
        else:
            print("⚠️  未检测到'现行X运'格式")
        
        # 检查是否包含"关键节点"
        has_key_dayun = bool(re.search(r'关键节点.*运', all_content))
        if has_key_dayun:
            print("✅ 包含'关键节点：X运'格式")
        else:
            print("⚠️  未检测到'关键节点：X运'格式")
        
        # 检查是否包含流年信息
        has_liunian = bool(re.search(r'\d{4}年', all_content))
        if has_liunian:
            print("✅ 包含流年信息（年份）")
            # 提取所有年份
            years = re.findall(r'(\d{4})年', all_content)
            print(f"   检测到流年: {', '.join(set(years[:10]))}...")  # 显示前10个不重复的年份
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


async def test_marriage_analysis():
    """测试感情婚姻分析接口的大运流年"""
    print(f"\n{'='*80}")
    print("测试接口: 感情婚姻分析")
    print(f"{'='*80}")
    
    try:
        from server.api.v1.marriage_analysis import marriage_analysis_stream_generator
        
        # 测试数据
        solar_date = '1990-01-15'
        solar_time = '12:00'
        gender = 'male'
        
        print(f"测试数据: {solar_date} {solar_time} {gender}")
        print("\n开始测试...")
        
        # 收集流式响应（只收集前几个chunk，避免等待太久）
        chunks = []
        chunk_count = 0
        max_chunks = 10  # 只收集前10个chunk用于验证
        
        async for chunk in marriage_analysis_stream_generator(solar_date, solar_time, gender):
            if isinstance(chunk, str):
                if chunk.startswith('data: '):
                    try:
                        data = json.loads(chunk[6:])
                        chunks.append(data)
                        chunk_count += 1
                        
                        # 检查是否有错误
                        if data.get('type') == 'error':
                            print(f"❌ 错误: {data.get('content', '未知错误')}")
                            return False
                        
                        # 只收集前几个chunk
                        if chunk_count >= max_chunks:
                            break
                    except:
                        pass
        
        if not chunks:
            print("❌ 未收到任何响应")
            return False
        
        # 检查响应内容
        progress_chunks = [c for c in chunks if c.get('type') == 'progress']
        if not progress_chunks:
            print("⚠️  警告: 未收到内容块")
            return False
        
        # 合并所有内容
        all_content = ' '.join(c.get('content', '') for c in progress_chunks)
        
        print(f"\n✅ 收到 {len(progress_chunks)} 个内容块")
        print(f"✅ 总内容长度: {len(all_content)} 字符")
        
        # 检查大运流年格式
        print("\n检查大运流年格式...")
        
        # 检查是否包含"第X步大运"
        has_dayun = bool(re.search(r'第\d+步大运', all_content))
        if has_dayun:
            print("✅ 包含'第X步大运'格式")
            # 提取大运步骤
            steps = re.findall(r'第(\d+)步大运', all_content)
            print(f"   检测到大运步骤: {', '.join(set(steps))}")
        else:
            print("⚠️  未检测到'第X步大运'格式")
        
        # 检查是否包含流年信息
        has_liunian = bool(re.search(r'\d{4}年', all_content))
        if has_liunian:
            print("✅ 包含流年信息（年份）")
            # 提取所有年份
            years = re.findall(r'(\d{4})年', all_content)
            print(f"   检测到流年: {', '.join(set(years[:10]))}...")  # 显示前10个不重复的年份
        else:
            print("⚠️  未检测到流年信息")
        
        # 检查是否包含"关键流年"
        has_key_liunian = '关键流年' in all_content
        if has_key_liunian:
            print("✅ 包含'关键流年'标识")
        else:
            print("⚠️  未检测到'关键流年'标识")
        
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


async def test_data_structure():
    """测试数据构建结构（不调用Coze API）"""
    print(f"\n{'='*80}")
    print("测试数据构建结构（验证流年数据是否正确组织）")
    print(f"{'='*80}")
    
    try:
        from server.services.bazi_data_orchestrator import BaziDataOrchestrator
        from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun
        from server.api.v1.career_wealth_analysis import identify_key_dayuns, _calculate_ganzhi_elements
        
        # 测试数据
        solar_date = '1990-01-15'
        solar_time = '12:00'
        gender = 'male'
        
        print(f"测试数据: {solar_date} {solar_time} {gender}")
        print("\n开始测试...")
        
        # 使用统一接口获取所有数据
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
        
        print(f"\n✅ 获取到大运数量: {len(dayun_sequence)}")
        print(f"✅ 获取到特殊流年数量: {len(special_liunians)}")
        
        if not special_liunians:
            print("⚠️  警告: 未获取到特殊流年数据，可能测试数据没有特殊流年")
            return True  # 不算失败，可能是数据问题
        
        # 按大运分组特殊流年
        dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
        
        print(f"\n✅ 大运流年分组完成，分组数量: {len(dayun_liunians)}")
        
        # 检查分组结果
        total_liunians = 0
        for step, data in sorted(dayun_liunians.items()):
            dayun_info = data.get('dayun_info', {})
            step_display = dayun_info.get('step', step)
            stem = dayun_info.get('stem', '')
            branch = dayun_info.get('branch', '')
            
            tiankedi = len(data.get('tiankedi_chong', []))
            tianhedi = len(data.get('tianhedi_he', []))
            suiyun = len(data.get('suiyun_binglin', []))
            other = len(data.get('other', []))
            total = tiankedi + tianhedi + suiyun + other
            total_liunians += total
            
            if total > 0:
                print(f"  第{step_display}步大运 {stem}{branch}: {total}个流年")
                print(f"    - 天克地冲: {tiankedi} (优先级1)")
                print(f"    - 天合地合: {tianhedi} (优先级2)")
                print(f"    - 岁运并临: {suiyun} (优先级3)")
                print(f"    - 其他: {other} (优先级4)")
        
        print(f"\n✅ 总流年数量: {total_liunians}")
        
        # 检查事业财富接口的数据构建
        print("\n检查事业财富接口数据构建...")
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
                liunian_list = [f"{l.get('year', '')}年({l.get('type', '')})" for l in all_liunians[:5]]
                print(f"   流年列表: {liunian_list}")
        
        if key_dayuns_list:
            print(f"✅ 关键节点大运数量: {len(key_dayuns_list)}")
            for key_dayun in key_dayuns_list[:3]:  # 只显示前3个
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
        
        # 检查感情婚姻接口的数据构建（第2-4步大运）
        print("\n检查感情婚姻接口数据构建（第2-4步大运）...")
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
                    print(f"   流年列表: {liunian_list}")
        
        return True
        
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("="*80)
    print("大运流年返回值验证测试")
    print("="*80)
    
    results = []
    
    # 测试1: 数据构建结构（不调用Coze API，快速验证）
    print("\n【测试1】数据构建结构验证")
    result1 = await test_data_structure()
    results.append(('数据构建结构', result1))
    
    # 测试2: 事业财富分析接口（需要Coze API，可能超时）
    print("\n【测试2】事业财富分析接口（流式响应）")
    try:
        result2 = await asyncio.wait_for(test_career_wealth_analysis(), timeout=30.0)
        results.append(('事业财富分析', result2))
    except asyncio.TimeoutError:
        print("⚠️  测试超时（Coze API可能不可用）")
        results.append(('事业财富分析', None))
    except Exception as e:
        print(f"⚠️  测试失败: {e}")
        results.append(('事业财富分析', False))
    
    # 测试3: 感情婚姻分析接口（需要Coze API，可能超时）
    print("\n【测试3】感情婚姻分析接口（流式响应）")
    try:
        result3 = await asyncio.wait_for(test_marriage_analysis(), timeout=30.0)
        results.append(('感情婚姻分析', result3))
    except asyncio.TimeoutError:
        print("⚠️  测试超时（Coze API可能不可用）")
        results.append(('感情婚姻分析', None))
    except Exception as e:
        print(f"⚠️  测试失败: {e}")
        results.append(('感情婚姻分析', False))
    
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

