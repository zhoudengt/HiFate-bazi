#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字服务 V2 单元测试
测试依赖注入和接口抽象
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.services.bazi_service_v2 import BaziServiceV2
from server.interfaces.bazi_core_client_interface import IBaziCoreClient
from server.interfaces.bazi_calculator_interface import IBaziCalculator


class TestBaziServiceV2:
    """八字服务 V2 测试类"""
    
    def test_calculate_bazi_with_mock_client(self):
        """测试使用 Mock 客户端（依赖注入的优势）"""
        # 创建 Mock 客户端
        mock_client = Mock(spec=IBaziCoreClient)
        mock_client.calculate_bazi.return_value = {
            'bazi_pillars': {
                'year': {'stem': '庚', 'branch': '午'},
                'month': {'stem': '己', 'branch': '丑'},
                'day': {'stem': '甲', 'branch': '子'},
                'hour': {'stem': '庚', 'branch': '午'}
            },
            'basic_info': {
                'solar_date': '1990-01-15',
                'solar_time': '12:00',
                'gender': 'male'
            },
            'details': {},
            'ten_gods_stats': {},
            'elements': {},
            'element_counts': {},
            'relationships': {}
        }
        
        # 创建服务实例（注入 Mock 客户端）
        service = BaziServiceV2(core_client=mock_client)
        
        # 调用方法
        result = service.calculate_bazi_full("1990-01-15", "12:00", "male")
        
        # 验证
        assert result is not None
        assert "bazi" in result
        assert "rizhu" in result
        
        # 验证 Mock 被调用
        mock_client.calculate_bazi.assert_called_once_with("1990-01-15", "12:00", "male")
    
    def test_calculate_bazi_without_client(self):
        """测试不使用远程客户端（本地计算）"""
        # 创建服务实例（不注入客户端）
        service = BaziServiceV2(core_client=None)
        
        # 调用方法
        result = service.calculate_bazi_full("1990-01-15", "12:00", "male")
        
        # 验证
        assert result is not None
        assert "bazi" in result
        assert "rizhu" in result
        # 验证日柱天干存在（不验证具体值，因为可能因计算库版本而异）
        assert "stem" in result["bazi"]["bazi_pillars"]["day"]
        assert result["bazi"]["bazi_pillars"]["day"]["stem"] in ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    
    def test_calculate_bazi_with_factory(self):
        """测试使用自定义计算器工厂"""
        # 创建 Mock 计算器
        mock_calculator = Mock(spec=IBaziCalculator)
        mock_calculator.calculate.return_value = {
            'bazi_pillars': {
                'year': {'stem': '庚', 'branch': '午'},
                'month': {'stem': '己', 'branch': '丑'},
                'day': {'stem': '甲', 'branch': '子'},
                'hour': {'stem': '庚', 'branch': '午'}
            },
            'basic_info': {
                'solar_date': '1990-01-15',
                'solar_time': '12:00',
                'gender': 'male'
            },
            'details': {},
            'ten_gods_stats': {},
            'elements': {},
            'element_counts': {},
            'relationships': {}
        }
        
        # 自定义工厂函数
        def custom_factory(solar_date, solar_time, gender):
            return mock_calculator
        
        # 创建服务实例
        service = BaziServiceV2(core_client=None, calculator_factory=custom_factory)
        
        # 调用方法
        result = service.calculate_bazi_full("1990-01-15", "12:00", "male")
        
        # 验证
        assert result is not None
        mock_calculator.calculate.assert_called_once()
    
    def test_create_default(self):
        """测试创建默认服务实例"""
        service = BaziServiceV2.create_default()
        
        assert service is not None
        assert isinstance(service, BaziServiceV2)
        
        # 测试可以正常调用
        result = service.calculate_bazi_full("1990-01-15", "12:00", "male")
        assert result is not None

