#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
架构改进集成测试
验证依赖注入、接口抽象、统一配置的效果
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.app_config import get_config, reload_config, AppConfig
from server.services.bazi_service_v2 import BaziServiceV2
from server.factories.service_factory import ServiceFactory
from server.interfaces.bazi_core_client_interface import IBaziCoreClient


class TestArchitectureImprovements:
    """架构改进测试类"""
    
    def test_unified_config(self):
        """测试统一配置管理"""
        config = get_config()
        
        # 验证配置结构
        assert hasattr(config, 'database')
        assert hasattr(config, 'redis')
        assert hasattr(config, 'services')
        
        # 验证配置可以访问
        assert config.database.host is not None
        assert config.redis.host is not None
    
    def test_interface_abstraction(self):
        """测试接口抽象层"""
        # 创建 Mock 实现接口
        mock_client = Mock(spec=IBaziCoreClient)
        mock_client.calculate_bazi.return_value = {
            'bazi_pillars': {
                'year': {'stem': '庚', 'branch': '午'},
                'month': {'stem': '己', 'branch': '丑'},
                'day': {'stem': '甲', 'branch': '子'},
                'hour': {'stem': '庚', 'branch': '午'}
            },
            'basic_info': {'solar_date': '1990-01-15', 'solar_time': '12:00', 'gender': 'male'},
            'details': {},
            'ten_gods_stats': {},
            'elements': {},
            'element_counts': {},
            'relationships': {}
        }
        
        # 验证 Mock 实现了接口
        assert isinstance(mock_client, IBaziCoreClient)
        
        # 使用接口调用
        result = mock_client.calculate_bazi("1990-01-15", "12:00", "male")
        assert result is not None
    
    def test_dependency_injection(self):
        """测试依赖注入"""
        # 创建 Mock 客户端
        mock_client = Mock(spec=IBaziCoreClient)
        mock_client.calculate_bazi.return_value = {
            'bazi_pillars': {
                'year': {'stem': '庚', 'branch': '午'},
                'month': {'stem': '己', 'branch': '丑'},
                'day': {'stem': '甲', 'branch': '子'},
                'hour': {'stem': '庚', 'branch': '午'}
            },
            'basic_info': {'solar_date': '1990-01-15', 'solar_time': '12:00', 'gender': 'male'},
            'details': {},
            'ten_gods_stats': {},
            'elements': {},
            'element_counts': {},
            'relationships': {}
        }
        
        # 通过依赖注入创建服务
        service = BaziServiceV2(core_client=mock_client)
        
        # 调用服务
        result = service.calculate_bazi_full("1990-01-15", "12:00", "male")
        
        # 验证结果
        assert result is not None
        assert "bazi" in result
        
        # 验证依赖被正确注入和使用
        mock_client.calculate_bazi.assert_called_once()
    
    def test_service_factory(self):
        """测试服务工厂"""
        # 使用工厂创建服务
        service = ServiceFactory.create_bazi_service()
        
        assert service is not None
        assert isinstance(service, BaziServiceV2)
        
        # 验证服务可以正常工作
        result = service.calculate_bazi_full("1990-01-15", "12:00", "male")
        assert result is not None
    
    def test_config_reload(self):
        """测试配置热重载"""
        config1 = get_config()
        
        # 修改环境变量
        with patch.dict(os.environ, {'APP_ENV': 'test_reload'}):
            config2 = reload_config()
            
            assert config2.env == 'test_reload'
            # 验证是新实例
            assert config2 is not config1
    
    def test_low_coupling(self):
        """测试低耦合度（可以轻松替换实现）"""
        # 创建两个不同的 Mock 实现
        mock_client1 = Mock(spec=IBaziCoreClient)
        mock_client2 = Mock(spec=IBaziCoreClient)
        
        # 创建两个服务实例，使用不同的客户端
        service1 = BaziServiceV2(core_client=mock_client1)
        service2 = BaziServiceV2(core_client=mock_client2)
        
        # 验证它们可以独立工作
        assert service1 is not service2
        assert service1._core_client is mock_client1
        assert service2._core_client is mock_client2

