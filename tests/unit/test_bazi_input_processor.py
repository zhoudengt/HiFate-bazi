#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字输入处理器单元测试
测试农历转换和时区转换的统一处理
"""

import unittest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.utils.bazi_input_processor import BaziInputProcessor


class TestBaziInputProcessor(unittest.TestCase):
    """BaziInputProcessor 测试类"""
    
    def test_process_input_solar_basic(self):
        """测试：阳历输入基本流程"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar"
        )
        
        self.assertEqual(info['original_date'], "1990-05-15")
        self.assertEqual(info['original_time'], "14:30")
        self.assertEqual(info['calendar_type'], "solar")
        self.assertFalse(info['converted'])
    
    def test_process_input_lunar_basic(self):
        """测试：农历输入基本流程"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="2024年正月初一",
            solar_time="12:00",
            calendar_type="lunar"
        )
        
        self.assertTrue(info.get('converted'))
        self.assertIn('lunar_to_solar', info)
        self.assertIsNotNone(final_date)
        self.assertIsNotNone(final_time)
    
    def test_process_input_lunar_date_format(self):
        """测试：农历 YYYY-MM-DD 格式"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="2024-01-01",  # 农历年月日
            solar_time="08:00",
            calendar_type="lunar"
        )
        
        self.assertTrue(info.get('converted'))
        self.assertIn('lunar_to_solar', info)
    
    def test_process_input_with_location(self):
        """测试：带地点的输入（触发时区转换）"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar",
            location="北京"
        )
        
        # 有 location 时应该有时区转换信息
        # timezone_info 可能是字符串或 None（取决于是否转换成功）
        self.assertIn('timezone_info', info)
    
    def test_process_input_with_coordinates(self):
        """测试：使用经纬度（触发时区转换）"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar",
            latitude=39.90,
            longitude=116.40
        )
        
        # 有经纬度时应该有时区转换信息
        self.assertIn('timezone_info', info)
    
    def test_process_input_lunar_and_timezone(self):
        """测试：农历输入 + 时区转换（组合场景）"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="2024年正月初一",
            solar_time="12:00",
            calendar_type="lunar",
            location="北京"
        )
        
        self.assertTrue(info.get('converted'))
        self.assertIn('lunar_to_solar', info)
    
    def test_process_input_default_calendar_type(self):
        """测试：默认日历类型为 solar"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30"
        )
        
        self.assertEqual(info['calendar_type'], "solar")
        self.assertFalse(info['converted'])
    
    def test_process_input_returns_tuple(self):
        """测试：返回值是三元组"""
        result = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30"
        )
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], str)  # final_date
        self.assertIsInstance(result[1], str)  # final_time
        self.assertIsInstance(result[2], dict)  # info
    
    def test_process_input_final_values_in_info(self):
        """测试：conversion_info 包含 final_date 和 final_time"""
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30"
        )
        
        self.assertEqual(info['final_date'], final_date)
        self.assertEqual(info['final_time'], final_time)
    
    def test_process_input_invalid_lunar_date(self):
        """测试：无效的农历日期"""
        with self.assertRaises(ValueError):
            BaziInputProcessor.process_input(
                solar_date="无效日期",
                solar_time="12:00",
                calendar_type="lunar"
            )


if __name__ == '__main__':
    unittest.main()
