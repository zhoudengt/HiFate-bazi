#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试特殊流年数据获取
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_special_liunians():
    """测试特殊流年数据获取"""
    print("="*60)
    print("测试特殊流年数据获取")
    print("="*60)
    
    url = f"{BASE_URL}/api/v1/children-study/debug"
    payload = {
        "solar_date": "1990-05-15",
        "solar_time": "14:30",
        "gender": "male"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get('success'):
            print(f"❌ 请求失败：{result.get('error')}")
            return
        
        input_data = result.get('input_data', {})
        
        # 检查特殊流年原始数据
        special_liunians_raw = input_data.get('_special_liunians_raw', [])
        print(f"\n特殊流年原始数据数量: {len(special_liunians_raw)}")
        
        if special_liunians_raw:
            print(f"\n前5个特殊流年:")
            for liunian in special_liunians_raw[:5]:
                print(f"  - {liunian.get('year')}年, dayun_step={liunian.get('dayun_step')}, relations={liunian.get('relations', [])}")
        
        # 检查大运序列
        shengyu = input_data.get('shengyu_shiji', {})
        all_dayuns = shengyu.get('all_dayuns', [])
        print(f"\n大运序列数量: {len(all_dayuns)}")
        print(f"前5个大运的step:")
        for dayun in all_dayuns[:5]:
            print(f"  - step={dayun.get('step')}, stem={dayun.get('stem')}, branch={dayun.get('branch')}, age={dayun.get('age_display')}")
        
        # 检查现行运
        current_dayun = shengyu.get('current_dayun')
        if current_dayun:
            print(f"\n现行运:")
            print(f"  - step={current_dayun.get('step')}")
            print(f"  - 流年数量: {len(current_dayun.get('liunians', []))}")
        
        # 检查关键节点
        key_dayuns = shengyu.get('key_dayuns', [])
        print(f"\n关键节点大运数量: {len(key_dayuns)}")
        for key_dayun in key_dayuns:
            print(f"  - step={key_dayun.get('step')}, 流年数量: {len(key_dayun.get('liunians', []))}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_special_liunians()

