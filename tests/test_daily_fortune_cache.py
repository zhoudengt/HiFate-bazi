#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日运势Redis缓存测试
测试缓存命中、未命中、失效、降级等功能
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import date, datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.services.daily_fortune_calendar_service import DailyFortuneCalendarService
from server.services.daily_fortune_service import DailyFortuneService


class TestDailyFortuneCache(unittest.TestCase):
    """每日运势缓存测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_date = "2025-01-15"
        self.user_solar_date = "1990-05-15"
        self.user_solar_time = "12:00"
        self.user_gender = "male"
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        key = DailyFortuneCalendarService._generate_cache_key(
            self.test_date,
            self.user_solar_date,
            self.user_solar_time,
            self.user_gender
        )
        
        # 验证键格式
        self.assertTrue(key.startswith('daily_fortune:calendar:'))
        self.assertIn(self.test_date, key)
        self.assertIn(self.user_solar_date, key)
        self.assertIn(self.user_solar_time, key)
        self.assertIn(self.user_gender, key)
    
    def test_cache_miss_then_hit(self):
        """测试缓存未命中后命中"""
        # 清理缓存
        DailyFortuneCalendarService.invalidate_cache_for_date(self.test_date)
        
        # 第一次调用（缓存未命中，应查询数据库）
        with patch('server.services.daily_fortune_calendar_service.get_multi_cache') as mock_cache:
            # 模拟缓存未命中
            mock_cache_instance = MagicMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance
            
            # 模拟数据库查询
            with patch.object(DailyFortuneCalendarService, '_query_from_database') as mock_query:
                mock_query.return_value = {
                    'success': True,
                    'solar_date': '2025年1月15日',
                    'jiazi_fortune': '测试运势'
                }
                
                result1 = DailyFortuneCalendarService.get_daily_fortune_calendar(
                    date_str=self.test_date,
                    user_solar_date=self.user_solar_date,
                    user_solar_time=self.user_solar_time,
                    user_gender=self.user_gender
                )
                
                # 验证第一次调用查询了数据库
                mock_query.assert_called_once()
                self.assertTrue(result1.get('success'))
        
        # 第二次调用（缓存命中，不应查询数据库）
        with patch('server.services.daily_fortune_calendar_service.get_multi_cache') as mock_cache:
            # 模拟缓存命中
            cached_result = {
                'success': True,
                'solar_date': '2025年1月15日',
                'jiazi_fortune': '测试运势'
            }
            mock_cache_instance = MagicMock()
            mock_cache_instance.get.return_value = cached_result
            mock_cache.return_value = mock_cache_instance
            
            # 模拟数据库查询（不应被调用）
            with patch.object(DailyFortuneCalendarService, '_query_from_database') as mock_query:
                result2 = DailyFortuneCalendarService.get_daily_fortune_calendar(
                    date_str=self.test_date,
                    user_solar_date=self.user_solar_date,
                    user_solar_time=self.user_solar_time,
                    user_gender=self.user_gender
                )
                
                # 验证第二次调用未查询数据库（缓存命中）
                mock_query.assert_not_called()
                self.assertEqual(result2, cached_result)
    
    def test_cache_invalidation(self):
        """测试缓存失效"""
        with patch('server.config.redis_config.get_redis_client') as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis_client.scan.return_value = (0, [b'daily_fortune:calendar:2025-01-15:test'])
            mock_redis_client.delete.return_value = 1
            mock_redis.return_value = mock_redis_client
            
            # 清理缓存
            DailyFortuneCalendarService.invalidate_cache_for_date(self.test_date)
            
            # 验证调用了Redis删除
            mock_redis_client.delete.assert_called()
            mock_redis_client.publish.assert_called_once()
    
    def test_redis_unavailable_fallback(self):
        """测试Redis不可用时的降级"""
        # 模拟Redis不可用
        with patch('server.services.daily_fortune_calendar_service.get_multi_cache') as mock_cache:
            mock_cache.side_effect = Exception("Redis不可用")
            
            # 模拟数据库查询
            with patch.object(DailyFortuneCalendarService, '_query_from_database') as mock_query:
                mock_query.return_value = {
                    'success': True,
                    'solar_date': '2025年1月15日'
                }
                
                result = DailyFortuneCalendarService.get_daily_fortune_calendar(
                    date_str=self.test_date
                )
                
                # 验证降级到数据库查询
                mock_query.assert_called_once()
                self.assertTrue(result.get('success'))
    
    def test_daily_fortune_service_cache(self):
        """测试每日运势服务缓存"""
        # 清理缓存
        DailyFortuneService.invalidate_cache_for_date(self.test_date)
        
        # 第一次调用（缓存未命中）
        with patch('server.services.daily_fortune_service.get_multi_cache') as mock_cache:
            mock_cache_instance = MagicMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance
            
            # 模拟数据库查询
            with patch.object(DailyFortuneService, '_calculate_daily_fortune_from_database') as mock_query:
                mock_query.return_value = {
                    'success': True,
                    'target_date': self.test_date,
                    'fortune': {'text': '测试运势'}
                }
                
                result1 = DailyFortuneService.calculate_daily_fortune(
                    solar_date=self.user_solar_date,
                    solar_time=self.user_solar_time,
                    gender=self.user_gender,
                    target_date=self.test_date
                )
                
                # 验证第一次调用查询了数据库
                mock_query.assert_called_once()
                self.assertTrue(result1.get('success'))
        
        # 第二次调用（缓存命中）
        with patch('server.services.daily_fortune_service.get_multi_cache') as mock_cache:
            cached_result = {
                'success': True,
                'target_date': self.test_date,
                'fortune': {'text': '测试运势'}
            }
            mock_cache_instance = MagicMock()
            mock_cache_instance.get.return_value = cached_result
            mock_cache.return_value = mock_cache_instance
            
            with patch.object(DailyFortuneService, '_calculate_daily_fortune_from_database') as mock_query:
                result2 = DailyFortuneService.calculate_daily_fortune(
                    solar_date=self.user_solar_date,
                    solar_time=self.user_solar_time,
                    gender=self.user_gender,
                    target_date=self.test_date
                )
                
                # 验证第二次调用未查询数据库
                mock_query.assert_not_called()
                self.assertEqual(result2, cached_result)


if __name__ == '__main__':
    unittest.main()

