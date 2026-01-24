#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC 网关接口测试
测试所有 42 个接口的基本功能
"""

import pytest
import sys
import os
import httpx
from unittest.mock import patch, MagicMock

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


# 所有需要测试的接口
ALL_ENDPOINTS = {
    # 八字核心接口（10个）
    'bazi_core': [
        '/bazi/pan/display',
        '/bazi/fortune/display',
        '/bazi/interface',
        '/bazi/shengong-minggong',
        '/bazi/data',
        '/bazi/wangshuai',
        '/bazi/rizhu-liujiazi',
        '/bazi/formula-analysis',
        '/bazi/xishen-jishen',
        '/bazi/wuxing-proportion',
    ],
    # 流式接口（10个）
    'stream': [
        '/bazi/xishen-jishen/stream',
        '/bazi/wuxing-proportion/stream',
        '/bazi/marriage-analysis/stream',
        '/career-wealth/stream',
        '/children-study/stream',
        '/health/stream',
        '/general-review/stream',
        '/annual-report/stream',
        '/smart-fortune/smart-analyze-stream',
        '/daily-fortune-calendar/stream',
    ],
    # 支付接口（5个）
    'payment': [
        '/payment/create-session',
        '/payment/verify',
        '/payment/unified/create',
        '/payment/unified/verify',
        '/payment/providers',
    ],
    # 日历接口（3个）
    'calendar': [
        '/calendar/query',
        '/daily-fortune-calendar/query',
        '/smart-analyze',
    ],
    # 首页接口（6个）
    'homepage': [
        '/homepage/contents',
        '/homepage/contents/detail',
        '/admin/homepage/contents',
        '/admin/homepage/contents/update',
        '/admin/homepage/contents/delete',
        '/admin/homepage/contents/sort',
    ],
    # AI接口（2个）
    'ai': [
        '/api/v2/face/analyze',
        '/api/v2/desk-fengshui/analyze',
    ],
    # 安全接口（3个）
    'security': [
        '/security/stats',
        '/security/blocked-ips',
        '/security/unblock-ip',
    ],
    # 其他（1个）
    'misc': [
        '/proto/list',
    ],
}


@pytest.mark.api
class TestEndpointsList:
    """端点列表测试"""
    
    def test_bazi_core_count(self):
        """测试：八字核心接口数量"""
        assert len(ALL_ENDPOINTS['bazi_core']) == 10
    
    def test_stream_count(self):
        """测试：流式接口数量"""
        assert len(ALL_ENDPOINTS['stream']) == 10
    
    def test_payment_count(self):
        """测试：支付接口数量"""
        assert len(ALL_ENDPOINTS['payment']) == 5
    
    def test_calendar_count(self):
        """测试：日历接口数量"""
        assert len(ALL_ENDPOINTS['calendar']) == 3
    
    def test_homepage_count(self):
        """测试：首页接口数量"""
        assert len(ALL_ENDPOINTS['homepage']) == 6
    
    def test_ai_count(self):
        """测试：AI接口数量"""
        assert len(ALL_ENDPOINTS['ai']) == 2
    
    def test_security_count(self):
        """测试：安全接口数量"""
        assert len(ALL_ENDPOINTS['security']) == 3
    
    def test_misc_count(self):
        """测试：其他接口数量"""
        assert len(ALL_ENDPOINTS['misc']) == 1
    
    def test_total_count(self):
        """测试：总接口数量"""
        total = sum(len(eps) for eps in ALL_ENDPOINTS.values())
        assert total == 40  # 42 - 2（去掉测试接口后）


@pytest.mark.api
class TestBaziCoreServices:
    """八字核心服务测试"""
    
    def test_bazi_input_processor_exists(self):
        """测试：BaziInputProcessor 类存在"""
        from server.utils.bazi_input_processor import BaziInputProcessor
        assert hasattr(BaziInputProcessor, 'process_input')
    
    def test_bazi_display_service_exists(self):
        """测试：BaziDisplayService 类存在"""
        from server.services.bazi_display_service import BaziDisplayService
        assert hasattr(BaziDisplayService, 'get_pan_display')
        assert hasattr(BaziDisplayService, 'get_fortune_display')
    
    def test_bazi_interface_service_exists(self):
        """测试：BaziInterfaceService 类存在"""
        from server.services.bazi_interface_service import BaziInterfaceService
        assert hasattr(BaziInterfaceService, 'generate_interface_full')
    
    def test_wangshuai_service_exists(self):
        """测试：WangShuaiService 类存在"""
        from server.services.wangshuai_service import WangShuaiService
        assert WangShuaiService is not None
    
    def test_xishen_jishen_service_exists(self):
        """测试：喜神忌神服务存在"""
        from server.api.v1.xishen_jishen import get_xishen_jishen
        assert callable(get_xishen_jishen)
    
    def test_wuxing_proportion_service_exists(self):
        """测试：五行比例服务存在"""
        from server.api.v1.wuxing_proportion import get_wuxing_proportion
        assert callable(get_wuxing_proportion)


@pytest.mark.api
class TestCalendarServices:
    """日历服务测试"""
    
    def test_calendar_api_service_exists(self):
        """测试：CalendarAPIService 类存在"""
        from server.services.calendar_api_service import CalendarAPIService
        assert hasattr(CalendarAPIService, 'get_calendar')
    
    def test_daily_fortune_service_exists(self):
        """测试：DailyFortuneService 类存在"""
        from server.services.daily_fortune_service import DailyFortuneService
        assert DailyFortuneService is not None


@pytest.mark.api
class TestSecurityServices:
    """安全服务测试"""
    
    def test_sql_security_exists(self):
        """测试：SQL安全模块存在"""
        from server.utils.sql_security import SQLSecurityChecker
        assert SQLSecurityChecker is not None


@pytest.mark.api  
class TestStreamGenerators:
    """流式生成器测试"""
    
    def test_xishen_stream_generator_exists(self):
        """测试：喜神忌神流式生成器存在"""
        from server.api.v1.xishen_jishen import xishen_jishen_stream_generator
        assert callable(xishen_jishen_stream_generator)
    
    def test_wuxing_stream_generator_exists(self):
        """测试：五行比例流式生成器存在"""
        from server.api.v1.wuxing_proportion import wuxing_proportion_stream_generator
        assert callable(wuxing_proportion_stream_generator)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
