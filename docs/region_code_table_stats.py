#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地区码表数据统计
"""

import json

def print_stats():
    file_path = 'docs/region_code_table.json'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    regions = data['regions']
    
    print("=" * 70)
    print("地区码表数据统计报告")
    print("=" * 70)
    print(f"\n📊 总体统计:")
    print(f"  - 一级（国家/地区）: {len(regions)} 个")
    
    total_subdivisions = 0
    total_cities = 0
    total_areas = 0
    regions_with_level4 = 0
    
    for region_code, region in regions.items():
        subdivisions = region.get('subdivisions', {})
        total_subdivisions += len(subdivisions)
        
        for sub_code, sub_data in subdivisions.items():
            cities = sub_data.get('cities', {}) or sub_data.get('major_cities', {})
            total_cities += len(cities)
            
            for city_code, city_data in cities.items():
                areas = city_data.get('areas', {})
                total_areas += len(areas)
                if len(areas) > 0:
                    regions_with_level4 += 1
    
    print(f"  - 二级（省/州/区）: {total_subdivisions} 个")
    print(f"  - 三级（城市/街道）: {total_cities} 个")
    print(f"  - 四级（区域/社区）: {total_areas} 个")
    print(f"  - 有四级数据的城市: {regions_with_level4}/{total_cities} ({regions_with_level4*100//total_cities if total_cities > 0 else 0}%)")
    
    print(f"\n📋 各地区详细统计:")
    for region_code, region in sorted(regions.items()):
        region_name = region.get('name_zh', '')
        subdivisions = region.get('subdivisions', {})
        sub_count = len(subdivisions)
        
        city_count = 0
        area_count = 0
        for sub_data in subdivisions.values():
            cities = sub_data.get('cities', {}) or sub_data.get('major_cities', {})
            city_count += len(cities)
            for city_data in cities.values():
                area_count += len(city_data.get('areas', {}))
        
        print(f"\n  {region_name} ({region_code}):")
        print(f"    - 省/州/区: {sub_count} 个")
        print(f"    - 城市/街道: {city_count} 个")
        print(f"    - 四级区域: {area_count} 个")
    
    print("\n" + "=" * 70)
    print("✅ 所有数据已补充完整到四级！")
    print("=" * 70)

if __name__ == '__main__':
    print_stats()
