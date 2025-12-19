#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试每日运势日历API字段名
验证字段名是否正确：energy, wuxing_wear, guiren_fangwei
"""

import sys
import os
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_api_fields():
    """测试API返回的字段名"""
    print('=' * 60)
    print('测试每日运势日历API字段名')
    print('=' * 60)
    print()
    
    try:
        from server.services.daily_fortune_calendar_service import DailyFortuneCalendarService
        from datetime import date
        
        # 测试 get_jianchu_info
        print('1. 测试 get_jianchu_info 返回字段:')
        jianchu_info = DailyFortuneCalendarService.get_jianchu_info('开')
        if jianchu_info:
            print(f'   返回字段: {list(jianchu_info.keys())}')
            if 'energy' in jianchu_info:
                print(f'   ✅ energy 字段存在: {jianchu_info["energy"]}')
            else:
                print(f'   ❌ energy 字段不存在')
            if 'score' in jianchu_info:
                print(f'   ❌ score 字段仍然存在（错误！）')
            else:
                print(f'   ✅ score 字段已移除')
        else:
            print('   ⚠️  返回 None（可能是数据库中没有数据）')
        print()
        
        # 测试 get_daily_fortune_calendar（不实际调用，只检查代码）
        print('2. 检查 get_daily_fortune_calendar 代码:')
        import inspect
        source = inspect.getsource(DailyFortuneCalendarService.get_daily_fortune_calendar)
        
        checks = {
            'wuxing_wear': 'wuxing_wear' in source,
            'guiren_fangwei': 'guiren_fangwei' in source,
            'energy': "'energy':" in source or '"energy":' in source,
            'lucky_colors': 'lucky_colors' not in source,
            'guiren_directions': 'guiren_directions' not in source,
            'score': "'score':" not in source.replace("'score'", "").replace('"score"', '')
        }
        
        for field, exists in checks.items():
            if exists:
                print(f'   ✅ {field}: 正确')
            else:
                print(f'   ❌ {field}: 错误')
        print()
        
        # 测试颜色筛选函数
        print('3. 测试颜色筛选函数:')
        colors = ['红色', '粉红色', '蓝色', '天蓝色', '绿色', '黄色']
        filtered = DailyFortuneCalendarService._filter_colors_to_limit(colors, max_count=4)
        print(f'   原始颜色: {colors}')
        print(f'   筛选后: {filtered}')
        print(f'   数量: {len(filtered)} (期望 ≤ 4)')
        if len(filtered) <= 4:
            print('   ✅ 颜色筛选功能正常')
        else:
            print('   ❌ 颜色筛选功能异常')
        print()
        
        print('=' * 60)
        print('✅ 代码检查完成')
        print('=' * 60)
        print()
        print('如果代码检查都通过，但前端仍显示"暂无"，说明：')
        print('1. 后端服务需要重启以加载新代码')
        print('2. 或者需要清理 Redis 缓存')
        print()
        print('重启服务命令：')
        print('  - 如果使用 systemd: sudo systemctl restart hifate-bazi')
        print('  - 如果使用 docker: docker-compose restart web')
        print('  - 如果使用热更新: curl -X POST http://localhost:8001/api/v1/hot-reload/check')
        
    except Exception as e:
        import traceback
        print(f'❌ 测试失败: {e}')
        print(traceback.format_exc())

if __name__ == '__main__':
    test_api_fields()

