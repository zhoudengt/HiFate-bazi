#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地区码表读取示例
演示如何从 region_code_table.json 中读取三级数据
"""

import json
from typing import Dict, List, Optional

def load_region_table(file_path: str = "docs/region_code_table.json") -> Dict:
    """加载地区码表"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_region_info(data: Dict, region_code: str) -> Optional[Dict]:
    """获取地区信息（一级：国家/地区）"""
    return data['regions'].get(region_code)

def get_subdivision_info(data: Dict, region_code: str, subdivision_code: str) -> Optional[Dict]:
    """获取省/州/区信息（二级：省/州/区）"""
    region = get_region_info(data, region_code)
    if region:
        return region.get('subdivisions', {}).get(subdivision_code)
    return None

def get_city_info(data: Dict, region_code: str, subdivision_code: str, city_code: str) -> Optional[Dict]:
    """获取城市信息（三级：城市/街道/选区）"""
    subdivision = get_subdivision_info(data, region_code, subdivision_code)
    if subdivision:
        # 检查是否有 cities 字段
        cities = subdivision.get('cities', {})
        if cities:
            return cities.get(city_code)
        # 检查是否有 major_cities 字段（美国等）
        major_cities = subdivision.get('major_cities', {})
        if major_cities:
            return major_cities.get(city_code)
    return None

def get_area_info(data: Dict, region_code: str, subdivision_code: str, city_code: str, area_code: str) -> Optional[Dict]:
    """获取区域信息（四级：具体区域/社区/地点）"""
    city = get_city_info(data, region_code, subdivision_code, city_code)
    if city:
        areas = city.get('areas', {})
        return areas.get(area_code)
    return None

def list_all_areas(data: Dict, region_code: str, subdivision_code: str, city_code: str) -> List[Dict]:
    """列出某个城市的所有区域（四级）"""
    city = get_city_info(data, region_code, subdivision_code, city_code)
    if not city:
        return []
    
    areas = city.get('areas', {})
    return [
        {
            'code': code,
            'name_zh': info.get('name_zh'),
            'name_en': info.get('name_en'),
            'latitude': info.get('latitude'),
            'longitude': info.get('longitude'),
        }
        for code, info in areas.items()
    ]

def list_all_subdivisions(data: Dict, region_code: str) -> List[Dict]:
    """列出某个地区的所有省/州/区"""
    region = get_region_info(data, region_code)
    if region:
        subdivisions = region.get('subdivisions', {})
        return [
            {
                'code': code,
                'name_zh': info.get('name_zh'),
                'name_en': info.get('name_en'),
                'latitude': info.get('latitude'),
                'longitude': info.get('longitude'),
            }
            for code, info in subdivisions.items()
        ]
    return []

def list_all_cities(data: Dict, region_code: str, subdivision_code: str) -> List[Dict]:
    """列出某个省/州/区的所有城市"""
    subdivision = get_subdivision_info(data, region_code, subdivision_code)
    if not subdivision:
        return []
    
    cities = []
    # 检查 cities 字段
    if 'cities' in subdivision:
        for code, info in subdivision['cities'].items():
            cities.append({
                'code': code,
                'name_zh': info.get('name_zh'),
                'name_en': info.get('name_en'),
                'latitude': info.get('latitude'),
                'longitude': info.get('longitude'),
            })
    # 检查 major_cities 字段
    elif 'major_cities' in subdivision:
        for code, info in subdivision['major_cities'].items():
            cities.append({
                'code': code,
                'name_zh': info.get('name_zh'),
                'name_en': info.get('name_en'),
                'latitude': info.get('latitude'),
                'longitude': info.get('longitude'),
            })
    
    return cities

def search_by_name(data: Dict, name_zh: str = None, name_en: str = None) -> List[Dict]:
    """根据中文或英文名称搜索地区"""
    results = []
    for region_code, region in data['regions'].items():
        # 搜索一级（国家/地区）
        if name_zh and name_zh in region.get('name_zh', ''):
            results.append({
                'level': 1,
                'region_code': region_code,
                'name_zh': region.get('name_zh'),
                'name_en': region.get('name_en'),
            })
        if name_en and name_en.lower() in region.get('name_en', '').lower():
            results.append({
                'level': 1,
                'region_code': region_code,
                'name_zh': region.get('name_zh'),
                'name_en': region.get('name_en'),
            })
        
        # 搜索二级（省/州/区）
        for sub_code, sub_info in region.get('subdivisions', {}).items():
            if name_zh and name_zh in sub_info.get('name_zh', ''):
                results.append({
                    'level': 2,
                    'region_code': region_code,
                    'subdivision_code': sub_code,
                    'name_zh': sub_info.get('name_zh'),
                    'name_en': sub_info.get('name_en'),
                })
            if name_en and name_en.lower() in sub_info.get('name_en', '').lower():
                results.append({
                    'level': 2,
                    'region_code': region_code,
                    'subdivision_code': sub_code,
                    'name_zh': sub_info.get('name_zh'),
                    'name_en': sub_info.get('name_en'),
                })
            
            # 搜索三级（城市）
            cities = sub_info.get('cities', {}) or sub_info.get('major_cities', {})
            for city_code, city_info in cities.items():
                if name_zh and name_zh in city_info.get('name_zh', ''):
                    results.append({
                        'level': 3,
                        'region_code': region_code,
                        'subdivision_code': sub_code,
                        'city_code': city_code,
                        'name_zh': city_info.get('name_zh'),
                        'name_en': city_info.get('name_en'),
                    })
                if name_en and name_en.lower() in city_info.get('name_en', '').lower():
                    results.append({
                        'level': 3,
                        'region_code': region_code,
                        'subdivision_code': sub_code,
                        'city_code': city_code,
                        'name_zh': city_info.get('name_zh'),
                        'name_en': city_info.get('name_en'),
                    })
    
    return results


