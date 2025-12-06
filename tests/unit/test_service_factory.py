#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务工厂单元测试
测试服务工厂创建服务实例
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.factories.service_factory import ServiceFactory
from server.services.bazi_service_v2 import BaziServiceV2


class TestServiceFactory:
    """服务工厂测试类"""
    
    def test_create_bazi_service(self):
        """测试创建八字服务"""
        service = ServiceFactory.create_bazi_service()
        
        assert service is not None
        assert isinstance(service, BaziServiceV2)
    
    @patch('server.factories.service_factory.get_config')
    def test_create_bazi_core_client_with_config(self, mock_get_config):
        """测试创建八字核心客户端（有配置）"""
        from server.config.app_config import ServiceConfig
        
        # Mock 配置
        mock_config = MagicMock()
        mock_config.services = ServiceConfig(
            bazi_core_url="http://localhost:9001"
        )
        mock_get_config.return_value = mock_config
        
        client = ServiceFactory.create_bazi_core_client()
        
        assert client is not None
        from server.interfaces.bazi_core_client_interface import IBaziCoreClient
        assert isinstance(client, IBaziCoreClient)
    
    @patch('server.factories.service_factory.get_config')
    def test_create_bazi_core_client_without_config(self, mock_get_config):
        """测试创建八字核心客户端（无配置）"""
        from server.config.app_config import ServiceConfig
        
        # Mock 配置（无 URL）
        mock_config = MagicMock()
        mock_config.services = ServiceConfig(bazi_core_url=None)
        mock_get_config.return_value = mock_config
        
        client = ServiceFactory.create_bazi_core_client()
        
        assert client is None

