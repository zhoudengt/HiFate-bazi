#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区映射配置
提供 Location 字符串到时区的映射表（支持中英文）

数据来源：
- LOCATION_TIMEZONE_MAP: 手工维护的常用地名（中国大陆、欧洲、日韩、印度、中东、澳洲等）
- region_timezone_data.json: 从 region_code_table.json 自动提取（港澳台、东南亚、北美，1389 条）
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

# ========================================================================
# 手工维护的常用地名映射
# 覆盖：中国大陆、欧洲、日韩、印度、中东、澳洲
# ========================================================================
LOCATION_TIMEZONE_MAP = {
    # 中国大陆（全境 UTC+8）
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
    "美国": "America/New_York",
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

# ========================================================================
# 从 region_code_table.json 提取的扩展映射（港澳台、东南亚、北美）
# 启动时加载一次，1389 条地名精确匹配
# ========================================================================
_REGION_TIMEZONE_MAP = {}


def _load_region_data():
    """加载 region_timezone_data.json（启动时执行一次）"""
    global _REGION_TIMEZONE_MAP
    data_path = os.path.join(os.path.dirname(__file__), "region_timezone_data.json")
    if not os.path.exists(data_path):
        return
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            _REGION_TIMEZONE_MAP = json.load(f)
        logger.debug(f"加载 region_timezone_data.json: {len(_REGION_TIMEZONE_MAP)} 条")
    except Exception as e:
        logger.warning(f"加载 region_timezone_data.json 失败: {e}")


_load_region_data()


def match_location_to_timezone(location: str) -> str:
    """
    根据 Location 字符串匹配时区

    匹配优先级：
    1. LOCATION_TIMEZONE_MAP 精确匹配（手工维护，高优先级）
    2. _REGION_TIMEZONE_MAP 精确匹配（region_code_table 提取，1389 条）
    3. LOCATION_TIMEZONE_MAP 部分匹配（包含关系）
    4. _REGION_TIMEZONE_MAP 部分匹配（包含关系）

    Args:
        location: 地点字符串（支持中英文）

    Returns:
        时区字符串（如 "Asia/Shanghai"），如果无法匹配则返回 None
    """
    if not location:
        return None

    location_clean = location.strip()

    # 1. 手工映射精确匹配
    if location_clean in LOCATION_TIMEZONE_MAP:
        return LOCATION_TIMEZONE_MAP[location_clean]

    # 2. region 数据精确匹配
    if location_clean in _REGION_TIMEZONE_MAP:
        return _REGION_TIMEZONE_MAP[location_clean]

    # 3. 手工映射部分匹配
    location_lower = location_clean.lower()
    for key, timezone in LOCATION_TIMEZONE_MAP.items():
        if location_lower in key.lower() or key.lower() in location_lower:
            return timezone

    # 4. region 数据部分匹配
    for key, timezone in _REGION_TIMEZONE_MAP.items():
        if location_lower in key.lower() or key.lower() in location_lower:
            return timezone

    return None
