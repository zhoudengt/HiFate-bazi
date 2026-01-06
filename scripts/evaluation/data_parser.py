# -*- coding: utf-8 -*-
"""
数据解析器

解析Excel中的日期、性别等数据。
"""

import re
from typing import Tuple, Optional
from datetime import datetime


class DataParser:
    """数据解析器"""
    
    # 中文数字映射
    CHINESE_NUMS = {
        '零': 0, '〇': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '十一': 11, '十二': 12
    }
    
    @classmethod
    def parse_birth_date(cls, text: str, default_time: str = "12:00") -> Tuple[str, str]:
        """
        解析出生日期文本
        
        支持格式：
        - "1985 年 10 月 21 日"
        - "1985年10月21日"
        - "1985-10-21"
        - "1985/10/21"
        
        Args:
            text: 日期文本
            default_time: 默认时间
            
        Returns:
            (solar_date, solar_time) 元组，格式为 ("YYYY-MM-DD", "HH:MM")
        """
        if not text or str(text).strip() == "" or str(text) == "nan":
            raise ValueError("日期为空")
        
        text = str(text).strip()
        
        # 尝试匹配各种格式
        patterns = [
            # 1985 年 10 月 21 日（带空格）
            r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
            # 1985年10月21日（无空格）
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            # 1985-10-21 或 1985/10/21
            r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                year, month, day = match.groups()
                year = int(year)
                month = int(month)
                day = int(day)
                
                # 验证日期有效性
                try:
                    datetime(year, month, day)
                except ValueError as e:
                    raise ValueError(f"无效日期: {year}-{month}-{day}, {e}")
                
                solar_date = f"{year:04d}-{month:02d}-{day:02d}"
                return solar_date, default_time
        
        raise ValueError(f"无法解析日期格式: {text}")
    
    @classmethod
    def parse_gender(cls, text: str) -> str:
        """
        解析性别文本
        
        Args:
            text: 性别文本（如"男"、"女"、"male"、"female"）
            
        Returns:
            标准化的性别值 "male" 或 "female"
        """
        if not text or str(text).strip() == "" or str(text) == "nan":
            raise ValueError("性别为空")
        
        text = str(text).strip().lower()
        
        if text in ['男', 'male', 'm', '1']:
            return 'male'
        elif text in ['女', 'female', 'f', '0', '2']:
            return 'female'
        else:
            raise ValueError(f"无法识别的性别: {text}")
    
    @classmethod
    def parse_birth_datetime(cls, date_text: str, time_text: Optional[str] = None, 
                             default_time: str = "12:00") -> Tuple[str, str]:
        """
        解析出生日期和时间
        
        Args:
            date_text: 日期文本
            time_text: 时间文本（可选）
            default_time: 默认时间
            
        Returns:
            (solar_date, solar_time) 元组
        """
        solar_date, _ = cls.parse_birth_date(date_text, default_time)
        
        if time_text and str(time_text).strip() not in ["", "nan"]:
            # 尝试解析时间
            time_str = str(time_text).strip()
            
            # 匹配 HH:MM 格式
            time_match = re.match(r'(\d{1,2}):(\d{2})', time_str)
            if time_match:
                hour, minute = time_match.groups()
                solar_time = f"{int(hour):02d}:{minute}"
                return solar_date, solar_time
            
            # 匹配纯数字（如 "12" 表示12点）
            if time_str.isdigit():
                hour = int(time_str)
                if 0 <= hour <= 23:
                    solar_time = f"{hour:02d}:00"
                    return solar_date, solar_time
        
        return solar_date, default_time
    
    @classmethod
    def extract_year_month_day(cls, solar_date: str) -> Tuple[int, int, int]:
        """
        从日期字符串提取年月日
        
        Args:
            solar_date: 日期字符串，格式 "YYYY-MM-DD"
            
        Returns:
            (year, month, day) 元组
        """
        parts = solar_date.split('-')
        return int(parts[0]), int(parts[1]), int(parts[2])
    
    @classmethod
    def extract_hour(cls, solar_time: str) -> int:
        """
        从时间字符串提取小时
        
        Args:
            solar_time: 时间字符串，格式 "HH:MM"
            
        Returns:
            小时数
        """
        parts = solar_time.split(':')
        return int(parts[0])

