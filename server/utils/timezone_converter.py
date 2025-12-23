#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区转换工具类
提供时区识别、时区转换、夏令时处理和真太阳时计算功能
"""

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


def calculate_timezone_from_coords(latitude: float, longitude: float) -> Optional[str]:
    """
    根据经纬度计算时区
    
    Args:
        latitude: 纬度
        longitude: 经度
    
    Returns:
        时区字符串，如果无法计算则返回 None
    """
    # 根据经度计算时区（每15度差1小时）
    # UTC偏移量 = 经度 / 15
    utc_offset = round(longitude / 15)
    
    # 常见的时区映射（基于UTC偏移量）
    # 注意：这只是近似值，实际时区可能因夏令时和历史原因有所不同
    timezone_map = {
        -12: "Pacific/Auckland",  # 近似
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
    
    # 查找最接近的UTC偏移量
    if utc_offset in timezone_map:
        return timezone_map[utc_offset]
    
    # 如果不在映射表中，尝试查找最接近的值
    closest_offset = min(timezone_map.keys(), key=lambda x: abs(x - utc_offset))
    return timezone_map[closest_offset]


def convert_to_utc(local_time_str: str, 
                   timezone_str: str, 
                   date_str: Optional[str] = None) -> Tuple[datetime, str]:
    """
    将本地时间转换为UTC（自动处理夏令时）
    
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
        
        # 获取时区对象
        tz = pytz.timezone(timezone_str)
        
        # 本地化（自动处理夏令时）
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


def calculate_true_solar_time(utc_time: datetime, longitude: float) -> datetime:
    """
    计算真太阳时
    
    真太阳时 = UTC时间 + 时差
    时差 = (经度 - 120) * 4 分钟（120度是北京经度，每15度差1小时=60分钟，所以每度差4分钟）
    
    Args:
        utc_time: UTC时间对象
        longitude: 经度
    
    Returns:
        真太阳时时间对象
    """
    # 计算时差（分钟）
    # 每15度经度差1小时，所以每度差4分钟
    time_diff_minutes = (longitude - 120) * 4
    
    # 计算真太阳时
    true_solar_time = utc_time + timedelta(minutes=time_diff_minutes)
    
    return true_solar_time


def convert_local_to_solar_time(local_time_str: str,
                                date_str: str,
                                location: Optional[str] = None,
                                latitude: Optional[float] = None,
                                longitude: Optional[float] = None) -> Tuple[datetime, str]:
    """
    将本地时间转换为真太阳时（完整流程）
    
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
    
    # 2. 转换为UTC（处理夏令时）
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

