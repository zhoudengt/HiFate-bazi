#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区转换工具测试
"""

import pytest
from datetime import datetime
from server.utils.timezone_converter import (
    get_timezone,
    convert_to_utc,
    calculate_true_solar_time,
    convert_local_to_solar_time,
    format_datetime_for_bazi
)
from server.utils.timezone_mapping import match_location_to_timezone
from src.tool.LunarConverter import LunarConverter


class TestTimezoneMapping:
    """时区映射测试"""
    
    def test_match_location_china(self):
        """测试中国地点匹配"""
        assert match_location_to_timezone("中国") == "Asia/Shanghai"
        assert match_location_to_timezone("北京") == "Asia/Shanghai"
        assert match_location_to_timezone("上海") == "Asia/Shanghai"
        assert match_location_to_timezone("Beijing") == "Asia/Shanghai"
    
    def test_match_location_europe(self):
        """测试欧洲地点匹配"""
        assert match_location_to_timezone("德国") == "Europe/Berlin"
        assert match_location_to_timezone("Germany") == "Europe/Berlin"
        assert match_location_to_timezone("法国") == "Europe/Paris"
        assert match_location_to_timezone("France") == "Europe/Paris"
        assert match_location_to_timezone("英国") == "Europe/London"
        assert match_location_to_timezone("United Kingdom") == "Europe/London"
    
    def test_match_location_usa(self):
        """测试美国地点匹配"""
        assert match_location_to_timezone("美国") == "America/New_York"
        assert match_location_to_timezone("New York") == "America/New_York"
        assert match_location_to_timezone("Los Angeles") == "America/Los_Angeles"
    
    def test_match_location_not_found(self):
        """测试无法匹配的地点"""
        assert match_location_to_timezone("未知地点") is None
        assert match_location_to_timezone("") is None


class TestTimezoneConverter:
    """时区转换测试"""
    
    def test_get_timezone_by_location(self):
        """测试通过 location 获取时区（优先级1）"""
        timezone = get_timezone(location="德国")
        assert timezone == "Europe/Berlin"
    
    def test_get_timezone_by_coords(self):
        """测试通过经纬度获取时区（优先级2）"""
        # 北京经纬度（约116.4, 39.9）
        timezone = get_timezone(latitude=39.9, longitude=116.4)
        assert timezone == "Asia/Shanghai"
    
    def test_get_timezone_priority(self):
        """测试时区获取优先级（location > 经纬度）"""
        # 即使经纬度是北京，但 location 是德国，应该返回德国时区
        timezone = get_timezone(location="德国", latitude=39.9, longitude=116.4)
        assert timezone == "Europe/Berlin"
    
    def test_get_timezone_default(self):
        """测试默认时区（无 location 和经纬度）"""
        timezone = get_timezone()
        assert timezone == "Asia/Shanghai"
    
    def test_convert_to_utc_summer_time(self):
        """测试夏令时转换（欧洲夏季）"""
        # 1990年7月15日 14:30（德国夏令时 CEST，UTC+2）
        utc_dt, timezone_info = convert_to_utc("14:30", "Europe/Berlin", "1990-07-15")
        # 应该减去2小时，得到 12:30 UTC
        assert utc_dt.hour == 12
        assert utc_dt.minute == 30
        assert "CEST" in timezone_info or "Europe/Berlin" in timezone_info
    
    def test_convert_to_utc_winter_time(self):
        """测试冬令时转换（欧洲冬季）"""
        # 1990年1月15日 14:30（德国冬令时 CET，UTC+1）
        utc_dt, timezone_info = convert_to_utc("14:30", "Europe/Berlin", "1990-01-15")
        # 应该减去1小时，得到 13:30 UTC
        assert utc_dt.hour == 13
        assert utc_dt.minute == 30
        assert "CET" in timezone_info or "Europe/Berlin" in timezone_info
    
    def test_calculate_true_solar_time(self):
        """测试真太阳时计算"""
        # UTC时间：1990-07-15 12:30:00
        utc_time = datetime(1990, 7, 15, 12, 30, 0)
        # 北京经度：116.4度
        true_solar_time = calculate_true_solar_time(utc_time, 116.4)
        # 时差 = (116.4 - 120) * 4 = -14.4 分钟
        # 真太阳时 = 12:30 - 14.4分钟 ≈ 12:15
        assert true_solar_time.minute == 15  # 约等于（可能有精度误差）
    
    def test_convert_local_to_solar_time(self):
        """测试完整流程：本地时间转真太阳时"""
        true_solar_time, timezone_info = convert_local_to_solar_time(
            "14:30",
            "1990-07-15",
            location="德国",
            latitude=52.5,  # 柏林纬度
            longitude=13.4  # 柏林经度
        )
        # 验证返回的是 datetime 对象
        assert isinstance(true_solar_time, datetime)
        # 验证时区信息
        assert timezone_info is not None
    
    def test_format_datetime_for_bazi(self):
        """测试 datetime 格式化"""
        dt = datetime(1990, 7, 15, 12, 30, 0)
        date_str, time_str = format_datetime_for_bazi(dt)
        assert date_str == "1990-07-15"
        assert time_str == "12:30"


class TestLunarConverter:
    """农历转换测试"""
    
    def test_lunar_to_solar_basic(self):
        """测试基本农历转阳历"""
        # 2024年正月初一（农历）
        result = LunarConverter.lunar_to_solar(2024, 1, 1, False, "12:00")
        assert 'solar_date' in result
        assert 'solar_time' in result
        assert result['solar_year'] == 2024
        # 正月初一应该在1月或2月
        assert result['solar_month'] in [1, 2]
    
    def test_lunar_to_solar_from_string(self):
        """测试字符串格式农历转阳历"""
        # 2024年正月初一
        result = LunarConverter.lunar_to_solar_from_string("2024年正月初一", "12:00")
        assert 'solar_date' in result
        assert 'solar_time' in result
    
    def test_lunar_to_solar_leap_month(self):
        """测试闰月转换"""
        # 尝试转换闰月（如果存在）
        try:
            result = LunarConverter.lunar_to_solar(2024, 1, 1, True, "12:00")
            assert 'solar_date' in result
        except ValueError:
            # 如果该年没有闰月，这是正常的
            pass


class TestIntegration:
    """集成测试"""
    
    def test_lunar_input_with_timezone(self):
        """测试农历输入+时区转换完整流程"""
        # 模拟农历输入：2024年正月初一 12:00，地点：德国
        # 1. 农历转阳历
        lunar_result = LunarConverter.lunar_to_solar_from_string("2024年正月初一", "12:00")
        solar_date = lunar_result['solar_date']
        solar_time = lunar_result['solar_time']
        
        # 2. 时区转换
        true_solar_time, timezone_info = convert_local_to_solar_time(
            solar_time,
            solar_date,
            location="德国",
            longitude=13.4
        )
        
        # 验证结果
        assert isinstance(true_solar_time, datetime)
        assert timezone_info is not None
    
    def test_backward_compatibility(self):
        """测试向后兼容性（不传新参数）"""
        # 不传 calendar_type、location 等参数，应该使用默认值
        timezone = get_timezone()
        assert timezone == "Asia/Shanghai"
        
        # 不传 location 和经纬度，应该使用默认时区
        utc_dt, _ = convert_to_utc("12:00", "Asia/Shanghai", "1990-01-15")
        assert isinstance(utc_dt, datetime)