# ========== 使用示例 ==========

if __name__ == '__main__':
    # 加载数据
    data = load_region_table()
    
    print("=" * 60)
    print("示例1: 读取香港中西区的信息")
    print("=" * 60)
    
    # 获取香港中西区信息
    hk_cw = get_subdivision_info(data, 'HK', 'HK-HCW')
    if hk_cw:
        print(f"区名（中文）: {hk_cw['name_zh']}")
        print(f"区名（英文）: {hk_cw['name_en']}")
        print(f"经纬度: ({hk_cw['latitude']}, {hk_cw['longitude']})")
        print()
        
        # 获取中西区下的所有街道/地区
        print("中西区下的街道/地区（三级数据）:")
        cities = list_all_cities(data, 'HK', 'HK-HCW')
        for i, city in enumerate(cities, 1):
            print(f"  {i}. {city['name_zh']} ({city['name_en']}) - {city['code']}")
            print(f"     经纬度: ({city['latitude']}, {city['longitude']})")
    
    print("\n" + "=" * 60)
    print("示例2: 读取香港所有区")
    print("=" * 60)
    hk_districts = list_all_subdivisions(data, 'HK')
    print(f"香港共有 {len(hk_districts)} 个区:")
    for district in hk_districts:
        cities_count = len(list_all_cities(data, 'HK', district['code']))
        print(f"  - {district['name_zh']} ({district['code']}) - 包含 {cities_count} 个街道/地区")
    
    print("\n" + "=" * 60)
    print("示例3: 读取特定城市信息（中环）")
    print("=" * 60)
    central = get_city_info(data, 'HK', 'HK-HCW', 'HK-HCW-CW')
    if central:
        print(f"城市名: {central['name_zh']} ({central['name_en']})")
        print(f"经纬度: ({central['latitude']}, {central['longitude']})")
        print(f"完整路径: 中国香港 > 中西区 > {central['name_zh']}")
    
    print("\n" + "=" * 60)
    print("示例4: 搜索功能（搜索包含'中'的地区）")
    print("=" * 60)
    results = search_by_name(data, name_zh='中')
    print(f"找到 {len(results)} 个结果:")
    for result in results[:10]:  # 只显示前10个
        if result['level'] == 1:
            print(f"  [一级] {result['name_zh']} ({result['region_code']})")
        elif result['level'] == 2:
            print(f"  [二级] {result['name_zh']} ({result['region_code']} > {result['subdivision_code']})")
        else:
            print(f"  [三级] {result['name_zh']} ({result['region_code']} > {result['subdivision_code']} > {result['city_code']})")
    
    print("\n" + "=" * 60)
    print("示例5: 读取美国加利福尼亚州的主要城市")
    print("=" * 60)
    ca_cities = list_all_cities(data, 'US', 'US-CA')
    print(f"加利福尼亚州共有 {len(ca_cities)} 个主要城市:")
    for city in ca_cities:
        print(f"  - {city['name_zh']} ({city['name_en']})")
    
    print("\n" + "=" * 60)
    print("示例6: 读取四级数据 - 中环下的所有区域")
    print("=" * 60)
    central_areas = list_all_areas(data, 'HK', 'HK-HCW', 'HK-HCW-CW')
    print(f"中环共有 {len(central_areas)} 个区域:")
    for area in central_areas:
        print(f"  - {area['name_zh']} ({area['name_en']}) - {area['code']}")
        print(f"     经纬度: ({area['latitude']}, {area['longitude']})")
    
    print("\n" + "=" * 60)
    print("示例7: 读取四级数据 - 洛杉矶的区域")
    print("=" * 60)
    la_areas = list_all_areas(data, 'US', 'US-CA', 'US-CA-LA')
    print(f"洛杉矶共有 {len(la_areas)} 个区域:")
    for area in la_areas:
        print(f"  - {area['name_zh']} ({area['name_en']})")
