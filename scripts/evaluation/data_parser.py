#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评测数据解析器

生辰、性别等解析，供 bazi_evaluator、bazi_rule_matcher 使用。
"""

import re
from typing import Tuple


def parse_birth_with_time(text: str) -> Tuple[str, str]:
    """
    解析包含时间的生辰文本

    支持格式：
    - "1987年1月7日 9:15" / "1987年1月7日 09:15"
    - "1987 年 1 月 7 日 9:15"
    - "1987-01-07 9:15" / "1987/01/07 9:15"
    - "1987年1月7日"（无时间则默认 12:00）

    Returns:
        (solar_date, solar_time) 元组
    """
    if not text or str(text).strip() == "" or str(text) == "nan":
        raise ValueError("生辰为空")

    text = str(text).strip()

    date_patterns = [
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
    ]
    solar_date = None
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            solar_date = f"{year:04d}-{month:02d}-{day:02d}"
            break

    if not solar_date:
        raise ValueError(f"无法解析日期: {text}")

    ri_match = re.search(r'日\s*(\d{1,2})\s*[：:]\s*(\d{2})', text)
    if ri_match:
        hour = int(ri_match.group(1))
        minute = ri_match.group(2)
        if 0 <= hour <= 23:
            return solar_date, f"{hour:02d}:{minute}"

    time_match = re.search(r'(\d{1,2})\s*[：:]\s*(\d{2})\s*$', text)
    if time_match:
        hour = int(time_match.group(1))
        minute = time_match.group(2)
        if 0 <= hour <= 23:
            return solar_date, f"{hour:02d}:{minute}"

    return solar_date, "12:00"


def parse_gender(text: str) -> str:
    """
    解析性别文本
    Returns: "male" 或 "female"
    """
    if not text or str(text).strip() == "" or str(text) == "nan":
        raise ValueError("性别为空")
    text = str(text).strip().lower()
    if text in ['男', 'male', 'm', '1']:
        return 'male'
    elif text in ['女', 'female', 'f', '0', '2']:
        return 'female'
    raise ValueError(f"无法识别的性别: {text}")


def extract_year_month_day(solar_date: str) -> Tuple[int, int, int]:
    """从 YYYY-MM-DD 提取 (year, month, day)"""
    if not solar_date:
        raise ValueError("日期为空")
    parts = str(solar_date).strip().split('-')
    if len(parts) != 3:
        raise ValueError(f"日期格式错误: {solar_date}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def extract_hour(solar_time: str) -> int:
    """从 HH:MM 提取小时"""
    if not solar_time:
        return 12
    parts = str(solar_time).strip().split(':')
    return int(parts[0]) if parts else 12


class DataParser:
    """数据解析器（静态方法封装）"""
    parse_birth_with_time = staticmethod(parse_birth_with_time)
    parse_gender = staticmethod(parse_gender)
    extract_year_month_day = staticmethod(extract_year_month_day)
    extract_hour = staticmethod(extract_hour)
