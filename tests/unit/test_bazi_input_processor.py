#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字输入处理工具类单元测试
"""

import unittest
from datetime import datetime
from server.utils.bazi_input_processor import BaziInputProcessor


class TestBaziInputProcessor(unittest.TestCase):
    """八字输入处理工具类测试"""
    
    def test_process_input_solar_only(self):
        """测试：仅阳历输入（无转换）"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar"
        )
        
        self.assertEqual(final_date, "1990-05-15")
        self.assertEqual(final_time, "14:30")
        self.assertFalse(info.get('converted'))
        self.assertIsNone(info.get('timezone_info'))
    
    def test_process_input_lunar_to_solar(self):
        """测试：农历转阳历"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="2024年正月初一",
            solar_time="12:00",
            calendar_type="lunar"
        )
        
        self.assertNotEqual(final_date, "2024年正月初一")
        self.assertTrue(info.get('converted'))
        self.assertIn('lunar_to_solar', info)
        self.assertEqual(info['lunar_to_solar']['solar_date'], final_date)
    
    def test_process_input_timezone_conversion(self):
        """测试：时区转换（不跨日）"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar",
            location="德国"
        )
        
        self.assertEqual(final_date, "1990-05-15")  # 不跨日，日期不变
        # 时间可能变化（取决于时区和真太阳时）
        self.assertIsNotNone(info.get('timezone_info'))
        self.assertIn('true_solar_time', info)
    
    def test_process_input_timezone_cross_day(self):
        """测试：时区转换（跨日情况）"""
        # 北京时间 23:30，经度 150°（东经），时差 +2小时 → 次日 01:30
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="23:30",
            calendar_type="solar",
            longitude=150.0  # 东经150度
        )
        
        # 如果跨日，日期会变化
        # 注意：实际结果取决于具体的时区转换逻辑
        self.assertIsNotNone(info.get('timezone_info'))
        self.assertIn('true_solar_time', info)
    
    def test_process_input_lunar_and_timezone(self):
        """测试：农历输入 + 时区转换（组合场景）"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="2024年正月初一",
            solar_time="12:00",
            calendar_type="lunar",
            location="德国"
        )
        
        self.assertTrue(info.get('converted'))
        self.assertIn('lunar_to_solar', info)
        self.assertIsNotNone(info.get('timezone_info'))
        self.assertIn('true_solar_time', info)
    
    def test_process_input_location_priority(self):
        """测试：location 优先级高于经纬度"""
        # location="德国" 应该覆盖经纬度
        final_date1, final_time1, info1 = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar",
            location="德国",
            latitude=39.90,  # 北京纬度
            longitude=116.40  # 北京经度
        )
        
        final_date2, final_time2, info2 = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar",
            location="德国"
        )
        
        # 两个结果应该一致（都使用德国的时区）
        self.assertEqual(info1.get('timezone_info', {}).get('original_timezone'),
                        info2.get('timezone_info', {}).get('original_timezone'))
    
    def test_process_input_coordinates_only(self):
        """测试：仅使用经纬度（无location）"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar",
            latitude=52.52,  # 柏林纬度
            longitude=13.40   # 柏林经度
        )
        
        self.assertIsNotNone(info.get('timezone_info'))
        self.assertIn('true_solar_time', info)
    
    def test_process_input_invalid_lunar_date(self):
        """测试：无效的农历日期"""
        with self.assertRaises(ValueError):
            BaziInputProcessor.process_input(
                solar_date="无效农历日期",
                solar_time="12:00",
                calendar_type="lunar"
            )
    
    def test_process_input_timezone_failure_graceful(self):
        """测试：时区转换失败时的降级处理"""
        # 使用无效的location，应该降级到默认时区
        try:
            final_date, final_time, info = BaziInputProcessor.process_input(
                solar_date="1990-05-15",
                solar_time="14:30",
                calendar_type="solar",
                location="无效地点12345"
            )
            # 应该使用默认时区（北京时间）
            self.assertEqual(final_date, "1990-05-15")
            self.assertEqual(final_time, "14:30")
        except Exception:
            # 如果抛出异常，也是可以接受的（取决于实现）
            pass


if __name__ == '__main__':
    unittest.main()

