#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字输入处理工具类 - 统一处理农历转换和时区转换
"""

import logging
from typing import Optional, Tuple
from core.calculators.LunarConverter import LunarConverter
from server.utils.timezone_converter import convert_local_to_solar_time, format_datetime_for_bazi

logger = logging.getLogger(__name__)


class BaziInputProcessor:
    """八字输入处理工具类 - 统一处理农历转换和时区转换"""
    
    @staticmethod
    def process_input(
        solar_date: str,
        solar_time: str,
        calendar_type: Optional[str] = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Tuple[str, str, dict]:
        """
        处理八字输入（农历转换 + 时区转换）
        
        Args:
            solar_date: 日期字符串（阳历或农历）
            solar_time: 时间字符串
            calendar_type: 历法类型（solar/lunar），默认 solar
            location: 地点字符串（可选，优先级1）
            latitude: 纬度（可选，优先级2）
            longitude: 经度（可选，优先级2，用于真太阳时计算）
        
        Returns:
            (final_solar_date, final_solar_time, conversion_info) - 最终用于计算的阳历日期、时间和转换信息
        """
        conversion_info = {
            'original_date': solar_date,
            'original_time': solar_time,
            'calendar_type': calendar_type or "solar",
            'location': location,
            'latitude': latitude,
            'longitude': longitude,
            'converted': False,
            'timezone_info': None
        }
        
        final_solar_date = solar_date
        final_solar_time = solar_time
        
        # 步骤1：如果是农历输入，转换为阳历
        if calendar_type == "lunar":
            try:
                # 解析农历日期（假设格式为 YYYY-MM-DD，表示农历年月日）
                # 或者使用字符串格式（如 "2024年正月初一"）
                if '年' in solar_date or '月' in solar_date or '初' in solar_date or '廿' in solar_date or '卅' in solar_date:
                    # 字符串格式（如 "2024年正月初一"）
                    lunar_result = LunarConverter.lunar_to_solar_from_string(solar_date, solar_time)
                else:
                    # YYYY-MM-DD 格式（表示农历年月日）
                    parts = solar_date.split('-')
                    if len(parts) == 3:
                        lunar_year = int(parts[0])
                        lunar_month = int(parts[1])
                        lunar_day = int(parts[2])
                        # 检查是否为闰月（可以通过尝试创建农历对象来判断）
                        try:
                            lunar_result = LunarConverter.lunar_to_solar(lunar_year, lunar_month, lunar_day, False, solar_time)
                        except:
                            # 如果失败，尝试闰月
                            lunar_result = LunarConverter.lunar_to_solar(lunar_year, lunar_month, lunar_day, True, solar_time)
                    else:
                        raise ValueError(f"无法解析农历日期: {solar_date}")
                
                final_solar_date = lunar_result['solar_date']
                final_solar_time = lunar_result['solar_time']
                conversion_info['converted'] = True
                conversion_info['lunar_to_solar'] = lunar_result
            except Exception as e:
                raise ValueError(f"农历转阳历失败: {e}")
        
        # 步骤2：时区转换和真太阳时计算
        # ⚠️ 夏令时处理说明：
        # convert_local_to_solar_time() 内部会调用 convert_to_utc()
        # convert_to_utc() 使用 pytz 自动识别和处理夏令时
        # 如果用户输入的时间是夏令时期间的本地时间，系统会自动转换为标准时间
        # 这对于历史日期（如中国1986-1991年）尤其重要
        if location or (latitude is not None and longitude is not None):
            try:
                true_solar_time, timezone_info = convert_local_to_solar_time(
                    final_solar_time,
                    final_solar_date,
                    location,
                    latitude,
                    longitude
                )
                
                # 格式化为八字计算所需的格式
                final_solar_date, final_solar_time = format_datetime_for_bazi(true_solar_time)
                conversion_info['timezone_info'] = timezone_info
                conversion_info['true_solar_time'] = {
                    'date': final_solar_date,
                    'time': final_solar_time
                }
            except Exception as e:
                # 时区转换失败不影响计算，使用原始时间
                logger.warning(f"时区转换失败，使用原始时间: {e}")
        
        conversion_info['final_date'] = final_solar_date
        conversion_info['final_time'] = final_solar_time
        
        return final_solar_date, final_solar_time, conversion_info

