#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强四级数据 - 为重要城市补充更多区域
"""

import json

def enhance_important_cities(data):
    """为重要城市补充更多四级区域数据"""
    
    enhancements = {
        # 香港中环
        ('HK', 'HK-HCW', 'HK-HCW-CW'): {
            "HK-HCW-CW-IFC": {"name_zh": "国际金融中心", "name_en": "IFC", "latitude": 22.2850, "longitude": 114.1550},
            "HK-HCW-CW-LKF": {"name_zh": "兰桂坊", "name_en": "Lan Kwai Fong", "latitude": 22.2800, "longitude": 114.1520},
            "HK-HCW-CW-SO": {"name_zh": "苏豪区", "name_en": "Soho", "latitude": 22.2780, "longitude": 114.1500},
            "HK-HCW-CW-CP": {"name_zh": "中环码头", "name_en": "Central Pier", "latitude": 22.2880, "longitude": 114.1550},
            "HK-HCW-CW-LG": {"name_zh": "立法会", "name_en": "Legislative Council", "latitude": 22.2820, "longitude": 114.1580},
            "HK-HCW-CW-HK": {"name_zh": "香港站", "name_en": "Hong Kong Station", "latitude": 22.2850, "longitude": 114.1570}
        },
        # 香港尖沙咀
        ('HK', 'HK-KYT', 'HK-KYT-TST'): {
            "HK-KYT-TST-TS": {"name_zh": "尖沙咀", "name_en": "Tsim Sha Tsui", "latitude": 22.3000, "longitude": 114.1700},
            "HK-KYT-TST-CL": {"name_zh": "钟楼", "name_en": "Clock Tower", "latitude": 22.2950, "longitude": 114.1690},
            "HK-KYT-TST-HK": {"name_zh": "海港城", "name_en": "Harbour City", "latitude": 22.2980, "longitude": 114.1680},
            "HK-KYT-TST-MP": {"name_zh": "星光大道", "name_en": "Avenue of Stars", "latitude": 22.2930, "longitude": 114.1720}
        },
        # 香港旺角
        ('HK', 'HK-KYT', 'HK-KYT-MK'): {
            "HK-KYT-MK-MK": {"name_zh": "旺角", "name_en": "Mong Kok", "latitude": 22.3200, "longitude": 114.1700},
            "HK-KYT-MK-LG": {"name_zh": "朗豪坊", "name_en": "Langham Place", "latitude": 22.3180, "longitude": 114.1690},
            "HK-KYT-MK-LD": {"name_zh": "女人街", "name_en": "Ladies' Market", "latitude": 22.3200, "longitude": 114.1710}
        },
        # 美国洛杉矶
        ('US', 'US-CA', 'US-CA-LA'): {
            "US-CA-LA-DT": {"name_zh": "市中心", "name_en": "Downtown", "latitude": 34.0522, "longitude": -118.2437},
            "US-CA-LA-BH": {"name_zh": "比佛利山", "name_en": "Beverly Hills", "latitude": 34.0736, "longitude": -118.4004},
            "US-CA-LA-SM": {"name_zh": "圣莫尼卡", "name_en": "Santa Monica", "latitude": 34.0195, "longitude": -118.4912},
            "US-CA-LA-HW": {"name_zh": "好莱坞", "name_en": "Hollywood", "latitude": 34.0928, "longitude": -118.3287},
            "US-CA-LA-VB": {"name_zh": "威尼斯海滩", "name_en": "Venice Beach", "latitude": 34.0522, "longitude": -118.4695}
        },
        # 美国纽约
        ('US', 'US-NY', 'US-NY-NYC'): {
            "US-NY-NYC-MN": {"name_zh": "曼哈顿", "name_en": "Manhattan", "latitude": 40.7831, "longitude": -73.9712},
            "US-NY-NYC-BK": {"name_zh": "布鲁克林", "name_en": "Brooklyn", "latitude": 40.6782, "longitude": -73.9442},
            "US-NY-NYC-QS": {"name_zh": "皇后区", "name_en": "Queens", "latitude": 40.7282, "longitude": -73.7949},
            "US-NY-NYC-BX": {"name_zh": "布朗克斯", "name_en": "The Bronx", "latitude": 40.8448, "longitude": -73.8648},
            "US-NY-NYC-SI": {"name_zh": "史泰登岛", "name_en": "Staten Island", "latitude": 40.5795, "longitude": -74.1502}
        },
        # 美国芝加哥
        ('US', 'US-IL', 'US-IL-CHI'): {
            "US-IL-CHI-DT": {"name_zh": "市中心", "name_en": "Downtown", "latitude": 41.8781, "longitude": -87.6298},
            "US-IL-CHI-LP": {"name_zh": "林肯公园", "name_en": "Lincoln Park", "latitude": 41.9256, "longitude": -87.6388},
            "US-IL-CHI-LV": {"name_zh": "湖景", "name_en": "Lakeview", "latitude": 41.9400, "longitude": -87.6500}
        },
        # 台湾台北
        ('TW', 'TW-TPE', 'TW-TPE-ZZ'): {
            "TW-TPE-ZZ-ZZ": {"name_zh": "中正区", "name_en": "Zhongzheng", "latitude": 25.0320, "longitude": 121.5200},
            "TW-TPE-ZZ-TP": {"name_zh": "台北车站", "name_en": "Taipei Station", "latitude": 25.0479, "longitude": 121.5170},
            "TW-TPE-ZZ-PP": {"name_zh": "总统府", "name_en": "Presidential Office", "latitude": 25.0400, "longitude": 121.5120}
        },
        # 台湾台北信义区
        ('TW', 'TW-TPE', 'TW-TPE-XY'): {
            "TW-TPE-XY-XY": {"name_zh": "信义区", "name_en": "Xinyi", "latitude": 25.0300, "longitude": 121.5700},
            "TW-TPE-XY-TP": {"name_zh": "台北101", "name_en": "Taipei 101", "latitude": 25.0340, "longitude": 121.5645},
            "TW-TPE-XY-XM": {"name_zh": "信义商圈", "name_en": "Xinyi Shopping District", "latitude": 25.0330, "longitude": 121.5680}
        },
        # 新加坡中区
        ('SG', 'SG-01', 'SG-01-DTC'): {
            "SG-01-DTC-DT": {"name_zh": "市中心", "name_en": "Downtown", "latitude": 1.2800, "longitude": 103.8500},
            "SG-01-DTC-MB": {"name_zh": "滨海湾", "name_en": "Marina Bay", "latitude": 1.2810, "longitude": 103.8600},
            "SG-01-DTC-CQ": {"name_zh": "克拉码头", "name_en": "Clarke Quay", "latitude": 1.2900, "longitude": 103.8450}
        },
        # 泰国曼谷
        ('TH', 'TH-10', 'TH-10-BKK'): {
            "TH-10-BKK-SI": {"name_zh": "暹罗", "name_en": "Siam", "latitude": 13.7450, "longitude": 100.5340},
            "TH-10-BKK-SK": {"name_zh": "素坤逸", "name_en": "Sukhumvit", "latitude": 13.7300, "longitude": 100.5600},
            "TH-10-BKK-SL": {"name_zh": "是隆", "name_en": "Silom", "latitude": 13.7300, "longitude": 100.5300},
            "TH-10-BKK-RD": {"name_zh": "考山路", "name_en": "Khao San Road", "latitude": 13.7590, "longitude": 100.4970}
        },
        # 马来西亚吉隆坡
        ('MY', 'MY-KUL', None): {
            "MY-KUL-KL": {"name_zh": "吉隆坡", "name_en": "Kuala Lumpur", "latitude": 3.1390, "longitude": 101.6869},
            "MY-KUL-KLCC": {"name_zh": "双子塔", "name_en": "KLCC", "latitude": 3.1579, "longitude": 101.7117},
            "MY-KUL-BK": {"name_zh": "武吉免登", "name_en": "Bukit Bintang", "latitude": 3.1490, "longitude": 101.7100}
        },
        # 越南胡志明市
        ('VN', 'VN-SG', 'VN-SG-HCM'): {
            "VN-SG-HCM-D1": {"name_zh": "第一郡", "name_en": "District 1", "latitude": 10.7800, "longitude": 106.7000},
            "VN-SG-HCM-D3": {"name_zh": "第三郡", "name_en": "District 3", "latitude": 10.7800, "longitude": 106.6900},
            "VN-SG-HCM-BD": {"name_zh": "滨城市场", "name_en": "Ben Thanh Market", "latitude": 10.7720, "longitude": 106.6980}
        },
        # 印尼雅加达
        ('ID', 'ID-JK', 'ID-JK-JKT'): {
            "ID-JK-JKT-CT": {"name_zh": "中雅加达", "name_en": "Central Jakarta", "latitude": -6.2000, "longitude": 106.8400},
            "ID-JK-JKT-NJ": {"name_zh": "北雅加达", "name_en": "North Jakarta", "latitude": -6.1400, "longitude": 106.8100},
            "ID-JK-JKT-SJ": {"name_zh": "南雅加达", "name_en": "South Jakarta", "latitude": -6.2600, "longitude": 106.8100}
        },
        # 加拿大温哥华
        ('CA', 'CA-BC', 'CA-BC-VAN'): {
            "CA-BC-VAN-DT": {"name_zh": "市中心", "name_en": "Downtown", "latitude": 49.2827, "longitude": -123.1207},
            "CA-BC-VAN-ST": {"name_zh": "斯坦利公园", "name_en": "Stanley Park", "latitude": 49.3000, "longitude": -123.1400},
            "CA-BC-VAN-GT": {"name_zh": "煤气镇", "name_en": "Gastown", "latitude": 49.2830, "longitude": -123.1100}
        },
        # 加拿大多伦多
        ('CA', 'CA-ON', 'CA-ON-TO'): {
            "CA-ON-TO-DT": {"name_zh": "市中心", "name_en": "Downtown", "latitude": 43.6532, "longitude": -79.3832},
            "CA-ON-TO-CN": {"name_zh": "中国城", "name_en": "Chinatown", "latitude": 43.6500, "longitude": -79.4000},
            "CA-ON-TO-CN2": {"name_zh": "CN塔", "name_en": "CN Tower", "latitude": 43.6426, "longitude": -79.3871}
        }
    }
    
    total_added = 0
    
    for (region_code, sub_code, city_code), areas_data in enhancements.items():
        try:
            region = data['regions'].get(region_code)
            if not region:
                continue
            
            subdivision = region.get('subdivisions', {}).get(sub_code)
            if not subdivision:
                continue
            
            # 处理cities或major_cities
            city = None
            if city_code:
                city = subdivision.get('cities', {}).get(city_code) or subdivision.get('major_cities', {}).get(city_code)
            else:
                # 对于没有city_code的情况（如MY-KUL），直接添加到subdivision
                if 'areas' not in subdivision:
                    subdivision['areas'] = {}
                subdivision['areas'].update(areas_data)
                total_added += len(areas_data)
                continue
            
            if city:
                if 'areas' not in city:
                    city['areas'] = {}
                # 合并areas，不覆盖已有的
                for area_code, area_data in areas_data.items():
                    if area_code not in city['areas']:
                        city['areas'][area_code] = area_data
                        total_added += 1
        except Exception as e:
            print(f"处理 {region_code}/{sub_code}/{city_code} 时出错: {e}")
            continue
    
    return total_added

def main():
    file_path = 'region_code_table.json'
    
    print(f"正在读取 {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("正在增强重要城市的四级数据...")
    total_added = enhance_important_cities(data)
    
    print(f"共添加了 {total_added} 个四级区域数据")
    
    # 保存更新后的文件
    print(f"保存更新后的文件: {file_path}")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("完成！")

if __name__ == '__main__':
    main()
