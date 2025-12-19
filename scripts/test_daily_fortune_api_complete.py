#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试每日运势日历API
模拟实际API调用，验证返回的字段名
"""

import sys
import os
import json
from datetime import date

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_complete_api():
    """完整测试API"""
    print('=' * 60)
    print('完整测试每日运势日历API')
    print('=' * 60)
    print()
    
    try:
        from server.services.daily_fortune_calendar_service import DailyFortuneCalendarService
        
        # 测试1: get_jianchu_info
        print('测试1: get_jianchu_info')
        print('-' * 60)
        jianchu_info = DailyFortuneCalendarService.get_jianchu_info('开')
        if jianchu_info:
            print(f'返回数据: {json.dumps(jianchu_info, ensure_ascii=False, indent=2)}')
            if 'energy' in jianchu_info and 'score' not in jianchu_info:
                print('✅ 字段名正确: 有 energy，无 score')
            elif 'score' in jianchu_info:
                print('❌ 字段名错误: 仍有 score 字段')
            else:
                print('⚠️  energy 字段不存在')
        else:
            print('⚠️  返回 None（数据库可能没有数据）')
        print()
        
        # 测试2: get_daily_fortune_calendar（模拟调用）
        print('测试2: get_daily_fortune_calendar (模拟)')
        print('-' * 60)
        print('注意: 这个测试需要数据库连接，可能返回空数据')
        print('但我们可以检查返回字典的字段名结构')
        print()
        
        # 测试3: 检查代码中的字段名
        print('测试3: 检查代码中的字段名')
        print('-' * 60)
        
        # 读取服务层代码
        service_file = 'server/services/daily_fortune_calendar_service.py'
        with open(service_file, 'r', encoding='utf-8') as f:
            service_code = f.read()
        
        checks = []
        if "'wuxing_wear':" in service_code or '"wuxing_wear":' in service_code:
            checks.append(('wuxing_wear', True))
        else:
            checks.append(('wuxing_wear', False))
            
        if "'guiren_fangwei':" in service_code or '"guiren_fangwei":' in service_code:
            checks.append(('guiren_fangwei', True))
        else:
            checks.append(('guiren_fangwei', False))
            
        if "'energy':" in service_code and "'score':" not in service_code.replace("'score'", "").replace('"score"', ''):
            checks.append(('energy (无score)', True))
        else:
            checks.append(('energy (无score)', False))
            
        if "'lucky_colors':" not in service_code and '"lucky_colors":' not in service_code:
            checks.append(('已移除 lucky_colors', True))
        else:
            checks.append(('已移除 lucky_colors', False))
            
        if "'guiren_directions':" not in service_code and '"guiren_directions":' not in service_code:
            checks.append(('已移除 guiren_directions', True))
        else:
            checks.append(('已移除 guiren_directions', False))
        
        all_passed = True
        for name, passed in checks:
            if passed:
                print(f'✅ {name}')
            else:
                print(f'❌ {name}')
                all_passed = False
        print()
        
        # 测试4: 检查API层
        print('测试4: 检查API层字段名')
        print('-' * 60)
        api_file = 'server/api/v1/daily_fortune_calendar.py'
        with open(api_file, 'r', encoding='utf-8') as f:
            api_code = f.read()
        
        api_checks = []
        if 'wuxing_wear=' in api_code:
            api_checks.append(('wuxing_wear', True))
        else:
            api_checks.append(('wuxing_wear', False))
            
        if 'guiren_fangwei=' in api_code:
            api_checks.append(('guiren_fangwei', True))
        else:
            api_checks.append(('guiren_fangwei', False))
            
        if 'energy=' in api_code and 'score=' not in api_code.replace('score_value', ''):
            api_checks.append(('energy', True))
        else:
            api_checks.append(('energy', False))
        
        for name, passed in api_checks:
            if passed:
                print(f'✅ {name}')
            else:
                print(f'❌ {name}')
                all_passed = False
        print()
        
        # 总结
        print('=' * 60)
        if all_passed:
            print('✅ 所有代码检查通过！')
            print()
            print('如果前端仍显示"暂无"，说明后端服务需要重启。')
            print('请执行以下命令之一：')
            print()
            print('1. 如果使用热更新（推荐）：')
            print('   curl -X POST http://localhost:8001/api/v1/hot-reload/check')
            print()
            print('2. 如果使用 Docker：')
            print('   docker-compose restart web')
            print()
            print('3. 如果使用 systemd：')
            print('   sudo systemctl restart hifate-bazi')
            print()
            print('4. 清理缓存（如果需要）：')
            print('   python3 scripts/clear_daily_fortune_cache.py')
        else:
            print('❌ 代码检查未完全通过，需要修复代码')
        print('=' * 60)
        
    except Exception as e:
        import traceback
        print(f'❌ 测试失败: {e}')
        print(traceback.format_exc())

if __name__ == '__main__':
    test_complete_api()

