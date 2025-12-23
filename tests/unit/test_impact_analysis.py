#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影响分析测试 - 验证时区转换对时柱和日柱的影响，确认年柱和月柱不受影响
"""

import unittest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.bazi_service import BaziService


class TestImpactAnalysis(unittest.TestCase):
    """影响分析测试"""
    
    def test_timezone_affects_hour_pillar_only(self):
        """测试：时区转换不跨日时，只影响时柱"""
        # 北京时间 14:30，转换为德国时间（UTC+1，夏令时UTC+2）
        # 使用经度 13.4°（柏林），真太阳时会有调整
        
        # 原始计算（无时区转换）
        result1 = BaziService.calculate_bazi_full(
            solar_date="1990-05-15",
            solar_time="14:30",
            gender="male"
        )
        
        # 带时区转换的计算
        final_date, final_time, conversion_info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar",
            location="德国"
        )
        
        result2 = BaziService.calculate_bazi_full(
            solar_date=final_date,
            solar_time=final_time,
            gender="male"
        )
        
        # 验证年柱和月柱不变
        pillars1 = result1.get('bazi', {}).get('bazi_pillars', {})
        pillars2 = result2.get('bazi', {}).get('bazi_pillars', {})
        
        self.assertEqual(pillars1.get('year'), pillars2.get('year'), "年柱应该不变")
        self.assertEqual(pillars1.get('month'), pillars2.get('month'), "月柱应该不变")
        
        # 时柱可能变化（取决于时区转换）
        # 如果时间变化导致日期变化，日柱也会变化
        if final_date == "1990-05-15":
            # 不跨日，日柱应该不变
            self.assertEqual(pillars1.get('day'), pillars2.get('day'), "日柱应该不变（不跨日）")
        else:
            # 跨日，日柱会变化
            self.assertNotEqual(pillars1.get('day'), pillars2.get('day'), "日柱应该变化（跨日）")
    
    def test_timezone_cross_day_affects_day_pillar(self):
        """测试：时区转换跨日时，影响日柱和时柱"""
        # 北京时间 23:30，经度 150°（东经），时差 +2小时 → 次日 01:30
        
        # 原始计算
        result1 = BaziService.calculate_bazi_full(
            solar_date="1990-05-15",
            solar_time="23:30",
            gender="male"
        )
        
        # 带时区转换的计算（使用东经150度，时差+2小时）
        final_date, final_time, conversion_info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="23:30",
            calendar_type="solar",
            longitude=150.0  # 东经150度
        )
        
        result2 = BaziService.calculate_bazi_full(
            solar_date=final_date,
            solar_time=final_time,
            gender="male"
        )
        
        pillars1 = result1.get('bazi', {}).get('bazi_pillars', {})
        pillars2 = result2.get('bazi', {}).get('bazi_pillars', {})
        
        # 验证年柱和月柱不变
        self.assertEqual(pillars1.get('year'), pillars2.get('year'), "年柱应该不变")
        self.assertEqual(pillars1.get('month'), pillars2.get('month'), "月柱应该不变")
        
        # 如果跨日，日柱和时柱都会变化
        if final_date != "1990-05-15":
            self.assertNotEqual(pillars1.get('day'), pillars2.get('day'), "日柱应该变化（跨日）")
            self.assertNotEqual(pillars1.get('hour'), pillars2.get('hour'), "时柱应该变化（跨日）")
    
    def test_lunar_conversion_affects_all_pillars(self):
        """测试：农历转换会影响所有柱（因为日期可能变化）"""
        # 农历 2024年正月初一 转换为阳历 2024-02-10
        
        # 原始计算（使用农历日期对应的阳历日期）
        result1 = BaziService.calculate_bazi_full(
            solar_date="2024-02-10",  # 农历2024年正月初一对应的阳历日期
            solar_time="12:00",
            gender="male"
        )
        
        # 使用农历输入
        final_date, final_time, conversion_info = BaziInputProcessor.process_input(
            solar_date="2024年正月初一",
            solar_time="12:00",
            calendar_type="lunar"
        )
        
        result2 = BaziService.calculate_bazi_full(
            solar_date=final_date,
            solar_time=final_time,
            gender="male"
        )
        
        pillars1 = result1.get('bazi', {}).get('bazi_pillars', {})
        pillars2 = result2.get('bazi', {}).get('bazi_pillars', {})
        
        # 农历转换后，所有柱应该一致（因为日期相同）
        self.assertEqual(pillars1.get('year'), pillars2.get('year'))
        self.assertEqual(pillars1.get('month'), pillars2.get('month'))
        self.assertEqual(pillars1.get('day'), pillars2.get('day'))
        self.assertEqual(pillars1.get('hour'), pillars2.get('hour'))
    
    def test_no_conversion_no_change(self):
        """测试：无转换时，结果应该完全一致"""
        # 不提供任何转换参数
        final_date, final_time, info = BaziInputProcessor.process_input(
            solar_date="1990-05-15",
            solar_time="14:30",
            calendar_type="solar"
        )
        
        self.assertEqual(final_date, "1990-05-15")
        self.assertEqual(final_time, "14:30")
        self.assertFalse(info.get('converted'))
        self.assertIsNone(info.get('timezone_info'))


if __name__ == '__main__':
    unittest.main()

