#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日元-六十甲子API
验证API接口和数据查询功能
"""

import sys
import os
import json
import requests

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_service():
    """测试服务层"""
    print('=' * 60)
    print('测试日元-六十甲子服务层')
    print('=' * 60)
    print()
    
    try:
        from server.services.rizhu_liujiazi_service import RizhuLiujiaziService
        
        # 测试查询日柱解析
        print('1. 测试查询日柱解析:')
        test_rizhu = '乙丑'
        result = RizhuLiujiaziService.get_rizhu_analysis(test_rizhu)
        if result:
            print(f'   ✅ 查询成功: 日柱={result["rizhu"]}, ID={result["id"]}')
            print(f'   解析内容长度: {len(result["analysis"])} 字符')
            print(f'   解析内容预览: {result["analysis"][:100]}...')
        else:
            print(f'   ⚠️  未找到日柱 {test_rizhu} 的解析（可能数据库中没有数据）')
        print()
        
        # 测试获取所有日柱列表
        print('2. 测试获取所有日柱列表:')
        all_rizhu = RizhuLiujiaziService.get_all_rizhu_list()
        print(f'   ✅ 获取成功: 共 {len(all_rizhu)} 条记录')
        if all_rizhu:
            print(f'   前5条: {[r["rizhu"] for r in all_rizhu[:5]]}')
        print()
        
        print('=' * 60)
        print('✅ 服务层测试完成')
        print('=' * 60)
        
    except Exception as e:
        import traceback
        print(f'❌ 测试失败: {e}')
        print(traceback.format_exc())


def test_api(base_url='http://localhost:8001'):
    """测试API接口"""
    print('=' * 60)
    print('测试日元-六十甲子API接口')
    print('=' * 60)
    print()
    
    # 测试数据
    test_cases = [
        {
            'name': '正常查询（乙丑）',
            'solar_date': '1990-01-07',
            'solar_time': '09:00',
            'gender': 'male'
        },
        {
            'name': '正常查询（女性）',
            'solar_date': '1995-05-20',
            'solar_time': '14:30',
            'gender': 'female'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f'{i}. {test_case["name"]}:')
        try:
            response = requests.post(
                f'{base_url}/api/v1/bazi/rizhu-liujiazi',
                json={
                    'solar_date': test_case['solar_date'],
                    'solar_time': test_case['solar_time'],
                    'gender': test_case['gender']
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    result = data.get('data', {})
                    print(f'   ✅ 查询成功')
                    print(f'   ID: {result.get("id")}')
                    print(f'   日柱: {result.get("rizhu")}')
                    print(f'   解析内容长度: {len(result.get("analysis", ""))} 字符')
                    print(f'   解析内容预览: {result.get("analysis", "")[:100]}...')
                else:
                    print(f'   ❌ 查询失败: {data.get("error")}')
            else:
                print(f'   ❌ HTTP错误: {response.status_code}')
                print(f'   响应: {response.text[:200]}')
        except Exception as e:
            print(f'   ❌ 请求失败: {e}')
        print()
    
    print('=' * 60)
    print('✅ API接口测试完成')
    print('=' * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='测试日元-六十甲子功能')
    parser.add_argument('--service-only', action='store_true', help='只测试服务层')
    parser.add_argument('--api-only', action='store_true', help='只测试API接口')
    parser.add_argument('--base-url', default='http://localhost:8001', help='API基础URL')
    args = parser.parse_args()
    
    if not args.api_only:
        test_service()
        print()
    
    if not args.service_only:
        test_api(args.base_url)


if __name__ == '__main__':
    main()

