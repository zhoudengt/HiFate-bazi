#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一应用配置管理（shared 模块）
委托给 server.config.app_config，保持单一配置源。
此文件保留是为了向后兼容已有的 import 路径。
"""

# 直接复用 server 层的配置，避免两套配置不一致
try:
    from server.config.app_config import (
        AppConfig,
        DatabaseConfig,
        RedisConfig,
        ServiceConfig,
        get_config,
        reload_config,
    )
except ImportError:
    # 当 server.config 不可用时（如微服务独立运行），提供最小可用实现
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
            env_value = os.getenv("ENV", os.getenv("APP_ENV", "local")).lower()
            is_local = env_value in ["local", "dev", "development"]
            default_host = 'localhost' if is_local else os.getenv('MYSQL_HOST', '')
            return cls(
                host=os.getenv('MYSQL_HOST', default_host),
                port=int(os.getenv('MYSQL_PORT', '3306')),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD', '')),
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
            return cls(
                bazi_core_url=os.getenv('BAZI_CORE_SERVICE_URL'),
                bazi_rule_url=os.getenv('BAZI_RULE_SERVICE_URL'),
                bazi_fortune_url=os.getenv('BAZI_FORTUNE_SERVICE_URL'),
                bazi_core_strict=os.getenv('BAZI_CORE_SERVICE_STRICT', '0') in ('1', 'true', 'yes'),
                bazi_fortune_strict=os.getenv('BAZI_FORTUNE_SERVICE_STRICT', '0') in ('1', 'true', 'yes')
            )

    @dataclass
    class AppConfig:
        """应用配置"""
        env: str = 'development'
        debug: bool = False
        secret_key: str = 'dev-secret-change-me'
        log_level: str = 'INFO'
        database: DatabaseConfig = None
        redis: RedisConfig = None
        services: ServiceConfig = None

        @classmethod
        def from_env(cls) -> 'AppConfig':
            env_value = os.getenv("ENV", os.getenv("APP_ENV", "local")).lower()
            if env_value in ("local", "dev", "development"):
                env_value = "local"
            elif env_value in ("prod", "production"):
                env_value = "production"
            config = cls(
                env=env_value,
                debug=os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes'),
                secret_key=os.getenv('SECRET_KEY', 'dev-secret-change-me'),
                log_level=os.getenv('LOG_LEVEL', 'INFO')
            )
            config.database = DatabaseConfig.from_env()
            config.redis = RedisConfig.from_env()
            config.services = ServiceConfig.from_env()
            return config

    _config: Optional[AppConfig] = None

    def get_config() -> AppConfig:
        global _config
        if _config is None:
            _config = AppConfig.from_env()
        return _config

    def reload_config():
        global _config
        _config = AppConfig.from_env()
        return _config

