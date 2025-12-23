#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lunar_python import Solar, Lunar
from datetime import datetime, timedelta

class LunarConverter:
    """农历转换工具类 - 提供统一的公历转农历方法"""

    @staticmethod
    def solar_to_lunar(solar_date, solar_time=None):
        """
        将公历日期时间转换为农历信息
        Args:
            solar_date: 公历日期，格式 'YYYY-MM-DD'
            solar_time: 公历时间，格式 'HH:MM'，可选
        Returns:
            dict: 包含农历信息和八字四柱的字典
        """
        # 解析日期
        year, month, day = map(int, solar_date.split('-'))

        # 处理时间
        if solar_time:
            hour, minute = map(int, solar_time.split(':'))
        else:
            hour, minute = 12, 0  # 默认中午12点

        # 处理子时情况（23:00-24:00）
        adjusted_year, adjusted_month, adjusted_day = year, month, day
        adjusted_hour, adjusted_minute = hour, minute
        is_zi_shi_adjusted = False

        if hour >= 23:
            # 日期加1天，时间设为0点
            current_date = datetime(year, month, day)
            next_date = current_date + timedelta(days=1)
            adjusted_year, adjusted_month, adjusted_day = next_date.year, next_date.month, next_date.day
            adjusted_hour = 0
            is_zi_shi_adjusted = True

        # 创建阳历对象（使用调整后的日期时间）
        solar = Solar.fromYmdHms(adjusted_year, adjusted_month, adjusted_day, adjusted_hour, adjusted_minute, 0)

        # 转换为农历
        lunar = solar.getLunar()

        # 获取八字信息
        bazi = lunar.getBaZi()

        # 获取原始日期的年柱
        original_solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
        original_lunar = original_solar.getLunar()
        original_bazi = original_lunar.getBaZi()

        # 解析四柱 - 年柱使用原始日期，其他柱使用调整后日期
        bazi_pillars = {
            'year': {'stem': original_bazi[0][0], 'branch': original_bazi[0][1]},  # 使用原始日期年柱
            'month': {'stem': bazi[1][0], 'branch': bazi[1][1]},  # 使用调整后日期
            'day': {'stem': bazi[2][0], 'branch': bazi[2][1]},    # 使用调整后日期
            'hour': {'stem': bazi[3][0], 'branch': bazi[3][1]}    # 使用调整后日期
        }

        # 保存农历日期
        lunar_date = {
            'year': lunar.getYear(),
            'month': lunar.getMonth(),
            'day': lunar.getDay(),
            'month_name': lunar.getMonthInChinese(),
            'day_name': lunar.getDayInChinese(),
            # 兼容性处理：尝试不同的方法
            'is_leap_month': LunarConverter._get_leap_month_status(lunar)
        }

        return {
            'lunar_date': lunar_date,
            'bazi_pillars': bazi_pillars,
            'adjusted_solar_date': f"{adjusted_year:04d}-{adjusted_month:02d}-{adjusted_day:02d}",
            'adjusted_solar_time': f"{adjusted_hour:02d}:{adjusted_minute:02d}",
            'is_zi_shi_adjusted': is_zi_shi_adjusted
        }

    @staticmethod
    def _get_leap_month_status(lunar):
        """获取闰月状态 - 兼容性方法"""
        try:
            # 尝试方法1: isLeap()
            if hasattr(lunar, 'isLeap'):
                return lunar.isLeap()
            # 尝试方法2: getLeap()
            elif hasattr(lunar, 'getLeap'):
                leap_month = lunar.getLeap()
                return leap_month != 0
            # 尝试方法3: getLeapMonth()
            elif hasattr(lunar, 'getLeapMonth'):
                leap_month = lunar.getLeapMonth()
                return leap_month != 0
            else:
                # 如果都没有，默认返回 False
                return False
        except:
            return False

    @staticmethod
    def get_ganzhi_by_solar(solar_date, solar_time=None):
        """
        获取指定公历日期时间的干支
        Args:
            solar_date: 公历日期，格式 'YYYY-MM-DD'
            solar_time: 公历时间，格式 'HH:MM'，可选
        Returns:
            dict: 包含干支信息的字典
        """
        result = LunarConverter.solar_to_lunar(solar_date, solar_time)
        return result['bazi_pillars']

    @staticmethod
    def get_year_ganzhi(year):
        """
        获取指定年份的年柱干支
        Args:
            year: 年份
        Returns:
            dict: 年柱干支信息
        """
        solar_date = f"{year}-01-01"
        result = LunarConverter.solar_to_lunar(solar_date, "12:00")
        return {
            'stem': result['bazi_pillars']['year']['stem'],
            'branch': result['bazi_pillars']['year']['branch']
        }

    @staticmethod
    def get_month_ganzhi(year, month, day):
        """
        获取指定公历日期的月柱干支
        Args:
            year: 年
            month: 月
            day: 日
        Returns:
            dict: 月柱干支信息
        """
        solar_date = f"{year}-{month:02d}-{day:02d}"
        result = LunarConverter.solar_to_lunar(solar_date, "12:00")
        return {
            'stem': result['bazi_pillars']['month']['stem'],
            'branch': result['bazi_pillars']['month']['branch']
        }

    @staticmethod
    def get_day_ganzhi(year, month, day):
        """
        获取指定公历日期的日柱干支
        Args:
            year: 年
            month: 月
            day: 日
        Returns:
            dict: 日柱干支信息
        """
        solar_date = f"{year}-{month:02d}-{day:02d}"
        result = LunarConverter.solar_to_lunar(solar_date, "12:00")
        return {
            'stem': result['bazi_pillars']['day']['stem'],
            'branch': result['bazi_pillars']['day']['branch']
        }

    @staticmethod
    def get_hour_ganzhi(year, month, day, hour, minute=0):
        """
        获取指定公历日期时间的时柱干支
        Args:
            year: 年
            month: 月
            day: 日
            hour: 时
            minute: 分
        Returns:
            dict: 时柱干支信息
        """
        solar_date = f"{year}-{month:02d}-{day:02d}"
        solar_time = f"{hour:02d}:{minute:02d}"
        result = LunarConverter.solar_to_lunar(solar_date, solar_time)
        return {
            'stem': result['bazi_pillars']['hour']['stem'],
            'branch': result['bazi_pillars']['hour']['branch']
        }

    @staticmethod
    def lunar_to_solar(lunar_year, lunar_month, lunar_day, is_leap_month=False, lunar_time=None):
        """
        将农历日期时间转换为公历信息
        
        Args:
            lunar_year: 农历年份
            lunar_month: 农历月份
            lunar_day: 农历日期
            is_leap_month: 是否为闰月，默认 False
            lunar_time: 农历时间，格式 'HH:MM'，可选
        
        Returns:
            dict: 包含公历日期时间和农历信息的字典
        """
        try:
            # 创建农历对象
            if is_leap_month:
                # 如果是闰月，需要特殊处理
                lunar = Lunar.fromYmd(lunar_year, lunar_month, lunar_day, is_leap_month)
            else:
                lunar = Lunar.fromYmd(lunar_year, lunar_month, lunar_day)
            
            # 转换为阳历
            solar = lunar.getSolar()
            
            # 获取阳历日期
            solar_year = solar.getYear()
            solar_month = solar.getMonth()
            solar_day = solar.getDay()
            
            # 处理时间
            if lunar_time:
                hour, minute = map(int, lunar_time.split(':'))
            else:
                hour, minute = 12, 0  # 默认中午12点
            
            # 格式化阳历日期
            solar_date = f"{solar_year:04d}-{solar_month:02d}-{solar_day:02d}"
            solar_time_str = f"{hour:02d}:{minute:02d}"
            
            # 获取农历信息（用于验证）
            lunar_info = {
                'year': lunar.getYear(),
                'month': lunar.getMonth(),
                'day': lunar.getDay(),
                'month_name': lunar.getMonthInChinese(),
                'day_name': lunar.getDayInChinese(),
                'is_leap_month': LunarConverter._get_leap_month_status(lunar)
            }
            
            return {
                'solar_date': solar_date,
                'solar_time': solar_time_str,
                'solar_year': solar_year,
                'solar_month': solar_month,
                'solar_day': solar_day,
                'solar_hour': hour,
                'solar_minute': minute,
                'lunar_date': lunar_info,
                'original_lunar': {
                    'year': lunar_year,
                    'month': lunar_month,
                    'day': lunar_day,
                    'is_leap_month': is_leap_month
                }
            }
        
        except Exception as e:
            raise ValueError(f"农历转阳历失败: {e}")

    @staticmethod
    def lunar_to_solar_from_string(lunar_date_str, lunar_time=None):
        """
        从字符串解析农历日期并转换为公历
        
        Args:
            lunar_date_str: 农历日期字符串，格式支持：
                - "2024年正月初一"
                - "2024-01-01" (农历年月日)
                - "2024年闰正月十五"
            lunar_time: 农历时间，格式 'HH:MM'，可选
        
        Returns:
            dict: 包含公历日期时间和农历信息的字典
        """
        import re
        
        # 解析农历日期字符串
        is_leap_month = False
        lunar_year = None
        lunar_month = None
        lunar_day = None
        
        # 尝试匹配 "2024年正月初一" 格式
        match1 = re.match(r'(\d{4})年(闰)?([正一二三四五六七八九十]+)月([初一二三四五六七八九十]+|[廿卅]+[一二三四五六七八九十]?)', lunar_date_str)
        if match1:
            lunar_year = int(match1.group(1))
            is_leap_month = match1.group(2) == '闰'
            month_str = match1.group(3)
            day_str = match1.group(4)
            
            # 转换月份（中文数字转阿拉伯数字）
            month_map = {
                '正': 1, '一': 1, '二': 2, '三': 3, '四': 4,
                '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
                '十': 10, '十一': 11, '十二': 12
            }
            lunar_month = month_map.get(month_str, 1)
            
            # 转换日期（中文数字转阿拉伯数字）
            day_map = {
                '初一': 1, '初二': 2, '初三': 3, '初四': 4, '初五': 5,
                '初六': 6, '初七': 7, '初八': 8, '初九': 9, '初十': 10,
                '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
                '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
                '廿一': 21, '廿二': 22, '廿三': 23, '廿四': 24, '廿五': 25,
                '廿六': 26, '廿七': 27, '廿八': 28, '廿九': 29, '三十': 30
            }
            lunar_day = day_map.get(day_str, 1)
        
        # 尝试匹配 "2024-01-01" 格式
        if not lunar_year:
            match2 = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', lunar_date_str)
            if match2:
                lunar_year = int(match2.group(1))
                lunar_month = int(match2.group(2))
                lunar_day = int(match2.group(3))
        
        if not lunar_year or not lunar_month or not lunar_day:
            raise ValueError(f"无法解析农历日期字符串: {lunar_date_str}")
        
        # 调用转换方法
        return LunarConverter.lunar_to_solar(lunar_year, lunar_month, lunar_day, is_leap_month, lunar_time)