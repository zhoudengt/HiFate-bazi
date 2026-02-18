#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区转换工具类
提供时区识别、时区转换、夏令时处理和真太阳时计算功能
"""

import math
import pytz
from datetime import datetime, timedelta
from typing import Optional, Tuple
from server.utils.timezone_mapping import match_location_to_timezone


def get_timezone(location: Optional[str] = None, 
                 latitude: Optional[float] = None, 
                 longitude: Optional[float] = None) -> str:
    """
    获取时区（优先级：location > 经纬度 > 默认）
    
    Args:
        location: 地点字符串（优先级1）
        latitude: 纬度（优先级2）
        longitude: 经度（优先级2）
    
    Returns:
        时区字符串（如 "Asia/Shanghai"）
    """
    # 优先级1：Location字符串匹配
    if location:
        timezone = match_location_to_timezone(location)
        if timezone:
            return timezone
    
    # 优先级2：经纬度计算
    if latitude is not None and longitude is not None:
        timezone = calculate_timezone_from_coords(latitude, longitude)
        if timezone:
            return timezone
    
    # 默认：北京时间
    return "Asia/Shanghai"


def _is_in_china(latitude: float, longitude: float) -> bool:
    """粗略判断经纬度是否在中国境内（含港澳台）"""
    return 18.0 <= latitude <= 54.0 and 73.0 <= longitude <= 136.0


def calculate_timezone_from_coords(latitude: float, longitude: float) -> Optional[str]:
    """
    根据经纬度计算时区
    
    特殊处理：中国全境使用 UTC+8 (Asia/Shanghai)，不按经度切分。
    其他地区按经度近似推算。
    
    Args:
        latitude: 纬度
        longitude: 经度
    
    Returns:
        时区字符串，如果无法计算则返回 None
    """
    if _is_in_china(latitude, longitude):
        return "Asia/Shanghai"

    utc_offset = round(longitude / 15)

    timezone_map = {
        -12: "Pacific/Auckland",
        -11: "Pacific/Honolulu",
        -10: "America/Anchorage",
        -9: "America/Los_Angeles",
        -8: "America/Los_Angeles",
        -7: "America/Denver",
        -6: "America/Chicago",
        -5: "America/New_York",
        -4: "America/Caracas",
        -3: "America/Sao_Paulo",
        -2: "Atlantic/South_Georgia",
        -1: "Atlantic/Azores",
        0: "Europe/London",
        1: "Europe/Paris",
        2: "Europe/Berlin",
        3: "Europe/Moscow",
        4: "Asia/Dubai",
        5: "Asia/Karachi",
        6: "Asia/Dhaka",
        7: "Asia/Bangkok",
        8: "Asia/Shanghai",
        9: "Asia/Tokyo",
        10: "Australia/Sydney",
        11: "Pacific/Guadalcanal",
        12: "Pacific/Auckland",
    }

    if utc_offset in timezone_map:
        return timezone_map[utc_offset]

    closest_offset = min(timezone_map.keys(), key=lambda x: abs(x - utc_offset))
    return timezone_map[closest_offset]


def convert_to_utc(local_time_str: str, 
                   timezone_str: str, 
                   date_str: Optional[str] = None) -> Tuple[datetime, str]:
    """
    将本地时间转换为UTC（自动处理夏令时）
    
    夏令时处理机制：
    - pytz.timezone() 获取的时区对象包含夏令时规则（基于IANA时区数据库）
    - tz.localize() 会自动判断该日期是否在夏令时期间
    - 如果在夏令时期间，会自动添加夏令时偏移量（通常+1小时）
    - 然后转换为UTC，保证了时间的准确性
    
    示例：
    - 输入：1989-07-15 14:00 (夏令时期间的北京时间)
    - pytz识别：该日期在夏令时期间，自动减去1小时
    - 转换：14:00 (DST) → 13:00 (标准时间) → UTC时间
    
    Args:
        local_time_str: 本地时间字符串，格式 "HH:MM"
        timezone_str: 时区字符串（如 "Europe/Berlin"）
        date_str: 日期字符串，格式 "YYYY-MM-DD"，如果为None则使用当前日期
    
    Returns:
        (utc_datetime, timezone_info) - UTC时间对象和时区信息字符串
    """
    try:
        # 解析时间
        hour, minute = map(int, local_time_str.split(':'))
        
        # 解析日期
        if date_str:
            year, month, day = map(int, date_str.split('-'))
        else:
            now = datetime.now()
            year, month, day = now.year, now.month, now.day
        
        # 创建本地时间对象（naive datetime）
        local_dt = datetime(year, month, day, hour, minute, 0)
        
        # 获取时区对象（包含夏令时规则）
        tz = pytz.timezone(timezone_str)
        
        # 本地化（自动处理夏令时）
        # ⚠️ 关键：pytz.localize() 会自动识别该日期是否在夏令时期间
        # 如果在夏令时期间，会自动应用夏令时偏移量
        localized_dt = tz.localize(local_dt)
        
        # 转换为UTC
        utc_dt = localized_dt.astimezone(pytz.UTC)
        
        # 获取时区信息（用于日志）
        timezone_info = f"{timezone_str} ({localized_dt.strftime('%Z')})"
        
        return utc_dt, timezone_info
    
    except Exception as e:
        # 如果转换失败，返回原始时间（假设已经是UTC）
        hour, minute = map(int, local_time_str.split(':'))
        if date_str:
            year, month, day = map(int, date_str.split('-'))
        else:
            now = datetime.now()
            year, month, day = now.year, now.month, now.day
        return datetime(year, month, day, hour, minute, 0), f"{timezone_str} (fallback)"


def _equation_of_time(dt: datetime) -> float:
    """
    计算均时差（Equation of Time），单位：分钟。
    
    均时差 = 真太阳时 − 地方平太阳时
    正值表示真太阳时快于平太阳时，负值表示慢于。
    
    使用 Spencer (1971) 近似公式，精度约 ±30 秒，满足八字排盘需求。
    
    Args:
        dt: 日期时间对象
    
    Returns:
        均时差（分钟），正值表示真太阳快于平太阳
    """
    day_of_year = dt.timetuple().tm_yday
    B = 2 * math.pi * (day_of_year - 81) / 365.0
    eot = (9.87 * math.sin(2 * B)
           - 7.53 * math.cos(B)
           - 1.50 * math.sin(B))
    return eot


def calculate_true_solar_time(utc_time: datetime, longitude: float) -> datetime:
    """
    计算真太阳时（地方真太阳时）
    
    真太阳时 = 地方平太阳时 + 均时差
    地方平太阳时 = UTC + 经度×4 分钟
    
    Args:
        utc_time: UTC时间对象
        longitude: 经度（东经为正，西经为负）
    
    Returns:
        该经度处的地方真太阳时
    """
    local_mean_solar_minutes = longitude * 4
    eot = _equation_of_time(utc_time)
    true_solar_time = utc_time + timedelta(minutes=local_mean_solar_minutes + eot)
    return true_solar_time


def convert_local_to_solar_time(local_time_str: str,
                                date_str: str,
                                location: Optional[str] = None,
                                latitude: Optional[float] = None,
                                longitude: Optional[float] = None) -> Tuple[datetime, str]:
    """
    将本地时间转换为真太阳时（完整流程）
    
    夏令时处理说明：
    - 本函数会调用 convert_to_utc() 进行时区转换
    - convert_to_utc() 会自动处理夏令时，确保UTC时间准确
    - 真太阳时计算基于UTC时间，因此夏令时处理是关键步骤
    - 如果不正确处理夏令时，会导致：
      * UTC时间错误 → 真太阳时错误 → 时柱干支错误 → 八字计算错误
    
    处理流程：
    1. 本地时间（可能包含夏令时） → UTC时间（自动处理夏令时）
    2. UTC时间 → 真太阳时（基于经度差计算）
    
    Args:
        local_time_str: 本地时间字符串，格式 "HH:MM"
        date_str: 日期字符串，格式 "YYYY-MM-DD"
        location: 地点字符串（可选，优先级1）
        latitude: 纬度（可选，优先级2）
        longitude: 经度（可选，优先级2，用于真太阳时计算）
    
    Returns:
        (true_solar_time, timezone_info) - 真太阳时时间对象和时区信息字符串
    """
    # 1. 获取时区
    timezone_str = get_timezone(location, latitude, longitude)
    
    # 2. 转换为UTC（自动处理夏令时）
    # ⚠️ 重要：convert_to_utc() 会使用 pytz 自动识别和处理夏令时
    # 如果用户输入的时间是夏令时期间的本地时间，这里会自动转换
    utc_time, timezone_info = convert_to_utc(local_time_str, timezone_str, date_str)
    
    # 3. 计算真太阳时（如果有经度）
    if longitude is not None:
        true_solar_time = calculate_true_solar_time(utc_time, longitude)
    else:
        # 如果没有经度，使用UTC时间（近似）
        true_solar_time = utc_time
    
    return true_solar_time, timezone_info


def format_datetime_for_bazi(dt: datetime) -> Tuple[str, str]:
    """
    将datetime对象格式化为八字计算所需的日期和时间字符串
    
    Args:
        dt: datetime对象
    
    Returns:
        (date_str, time_str) - 日期字符串 "YYYY-MM-DD" 和时间字符串 "HH:MM"
    """
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M")
    return date_str, time_str

