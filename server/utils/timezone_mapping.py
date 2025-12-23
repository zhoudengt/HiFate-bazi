#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区映射配置
提供 Location 字符串到时区的映射表（支持中英文）
"""

# Location 字符串到时区的映射表
# 优先级：精确匹配 > 部分匹配 > 默认时区
LOCATION_TIMEZONE_MAP = {
    # 中国
    "中国": "Asia/Shanghai",
    "北京": "Asia/Shanghai",
    "上海": "Asia/Shanghai",
    "广州": "Asia/Shanghai",
    "深圳": "Asia/Shanghai",
    "杭州": "Asia/Shanghai",
    "成都": "Asia/Shanghai",
    "重庆": "Asia/Shanghai",
    "西安": "Asia/Shanghai",
    "武汉": "Asia/Shanghai",
    "南京": "Asia/Shanghai",
    "天津": "Asia/Shanghai",
    "苏州": "Asia/Shanghai",
    "China": "Asia/Shanghai",
    "Beijing": "Asia/Shanghai",
    "Shanghai": "Asia/Shanghai",
    
    # 欧洲
    "德国": "Europe/Berlin",
    "Deutschland": "Europe/Berlin",
    "Germany": "Europe/Berlin",
    "柏林": "Europe/Berlin",
    "Berlin": "Europe/Berlin",
    "慕尼黑": "Europe/Berlin",
    "Munich": "Europe/Berlin",
    
    "法国": "Europe/Paris",
    "France": "Europe/Paris",
    "巴黎": "Europe/Paris",
    "Paris": "Europe/Paris",
    
    "英国": "Europe/London",
    "United Kingdom": "Europe/London",
    "UK": "Europe/London",
    "伦敦": "Europe/London",
    "London": "Europe/London",
    
    "意大利": "Europe/Rome",
    "Italy": "Europe/Rome",
    "罗马": "Europe/Rome",
    "Rome": "Europe/Rome",
    "米兰": "Europe/Rome",
    "Milan": "Europe/Rome",
    
    "西班牙": "Europe/Madrid",
    "Spain": "Europe/Madrid",
    "马德里": "Europe/Madrid",
    "Madrid": "Europe/Madrid",
    "巴塞罗那": "Europe/Madrid",
    "Barcelona": "Europe/Madrid",
    
    "荷兰": "Europe/Amsterdam",
    "Netherlands": "Europe/Amsterdam",
    "阿姆斯特丹": "Europe/Amsterdam",
    "Amsterdam": "Europe/Amsterdam",
    
    "比利时": "Europe/Brussels",
    "Belgium": "Europe/Brussels",
    "布鲁塞尔": "Europe/Brussels",
    "Brussels": "Europe/Brussels",
    
    "瑞士": "Europe/Zurich",
    "Switzerland": "Europe/Zurich",
    "苏黎世": "Europe/Zurich",
    "Zurich": "Europe/Zurich",
    
    "奥地利": "Europe/Vienna",
    "Austria": "Europe/Vienna",
    "维也纳": "Europe/Vienna",
    "Vienna": "Europe/Vienna",
    
    "瑞典": "Europe/Stockholm",
    "Sweden": "Europe/Stockholm",
    "斯德哥尔摩": "Europe/Stockholm",
    "Stockholm": "Europe/Stockholm",
    
    "挪威": "Europe/Oslo",
    "Norway": "Europe/Oslo",
    "奥斯陆": "Europe/Oslo",
    "Oslo": "Europe/Oslo",
    
    "丹麦": "Europe/Copenhagen",
    "Denmark": "Europe/Copenhagen",
    "哥本哈根": "Europe/Copenhagen",
    "Copenhagen": "Europe/Copenhagen",
    
    "芬兰": "Europe/Helsinki",
    "Finland": "Europe/Helsinki",
    "赫尔辛基": "Europe/Helsinki",
    "Helsinki": "Europe/Helsinki",
    
    "波兰": "Europe/Warsaw",
    "Poland": "Europe/Warsaw",
    "华沙": "Europe/Warsaw",
    "Warsaw": "Europe/Warsaw",
    
    "俄罗斯": "Europe/Moscow",
    "Russia": "Europe/Moscow",
    "莫斯科": "Europe/Moscow",
    "Moscow": "Europe/Moscow",
    
    # 美国
    "美国": "America/New_York",  # 默认东部时间
    "United States": "America/New_York",
    "USA": "America/New_York",
    "US": "America/New_York",
    "纽约": "America/New_York",
    "New York": "America/New_York",
    "洛杉矶": "America/Los_Angeles",
    "Los Angeles": "America/Los_Angeles",
    "LA": "America/Los_Angeles",
    "芝加哥": "America/Chicago",
    "Chicago": "America/Chicago",
    "丹佛": "America/Denver",
    "Denver": "America/Denver",
    "旧金山": "America/Los_Angeles",
    "San Francisco": "America/Los_Angeles",
    "SF": "America/Los_Angeles",
    
    # 加拿大
    "加拿大": "America/Toronto",
    "Canada": "America/Toronto",
    "多伦多": "America/Toronto",
    "Toronto": "America/Toronto",
    "温哥华": "America/Vancouver",
    "Vancouver": "America/Vancouver",
    
    # 澳大利亚
    "澳大利亚": "Australia/Sydney",
    "Australia": "Australia/Sydney",
    "悉尼": "Australia/Sydney",
    "Sydney": "Australia/Sydney",
    "墨尔本": "Australia/Melbourne",
    "Melbourne": "Australia/Melbourne",
    
    # 日本
    "日本": "Asia/Tokyo",
    "Japan": "Asia/Tokyo",
    "东京": "Asia/Tokyo",
    "Tokyo": "Asia/Tokyo",
    "大阪": "Asia/Tokyo",
    "Osaka": "Asia/Tokyo",
    
    # 韩国
    "韩国": "Asia/Seoul",
    "Korea": "Asia/Seoul",
    "首尔": "Asia/Seoul",
    "Seoul": "Asia/Seoul",
    
    # 东南亚（不使用夏令时）
    "新加坡": "Asia/Singapore",
    "Singapore": "Asia/Singapore",
    "马来西亚": "Asia/Kuala_Lumpur",
    "Malaysia": "Asia/Kuala_Lumpur",
    "吉隆坡": "Asia/Kuala_Lumpur",
    "Kuala Lumpur": "Asia/Kuala_Lumpur",
    "泰国": "Asia/Bangkok",
    "Thailand": "Asia/Bangkok",
    "曼谷": "Asia/Bangkok",
    "Bangkok": "Asia/Bangkok",
    "越南": "Asia/Ho_Chi_Minh",
    "Vietnam": "Asia/Ho_Chi_Minh",
    "胡志明市": "Asia/Ho_Chi_Minh",
    "Ho Chi Minh": "Asia/Ho_Chi_Minh",
    "印度尼西亚": "Asia/Jakarta",
    "Indonesia": "Asia/Jakarta",
    "雅加达": "Asia/Jakarta",
    "Jakarta": "Asia/Jakarta",
    "菲律宾": "Asia/Manila",
    "Philippines": "Asia/Manila",
    "马尼拉": "Asia/Manila",
    "Manila": "Asia/Manila",
    
    # 印度
    "印度": "Asia/Kolkata",
    "India": "Asia/Kolkata",
    "新德里": "Asia/Kolkata",
    "New Delhi": "Asia/Kolkata",
    "孟买": "Asia/Kolkata",
    "Mumbai": "Asia/Kolkata",
    
    # 中东
    "阿联酋": "Asia/Dubai",
    "UAE": "Asia/Dubai",
    "迪拜": "Asia/Dubai",
    "Dubai": "Asia/Dubai",
}


def match_location_to_timezone(location: str) -> str:
    """
    根据 Location 字符串匹配时区
    
    Args:
        location: 地点字符串（支持中英文）
    
    Returns:
        时区字符串（如 "Asia/Shanghai"），如果无法匹配则返回 None
    """
    if not location:
        return None
    
    # 去除空格并转换为小写（英文）或保持原样（中文）
    location_clean = location.strip()
    
    # 精确匹配
    if location_clean in LOCATION_TIMEZONE_MAP:
        return LOCATION_TIMEZONE_MAP[location_clean]
    
    # 部分匹配（包含关系）
    location_lower = location_clean.lower()
    for key, timezone in LOCATION_TIMEZONE_MAP.items():
        if location_lower in key.lower() or key.lower() in location_lower:
            return timezone
    
    return None

