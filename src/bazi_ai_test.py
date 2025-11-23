#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字AI分析测试脚本
用于测试 /api/v1/bazi/ai-analyze 接口
"""

import sys
import os
import json
import requests
from datetime import datetime

# 添加模块路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_bazi_ai_analyze(solar_date, solar_time, gender, user_question=None, 
                         access_token=None, bot_id=None, api_base=None,
                         include_rizhu_analysis=True, base_url="http://127.0.0.1:8001"):
    """
    测试八字AI分析接口
    
    Args:
        solar_date: 阳历日期，格式：YYYY-MM-DD
        solar_time: 出生时间，格式：HH:MM
        gender: 性别，'male' 或 'female'
        user_question: 用户的问题或分析需求，可选
        access_token: Coze Access Token，可选
        bot_id: Coze Bot ID，可选
        api_base: Coze API 基础URL，可选
        include_rizhu_analysis: 是否包含日柱性别分析结果，默认 True
        base_url: API 基础URL，默认 http://127.0.0.1:8001
    """
    url = f"{base_url}/api/v1/bazi/ai-analyze"
    
    # 构建请求数据
    data = {
        "solar_date": solar_date,
        "solar_time": solar_time,
        "gender": gender,
        "include_rizhu_analysis": include_rizhu_analysis
    }
    
    if user_question:
        data["user_question"] = user_question
    
    if access_token:
        data["access_token"] = access_token
    
    if bot_id:
        data["bot_id"] = bot_id
    
    if api_base:
        data["api_base"] = api_base
    
    # 打印请求信息
    print("=" * 80)
    print("八字AI分析接口测试")
    print("=" * 80)
    print(f"请求URL: {url}")
    print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n请求参数:")
    print(f"  阳历日期: {solar_date}")
    print(f"  出生时间: {solar_time}")
    print(f"  性别: {'男' if gender == 'male' else '女'}")
    if user_question:
        print(f"  用户问题: {user_question}")
    print(f"  包含日柱分析: {include_rizhu_analysis}")
    print("\n" + "-" * 80)
    
    try:
        # 发送请求
        print("正在发送请求...")
        response = requests.post(url, json=data, timeout=120)
        
        # 打印响应状态
        print(f"\n响应状态码: {response.status_code}")
        print("-" * 80)
        
        if response.status_code == 200:
            result = response.json()
            
            # 打印结果
            print("\n【响应结果】")
            print("=" * 80)
            
            if result.get('success'):
                print("✓ 请求成功\n")
                
                # 八字数据
                bazi_data = result.get('bazi_data', {})
                if bazi_data:
                    print("【八字数据】")
                    print("-" * 80)
                    bazi = bazi_data.get('bazi', {})
                    basic_info = bazi.get('basic_info', {})
                    print(f"阳历: {basic_info.get('solar_date')} {basic_info.get('solar_time')}")
                    print(f"性别: {'男' if basic_info.get('gender') == 'male' else '女'}")
                    
                    lunar_date = basic_info.get('lunar_date', {})
                    if isinstance(lunar_date, dict):
                        print(f"农历: {lunar_date.get('year')}年{lunar_date.get('month_name', '')}{lunar_date.get('day_name', '')}")
                    
                    bazi_pillars = bazi.get('bazi_pillars', {})
                    print("\n四柱八字:")
                    for pillar_type in ['year', 'month', 'day', 'hour']:
                        pillar = bazi_pillars.get(pillar_type, {})
                        pillar_name = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_type, pillar_type)
                        print(f"  {pillar_name}: {pillar.get('stem', '')}{pillar.get('branch', '')}")
                    
                    print(f"\n日柱: {bazi_data.get('rizhu', '')}")
                    print()
                
                # 日柱性别分析
                rizhu_analysis = result.get('rizhu_analysis')
                if rizhu_analysis:
                    print("【日柱性别分析（原始）】")
                    print("-" * 80)
                    print(rizhu_analysis)
                    print()
                
                # AI 分析结果
                ai_analysis = result.get('ai_analysis', {})
                if ai_analysis:
                    print("【AI 分析结果】")
                    print("-" * 80)
                    if ai_analysis.get('success'):
                        analysis_text = ai_analysis.get('analysis', '')
                        if analysis_text:
                            print(analysis_text)
                        else:
                            print("AI 分析结果为空")
                    else:
                        print(f"✗ AI 分析失败: {ai_analysis.get('error', '未知错误')}")
                    print()
                
                # 润色后的规则内容
                polished_rules = result.get('polished_rules')
                polished_rules_info = result.get('polished_rules_info')
                
                if polished_rules_info:
                    # 显示完整的原始内容和润色后的内容
                    original_content = polished_rules_info.get('original')
                    polished_content = polished_rules_info.get('polished')
                    
                    # 检查是否是错误信息（通常错误信息包含 "code" 或 "error" 等字段）
                    is_error = False
                    if polished_content:
                        polished_str = str(polished_content).strip()
                        # 检查是否是 JSON 格式的错误信息
                        if polished_str.startswith('{') and ('"code"' in polished_str or '"error"' in polished_str or '"msg"' in polished_str):
                            is_error = True
                    
                    if original_content:
                        print("【优化前（原始内容）】")
                        print("=" * 80)
                        print(original_content)
                        print()
                    
                    if polished_content and not is_error:
                        print("【优化后（处理后的内容）】")
                        print("=" * 80)
                        print(polished_content)
                        print()
                    elif is_error:
                        print("【优化后（处理后的内容）】")
                        print("=" * 80)
                        print("✗ 润色失败，返回了错误信息:")
                        print(polished_content)
                        print()
                    
                    # 只有在不是错误的情况下才显示修改清单
                    if not is_error:
                        # 显示修改清单（优化前/优化后对比）
                        changes = polished_rules_info.get('changes', [])
                        changes_count = polished_rules_info.get('changes_count', 0)
                        
                        if changes_count > 0:
                            print("【优化内容清单】")
                            print("=" * 80)
                            print(f"共发现 {changes_count} 处优化\n")
                            
                            for i, change in enumerate(changes, 1):
                                change_type = change.get('type', 'modified')
                                original_text = change.get('original', '').strip()
                                polished_text = change.get('polished', '').strip()
                                
                                type_name = {
                                    'modified': '修改',
                                    'added': '新增',
                                    'deleted': '删除'
                                }.get(change_type, change_type)
                                
                                print(f"优化项 {i} ({type_name}):")
                                print("-" * 80)
                                
                                if original_text:
                                    print("优化前:")
                                    # 如果是多行，保持格式
                                    for line in original_text.split('\n'):
                                        if line.strip():  # 只显示非空行
                                            print(f"  {line}")
                                else:
                                    print("优化前: (无)")
                                
                                print()
                                
                                if change_type == 'deleted':
                                    # 对于删除类型，明确说明
                                    print("优化后: [此内容已被删除]")
                                elif polished_text:
                                    print("优化后:")
                                    # 如果是多行，保持格式
                                    for line in polished_text.split('\n'):
                                        if line.strip():  # 只显示非空行
                                            print(f"  {line}")
                                else:
                                    print("优化后: (无)")
                                
                                print()
                                print()
                        else:
                            print("【优化内容清单】")
                            print("=" * 80)
                            print("未检测到修改（内容完全相同）")
                            print()
                elif polished_rules:
                    # 检查是否是错误信息
                    polished_str = str(polished_rules).strip()
                    is_error = polished_str.startswith('{') and ('"code"' in polished_str or '"error"' in polished_str or '"msg"' in polished_str)
                    
                    if is_error:
                        print("【优化后的规则内容】")
                        print("=" * 80)
                        print("✗ 润色失败，返回了错误信息:")
                        print(polished_rules)
                        print()
                    else:
                        # 如果没有对比信息，只显示润色后的内容
                        print("【优化后的规则内容】")
                        print("=" * 80)
                        print(polished_rules)
                        print()
            else:
                print("✗ 请求失败")
                error = result.get('error', '未知错误')
                print(f"错误信息: {error}")
        else:
            print(f"✗ HTTP 错误: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
            except:
                print(f"错误内容: {response.text}")
        
        print("=" * 80)
        return response.json() if response.status_code == 200 else None
        
    except requests.exceptions.Timeout:
        print("✗ 请求超时（超过120秒）")
        return None
    except requests.exceptions.ConnectionError:
        print(f"✗ 连接失败: 无法连接到 {base_url}")
        print("请确保服务已启动")
        return None
    except Exception as e:
        print(f"✗ 请求异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='八字AI分析接口测试工具')
    parser.add_argument('--date', '-d', type=str, default='1990-05-15', help='阳历日期 (YYYY-MM-DD)')
    parser.add_argument('--time', '-t', type=str, default='14:30', help='出生时间 (HH:MM)')
    parser.add_argument('--gender', '-g', type=str, choices=['male', 'female'], default='male', help='性别 (male/female)')
    parser.add_argument('--question', '-q', type=str, default=None, help='用户问题')
    parser.add_argument('--url', '-u', type=str, default='http://127.0.0.1:8001', help='API 基础URL')
    parser.add_argument('--all', '-a', action='store_true', help='运行所有测试用例')
    
    args = parser.parse_args()
    
    if args.all:
        # 运行所有测试用例
        print("\n" + "=" * 80)
        print("测试用例 1: 基本测试")
        print("=" * 80)
        test_bazi_ai_analyze(
            solar_date="1990-05-15",
            solar_time="14:30",
            gender="male",
            user_question="请分析我的财运和事业",
            base_url=args.url
        )
        
        print("\n\n")
        
        # 测试用例2: 不包含用户问题
        print("=" * 80)
        print("测试用例 2: 不包含用户问题")
        print("=" * 80)
        test_bazi_ai_analyze(
            solar_date="1983-12-22",
            solar_time="22:30",
            gender="male",
            base_url=args.url
        )
        
        print("\n\n")
        
        # 测试用例3: 女性测试
        print("=" * 80)
        print("测试用例 3: 女性测试")
        print("=" * 80)
        test_bazi_ai_analyze(
            solar_date="1995-08-20",
            solar_time="10:15",
            gender="female",
            user_question="请分析我的感情和健康",
            base_url=args.url
        )
    else:
        # 运行单个测试用例
        test_bazi_ai_analyze(
            solar_date=args.date,
            solar_time=args.time,
            gender=args.gender,
            user_question=args.question,
            base_url=args.url
        )

