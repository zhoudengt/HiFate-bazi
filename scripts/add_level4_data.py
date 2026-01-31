#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量补充地区码表的四级数据
为所有三级数据（cities/major_cities）添加四级数据（areas）
"""

import json
import os

def add_areas_to_city(city_data, city_code, city_name_zh):
    """为单个城市添加areas数据"""
    if 'areas' in city_data:
        return 0  # 已有areas数据，跳过
    
    # 根据城市名称生成areas数据
    areas = {}
    
    # 为每个城市至少添加一个area（使用城市本身作为area）
    area_code = f"{city_code}-AREA"
    areas[area_code] = {
        "name_zh": city_name_zh,
        "name_en": city_data.get('name_en', ''),
        "latitude": city_data.get('latitude', 0),
        "longitude": city_data.get('longitude', 0)
    }
    
    # 为重要城市添加更多areas
    if 'HK' in city_code:  # 香港
        if 'CW' in city_code and 'HK-HCW-CW' in city_code:  # 中环
            areas[f"{city_code}-IFC"] = {"name_zh": "国际金融中心", "name_en": "IFC", "latitude": city_data.get('latitude', 0) + 0.005, "longitude": city_data.get('longitude', 0) + 0.005}
            areas[f"{city_code}-LKF"] = {"name_zh": "兰桂坊", "name_en": "Lan Kwai Fong", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0) + 0.002}
        elif 'TST' in city_code:  # 尖沙咀
            areas[f"{city_code}-TS"] = {"name_zh": "尖沙咀", "name_en": "Tsim Sha Tsui", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
        elif 'MK' in city_code and 'HK-KYT-MK' in city_code:  # 旺角
            areas[f"{city_code}-MK"] = {"name_zh": "旺角", "name_en": "Mong Kok", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'TW' in city_code:  # 台湾
        # 台湾的cities实际上是乡镇区，areas可以是村里
        areas[f"{city_code}-VILLAGE"] = {"name_zh": f"{city_name_zh}中心", "name_en": f"{city_data.get('name_en', '')} Center", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'US' in city_code:  # 美国
        # 美国城市添加主要社区/区域
        city_name_en = city_data.get('name_en', '')
        if 'LA' in city_code and 'US-CA-LA' in city_code:  # 洛杉矶
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
            areas[f"{city_code}-BH"] = {"name_zh": "比佛利山", "name_en": "Beverly Hills", "latitude": city_data.get('latitude', 0) + 0.05, "longitude": city_data.get('longitude', 0) - 0.05}
            areas[f"{city_code}-SM"] = {"name_zh": "圣莫尼卡", "name_en": "Santa Monica", "latitude": city_data.get('latitude', 0) - 0.05, "longitude": city_data.get('longitude', 0) - 0.05}
        elif 'NYC' in city_code:  # 纽约
            areas[f"{city_code}-MN"] = {"name_zh": "曼哈顿", "name_en": "Manhattan", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
            areas[f"{city_code}-BK"] = {"name_zh": "布鲁克林", "name_en": "Brooklyn", "latitude": city_data.get('latitude', 0) - 0.01, "longitude": city_data.get('longitude', 0) + 0.01}
            areas[f"{city_code}-QS"] = {"name_zh": "皇后区", "name_en": "Queens", "latitude": city_data.get('latitude', 0) - 0.01, "longitude": city_data.get('longitude', 0) + 0.02}
        elif 'CHI' in city_code:  # 芝加哥
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
            areas[f"{city_code}-LP"] = {"name_zh": "林肯公园", "name_en": "Lincoln Park", "latitude": city_data.get('latitude', 0) + 0.01, "longitude": city_data.get('longitude', 0)}
        elif 'HOU' in city_code:  # 休斯敦
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
        elif 'DAL' in city_code:  # 达拉斯
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
        else:
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'CA' in city_code and 'CA-' in city_code:  # 加拿大
        if 'VAN' in city_code:  # 温哥华
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
            areas[f"{city_code}-ST"] = {"name_zh": "斯坦利公园", "name_en": "Stanley Park", "latitude": city_data.get('latitude', 0) + 0.01, "longitude": city_data.get('longitude', 0) - 0.01}
        elif 'TO' in city_code and 'CA-ON-TO' in city_code:  # 多伦多
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
            areas[f"{city_code}-CN"] = {"name_zh": "中国城", "name_en": "Chinatown", "latitude": city_data.get('latitude', 0) - 0.005, "longitude": city_data.get('longitude', 0) + 0.005}
        else:
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'SG' in city_code:  # 新加坡
        areas[f"{city_code}-AREA"] = {"name_zh": city_name_zh, "name_en": city_data.get('name_en', ''), "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'MY' in city_code:  # 马来西亚
        areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'TH' in city_code:  # 泰国
        if 'BKK' in city_code or 'TH-10-BKK' in city_code:  # 曼谷
            areas[f"{city_code}-SI"] = {"name_zh": "暹罗", "name_en": "Siam", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
            areas[f"{city_code}-SK"] = {"name_zh": "素坤逸", "name_en": "Sukhumvit", "latitude": city_data.get('latitude', 0) - 0.01, "longitude": city_data.get('longitude', 0) + 0.01}
        else:
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'VN' in city_code:  # 越南
        if 'HCM' in city_code:  # 胡志明市
            areas[f"{city_code}-D1"] = {"name_zh": "第一郡", "name_en": "District 1", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
            areas[f"{city_code}-D3"] = {"name_zh": "第三郡", "name_en": "District 3", "latitude": city_data.get('latitude', 0) - 0.01, "longitude": city_data.get('longitude', 0)}
        else:
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'ID' in city_code:  # 印尼
        if 'JKT' in city_code:  # 雅加达
            areas[f"{city_code}-CT"] = {"name_zh": "中雅加达", "name_en": "Central Jakarta", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
        else:
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'PH' in city_code:  # 菲律宾
        if 'MNL' in city_code:  # 马尼拉
            areas[f"{city_code}-IN"] = {"name_zh": "因特拉穆罗斯", "name_en": "Intramuros", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
        else:
            areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    elif 'MX' in city_code:  # 墨西哥
        areas[f"{city_code}-DT"] = {"name_zh": "市中心", "name_en": "Downtown", "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    else:  # 其他地区
        areas[f"{city_code}-AREA"] = {"name_zh": city_name_zh, "name_en": city_data.get('name_en', ''), "latitude": city_data.get('latitude', 0), "longitude": city_data.get('longitude', 0)}
    
    city_data['areas'] = areas
    return len(areas)

def add_level4_data(data):
    """为所有三级数据添加四级数据"""
    total_added = 0
    
    # 遍历所有地区
    for region_code, region in data['regions'].items():
        subdivisions = region.get('subdivisions', {})
        
        for sub_code, sub_data in subdivisions.items():
            # 处理cities字段
            if 'cities' in sub_data:
                for city_code, city_data in sub_data['cities'].items():
                    city_name_zh = city_data.get('name_zh', '')
                    count = add_areas_to_city(city_data, city_code, city_name_zh)
                    total_added += count
            
            # 处理major_cities字段（美国等）
            if 'major_cities' in sub_data:
                for city_code, city_data in sub_data['major_cities'].items():
                    city_name_zh = city_data.get('name_zh', '')
                    count = add_areas_to_city(city_data, city_code, city_name_zh)
                    total_added += count
    
    return total_added

def main():
    file_path = 'region_code_table.json'
    
    print(f"正在读取 {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("正在补充四级数据...")
    total_added = add_level4_data(data)
    
    print(f"共添加了 {total_added} 个四级区域数据")
    
    # 备份原文件
    backup_path = file_path + '.backup'
    if not os.path.exists(backup_path):
        print(f"创建备份文件: {backup_path}")
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 保存更新后的文件
    print(f"保存更新后的文件: {file_path}")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("完成！")

if __name__ == '__main__':
    main()
