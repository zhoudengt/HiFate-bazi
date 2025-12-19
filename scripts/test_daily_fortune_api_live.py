#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时测试每日运势日历API
直接调用API，验证返回的字段名
"""

import sys
import os
import json
import requests
from datetime import date

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_live_api(base_url='http://localhost:8001'):
    """实时测试API"""
    print('=' * 60)
    print('实时测试每日运势日历API')
    print('=' * 60)
    print(f'API地址: {base_url}')
    print()
    
    try:
        # 调用API
        url = f'{base_url}/api/v1/daily-fortune-calendar/query'
        payload = {
            'date': date.today().strftime('%Y-%m-%d')
        }
        
        print(f'请求URL: {url}')
        print(f'请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}')
        print()
        
        response = requests.post(url, json=payload, timeout=10)
        print(f'响应状态码: {response.status_code}')
        print()
        
        if response.status_code == 200:
            data = response.json()
            print('响应数据字段检查:')
            print('-' * 60)
            
            # 检查字段
            checks = []
            
            # 检查 jianchu
            jianchu = data.get('jianchu')
            if jianchu:
                if isinstance(jianchu, dict):
                    if 'energy' in jianchu:
                        checks.append(('jianchu.energy', True, jianchu.get('energy')))
                    else:
                        checks.append(('jianchu.energy', False, '字段不存在'))
                    if 'score' in jianchu:
                        checks.append(('jianchu.score', False, '❌ 仍有旧字段 score'))
                    else:
                        checks.append(('jianchu.score', True, '✅ 已移除'))
                else:
                    checks.append(('jianchu', False, f'类型错误: {type(jianchu)}'))
            else:
                checks.append(('jianchu', False, '字段不存在或为None'))
            
            # 检查 wuxing_wear
            wuxing_wear = data.get('wuxing_wear')
            if wuxing_wear is not None:
                checks.append(('wuxing_wear', True, wuxing_wear))
            else:
                checks.append(('wuxing_wear', False, '字段不存在或为None'))
            
            # 检查 guiren_fangwei
            guiren_fangwei = data.get('guiren_fangwei')
            if guiren_fangwei is not None:
                checks.append(('guiren_fangwei', True, guiren_fangwei))
            else:
                checks.append(('guiren_fangwei', False, '字段不存在或为None'))
            
            # 检查旧字段是否还存在
            if 'lucky_colors' in data:
                checks.append(('lucky_colors', False, '❌ 仍有旧字段'))
            else:
                checks.append(('lucky_colors', True, '✅ 已移除'))
            
            if 'guiren_directions' in data:
                checks.append(('guiren_directions', False, '❌ 仍有旧字段'))
            else:
                checks.append(('guiren_directions', True, '✅ 已移除'))
            
            # 显示检查结果
            all_passed = True
            for name, passed, value in checks:
                status = '✅' if passed else '❌'
                print(f'{status} {name}: {value}')
                if not passed:
                    all_passed = False
            print()
            
            # 显示完整响应（用于调试）
            print('完整响应数据（前500字符）:')
            print('-' * 60)
            response_str = json.dumps(data, ensure_ascii=False, indent=2)
            print(response_str[:500])
            if len(response_str) > 500:
                print('... (已截断)')
            print()
            
            # 总结
            print('=' * 60)
            if all_passed:
                print('✅ 所有字段检查通过！API返回的字段名正确。')
                print()
                print('如果前端仍显示"暂无"，可能是：')
                print('1. 数据本身为空（数据库中没有对应数据）')
                print('2. 前端代码需要刷新缓存')
                print('3. 浏览器需要强制刷新（Ctrl+F5 或 Cmd+Shift+R）')
            else:
                print('❌ 字段检查未完全通过！')
                print()
                print('可能的原因：')
                print('1. 后端服务没有重启，还在使用旧代码')
                print('2. 代码修改没有生效')
                print()
                print('解决方案：')
                print('1. 重启后端服务')
                print('2. 清理 Redis 缓存')
            print('=' * 60)
            
        else:
            print(f'❌ API调用失败: {response.status_code}')
            print(f'响应内容: {response.text[:500]}')
            
    except requests.exceptions.ConnectionError:
        print('❌ 无法连接到API服务器')
        print('请确保后端服务正在运行')
    except Exception as e:
        import traceback
        print(f'❌ 测试失败: {e}')
        print(traceback.format_exc())

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='测试每日运势日历API')
    parser.add_argument('--url', default='http://localhost:8001', help='API基础URL')
    args = parser.parse_args()
    
    test_live_api(args.url)

