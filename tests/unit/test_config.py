#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理单元测试
测试统一配置管理
"""

import pytest
import os
import sys
from unittest.mock import patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.app_config import (
    AppConfig,
    DatabaseConfig,
    RedisConfig,
    ServiceConfig,
    get_config,
    reload_config
)


class TestConfig:
    """配置测试类"""
    
    def test_database_config_from_env(self):
        """测试从环境变量创建数据库配置"""
        with patch.dict(os.environ, {
            'MYSQL_HOST': 'test_host',
            'MYSQL_PORT': '3307',
            'MYSQL_USER': 'test_user',
            'MYSQL_PASSWORD': 'test_pass',
            'MYSQL_DATABASE': 'test_db'
        }):
            config = DatabaseConfig.from_env()
            
            assert config.host == 'test_host'
            assert config.port == 3307
            assert config.user == 'test_user'
            assert config.password == 'test_pass'
            assert config.database == 'test_db'
    
    def test_database_config_defaults(self):
        """测试数据库配置默认值"""
        with patch.dict(os.environ, {}, clear=True):
            config = DatabaseConfig.from_env()
            
            assert config.host == 'localhost'
            assert config.port == 3306
            assert config.database == 'hifate_bazi'
    
    def test_redis_config_from_env(self):
        """测试从环境变量创建 Redis 配置"""
        with patch.dict(os.environ, {
            'REDIS_HOST': 'redis_host',
            'REDIS_PORT': '6380',
            'REDIS_DB': '1',
            'REDIS_PASSWORD': 'redis_pass'
        }):
            config = RedisConfig.from_env()
            
            assert config.host == 'redis_host'
            assert config.port == 6380
            assert config.db == 1
            assert config.password == 'redis_pass'
    
    def test_service_config_from_env(self):
        """测试从环境变量创建服务配置"""
        with patch.dict(os.environ, {
            'BAZI_CORE_SERVICE_URL': 'http://localhost:9001',
            'BAZI_RULE_SERVICE_URL': 'http://localhost:9004',
            'BAZI_CORE_SERVICE_STRICT': '1'
        }):
            config = ServiceConfig.from_env()
            
            assert config.bazi_core_url == 'http://localhost:9001'
            assert config.bazi_rule_url == 'http://localhost:9004'
            assert config.bazi_core_strict is True
    
    def test_app_config_from_env(self):
        """测试从环境变量创建完整应用配置"""
        with patch.dict(os.environ, {
            'APP_ENV': 'production',
            'DEBUG': 'True',
            'SECRET_KEY': 'test_secret',
            'MYSQL_HOST': 'db_host',
            'REDIS_HOST': 'redis_host'
        }):
            config = AppConfig.from_env()
            
            assert config.env == 'production'
            assert config.debug is True
            assert config.secret_key == 'test_secret'
            assert config.database.host == 'db_host'
            assert config.redis.host == 'redis_host'
    
    def test_get_config_singleton(self):
        """测试配置单例模式"""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_reload_config(self):
        """测试重新加载配置"""
        config1 = get_config()
        
        with patch.dict(os.environ, {'APP_ENV': 'test'}):
            config2 = reload_config()
            
            assert config2.env == 'test'
            # 重新加载后应该是新实例
            assert config2 is not config1

