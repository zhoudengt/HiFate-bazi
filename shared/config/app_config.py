#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一应用配置管理
所有配置统一从这里读取，避免配置分散
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str = 'utf8mb4'
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """从环境变量创建配置"""
        # ⚠️ 重要：根据环境自动选择默认配置
        # 本地开发：localhost:3306，密码: 123456
        # 生产环境：8.210.52.217:3306 (公网) / 172.18.121.222:3306 (内网)，密码: Yuanqizhan@163
        # 判断环境（本地开发 or 生产）
        env_value = os.getenv("ENV", os.getenv("APP_ENV", "local")).lower()
        is_local_dev = env_value in ["local", "development"]
        
        # 根据环境设置默认值
        # ⚠️ 安全规范：密码必须通过环境变量配置，不允许硬编码
        if is_local_dev:
            # 本地开发：使用本地MySQL
            default_host = 'localhost'
            default_password = os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD', ''))
        else:
            # 生产环境：使用生产MySQL
            default_host = '8.210.52.217'  # 生产Node1公网IP
            default_password = os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD', ''))
        
        return cls(
            host=os.getenv('MYSQL_HOST', default_host),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD', default_password)),
            database=os.getenv('MYSQL_DATABASE', 'hifate_bazi'),
            charset='utf8mb4'
        )


@dataclass
class RedisConfig:
    """Redis 配置"""
    host: str
    port: int
    db: int
    password: Optional[str]
    max_connections: int = 100
    decode_responses: bool = False
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        """从环境变量创建配置"""
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
            max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '100')),
            decode_responses=os.getenv('REDIS_DECODE_RESPONSES', 'False').lower() == 'true'
        )


@dataclass
class ServiceConfig:
    """微服务配置"""
    bazi_core_url: Optional[str] = None
    bazi_rule_url: Optional[str] = None
    bazi_fortune_url: Optional[str] = None
    bazi_core_strict: bool = False
    bazi_fortune_strict: bool = False
    
    @classmethod
    def from_env(cls) -> 'ServiceConfig':
        """从环境变量创建配置"""
        return cls(
            bazi_core_url=os.getenv('BAZI_CORE_SERVICE_URL'),
            bazi_rule_url=os.getenv('BAZI_RULE_SERVICE_URL'),
            bazi_fortune_url=os.getenv('BAZI_FORTUNE_SERVICE_URL'),
            bazi_core_strict=os.getenv('BAZI_CORE_SERVICE_STRICT', '0') == '1',
            bazi_fortune_strict=os.getenv('BAZI_FORTUNE_SERVICE_STRICT', '0') == '1'
        )


@dataclass
class AppConfig:
    """应用配置"""
    env: str = 'development'
    debug: bool = False
    secret_key: str = 'dev-secret-change-me'
    log_level: str = 'INFO'
    
    # 子配置
    database: DatabaseConfig = None
    redis: RedisConfig = None
    services: ServiceConfig = None
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """从环境变量创建完整配置"""
        config = cls(
            env=os.getenv('APP_ENV', 'development'),
            debug=os.getenv('DEBUG', 'False').lower() == 'true',
            secret_key=os.getenv('SECRET_KEY', 'dev-secret-change-me'),
            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )
        
        # 加载子配置
        config.database = DatabaseConfig.from_env()
        config.redis = RedisConfig.from_env()
        config.services = ServiceConfig.from_env()
        
        return config


# 全局配置实例（单例模式）
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置实例（单例）"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def reload_config():
    """重新加载配置（用于热更新）"""
    global _config
    _config = AppConfig.from_env()
    return _config

