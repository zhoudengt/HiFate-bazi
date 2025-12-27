#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试子女学习分析接口的大运流年格式
验证是否按照新格式返回（现行运和关键节点）
"""

import requests
import json
import sys

# 测试配置
BASE_URL = "http://localhost:8001"
TEST_CASES = [
    {
        "name": "测试案例1：1990-05-15 14:30 男",
        "solar_date": "1990-05-15",
        "solar_time": "14:30",
        "gender": "male"
    },
    {
        "name": "测试案例2：1995-08-20 09:00 女",
        "solar_date": "1995-08-20",
        "solar_time": "09:00",
        "gender": "female"
    }
]

def test_children_study_stream(test_case):
    """测试流式接口"""
    print(f"\n{'='*60}")
    print(f"测试：{test_case['name']}")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/api/v1/children-study/stream"
    payload = {
        "solar_date": test_case["solar_date"],
        "solar_time": test_case["solar_time"],
        "gender": test_case["gender"]
    }
    
    try:
        response = requests.post(url, json=payload, stream=True, timeout=60)
        response.raise_for_status()
        
        print(f"✅ 请求成功，状态码：{response.status_code}")
        
        # 解析 SSE 流
        full_content = ""
        has_progress = False
        has_complete = False
        has_error = False
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # 去掉 'data: ' 前缀
                    try:
                        data = json.loads(data_str)
                        data_type = data.get('type', '')
                        
                        if data_type == 'progress':
                            has_progress = True
                            content = data.get('content', '')
                            full_content += content
                            
                        elif data_type == 'complete':
                            has_complete = True
                            content = data.get('content', '')
                            full_content += content
                            
                        elif data_type == 'error':
                            has_error = True
                            error_content = data.get('content', '')
                            print(f"❌ 错误：{error_content}")
                            return False
                            
                    except json.JSONDecodeError as e:
                        print(f"⚠️  JSON 解析错误：{e}")
                        print(f"   原始数据：{line_str[:100]}")
        
        if has_error:
            print("❌ 测试失败：收到错误消息")
            return False
        
        if not has_progress and not has_complete:
            print("❌ 测试失败：未收到任何内容")
            return False
        
        print(f"✅ 收到流式响应（总长度：{len(full_content)} 字符）")
        
        # 检查大运流年格式
        print(f"\n{'─'*60}")
        print("检查大运流年格式：")
        print(f"{'─'*60}")
        
        # 检查是否包含"现行运"格式
        has_current_dayun = False
        if "**现行" in full_content and "运（" in full_content and "岁）：**" in full_content:
            has_current_dayun = True
            print("✅ 找到现行运格式：**现行X运（XX-XX岁）：**")
            
            # 提取现行运部分
            import re
            current_dayun_pattern = r'\*\*现行(\d+)运（([^）]+)）：\*\*'
            matches = re.findall(current_dayun_pattern, full_content)
            if matches:
                for step, age_range in matches:
                    print(f"   - 第{step}步大运，年龄范围：{age_range}")
        else:
            print("❌ 未找到现行运格式：**现行X运（XX-XX岁）：**")
        
        # 检查是否包含"关键节点"格式
        has_key_dayun = False
        if "**关键节点：" in full_content and "运（" in full_content and "岁）：**" in full_content:
            has_key_dayun = True
            print("✅ 找到关键节点格式：**关键节点：X运（XX-XX岁）：**")
            
            # 提取关键节点部分
            key_dayun_pattern = r'\*\*关键节点：(\d+)运（([^）]+)）：\*\*'
            matches = re.findall(key_dayun_pattern, full_content)
            if matches:
                for step, age_range in matches:
                    print(f"   - 第{step}步大运，年龄范围：{age_range}")
        else:
            print("⚠️  未找到关键节点格式（可能没有关键节点大运）")
        
        # 检查是否包含流年信息
        has_liunian = False
        if "年（" in full_content and ("天克地冲" in full_content or "天合地合" in full_content or 
                                       "岁运并临" in full_content or "其他" in full_content):
            has_liunian = True
            print("✅ 找到流年信息（包含特殊流年类型）")
            
            # 提取流年信息
            import re
            liunian_pattern = r'(\d{4})年（([^）]+)）：'
            matches = re.findall(liunian_pattern, full_content)
            if matches:
                print(f"   找到 {len(matches)} 个流年：")
                for year, liunian_type in matches[:10]:  # 最多显示10个
                    print(f"   - {year}年（{liunian_type}）")
        else:
            print("⚠️  未找到流年信息（可能没有特殊流年）")
        
        # 检查是否包含"分析该年的学习风险"等提示
        has_analysis_hint = False
        if "分析该年的学习风险" in full_content or "分析该年的健康风险" in full_content:
            has_analysis_hint = True
            print("✅ 找到分析提示：分析该年的学习/健康风险")
        else:
            print("⚠️  未找到分析提示（可能已被Coze Bot替换为实际分析）")
        
        # 检查是否包含"利好"和"挑战"
        has_benefit = False
        has_challenge = False
        if "利好：" in full_content or "积极影响" in full_content:
            has_benefit = True
            print("✅ 找到利好分析")
        if "挑战：" in full_content or "学习风险" in full_content:
            has_challenge = True
            print("✅ 找到挑战分析")
        
        # 显示部分内容（用于验证）
        print(f"\n{'─'*60}")
        print("内容预览（前1000字符）：")
        print(f"{'─'*60}")
        print(full_content[:1000])
        if len(full_content) > 1000:
            print(f"... (还有 {len(full_content) - 1000} 字符)")
        
        # 总结
        print(f"\n{'─'*60}")
        print("测试总结：")
        print(f"{'─'*60}")
        print(f"✅ 流式响应：成功")
        print(f"{'✅' if has_current_dayun else '❌'} 现行运格式：{'找到' if has_current_dayun else '未找到'}")
        print(f"{'✅' if has_key_dayun else '⚠️ '} 关键节点格式：{'找到' if has_key_dayun else '未找到（可能没有）'}")
        print(f"{'✅' if has_liunian else '⚠️ '} 流年信息：{'找到' if has_liunian else '未找到（可能没有）'}")
        print(f"{'✅' if has_benefit or has_challenge else '⚠️ '} 利好/挑战分析：{'找到' if (has_benefit or has_challenge) else '未找到'}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败：{e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_debug_endpoint(test_case):
    """测试调试接口，查看数据结构"""
    print(f"\n{'='*60}")
    print(f"调试接口测试：{test_case['name']}")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/api/v1/children-study/debug"
    payload = {
        "solar_date": test_case["solar_date"],
        "solar_time": test_case["solar_time"],
        "gender": test_case["gender"]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get('success'):
            print(f"❌ 调试接口返回错误：{result.get('error')}")
            return False
        
        print("✅ 调试接口请求成功")
        
        # 检查数据结构
        input_data = result.get('input_data', {})
        shengyu_shiji = input_data.get('shengyu_shiji', {})
        
        print(f"\n{'─'*60}")
        print("数据结构检查：")
        print(f"{'─'*60}")
        
        # 检查现行运
        current_dayun = shengyu_shiji.get('current_dayun')
        if current_dayun:
            print("✅ 找到现行运数据：")
            print(f"   - 步骤：{current_dayun.get('step')}")
            print(f"   - 大运：{current_dayun.get('stem')}{current_dayun.get('branch')}")
            print(f"   - 年龄：{current_dayun.get('age_display')}")
            liunians = current_dayun.get('liunians', [])
            print(f"   - 流年数量：{len(liunians)}")
            if liunians:
                print(f"   - 流年列表：")
                for liunian in liunians[:5]:  # 最多显示5个
                    year = liunian.get('year', '')
                    liunian_type = liunian.get('type', '')
                    print(f"     * {year}年（{liunian_type}）")
        else:
            print("❌ 未找到现行运数据")
        
        # 检查关键节点大运
        key_dayuns = shengyu_shiji.get('key_dayuns', [])
        if key_dayuns:
            print(f"\n✅ 找到 {len(key_dayuns)} 个关键节点大运：")
            for idx, key_dayun in enumerate(key_dayuns, 1):
                print(f"   {idx}. 第{key_dayun.get('step')}步大运：{key_dayun.get('stem')}{key_dayun.get('branch')}（{key_dayun.get('age_display')}）")
                print(f"      - 关系类型：{key_dayun.get('relation_type')}")
                liunians = key_dayun.get('liunians', [])
                print(f"      - 流年数量：{len(liunians)}")
                if liunians:
                    for liunian in liunians[:3]:  # 最多显示3个
                        year = liunian.get('year', '')
                        liunian_type = liunian.get('type', '')
                        print(f"        * {year}年（{liunian_type}）")
        else:
            print("\n⚠️  未找到关键节点大运（可能没有与原局有特殊生克关系的大运）")
        
        # 检查所有大运
        all_dayuns = shengyu_shiji.get('all_dayuns', [])
        if all_dayuns:
            print(f"\n✅ 找到 {len(all_dayuns)} 个大运（所有大运）")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败：{e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("="*60)
    print("子女学习分析接口 - 大运流年格式测试")
    print("="*60)
    
    # 检查服务是否可用
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code != 200:
            print(f"❌ 服务健康检查失败，状态码：{health_response.status_code}")
            sys.exit(1)
        print("✅ 服务健康检查通过")
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务：{e}")
        print(f"   请确保服务运行在 {BASE_URL}")
        sys.exit(1)
    
    # 运行测试
    success_count = 0
    total_count = 0
    
    for test_case in TEST_CASES:
        total_count += 1
        
        # 测试调试接口
        if test_debug_endpoint(test_case):
            success_count += 0.5
        
        # 测试流式接口
        if test_children_study_stream(test_case):
            success_count += 0.5
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    print(f"总测试数：{total_count}")
    print(f"成功数：{success_count}")
    print(f"成功率：{success_count / total_count * 100:.1f}%")
    
    if success_count == total_count:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试未通过，请检查上述输出")
        sys.exit(1)


if __name__ == "__main__":
    main()

