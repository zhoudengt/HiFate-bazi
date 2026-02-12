#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一环境配置管理

提供统一的环境判断和配置管理，避免配置分散
"""

import os
from typing import Literal, Optional
from enum import Enum

# 环境类型定义
Environment = Literal["local", "development", "staging", "production"]


class EnvironmentType(Enum):
    """环境类型枚举"""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvConfig:
    """
    统一环境配置管理器
    
    提供统一的环境判断和配置读取接口
    """
    
    _instance: 'EnvConfig' = None
    _env: Optional[Environment] = None
    _is_local_dev: Optional[bool] = None
    _is_production: Optional[bool] = None
    
    def __init__(self):
        """初始化环境配置"""
        self._detect_environment()
    
    @classmethod
    def get_instance(cls) -> 'EnvConfig':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    # 生产环境必需的环境变量列表
    PRODUCTION_REQUIRED_VARS = [
        "MYSQL_HOST",
        "MYSQL_PASSWORD",
        "REDIS_PASSWORD",
        "SECRET_KEY",
    ]

    def _detect_environment(self):
        """检测当前环境"""
        # 优先读取 ENV，其次 APP_ENV，默认 local
        env_value = os.getenv("ENV", os.getenv("APP_ENV", "local")).lower()
        
        # 标准化环境值
        if env_value in ["local", "dev", "development"]:
            self._env = "local"
            self._is_local_dev = True
            self._is_production = False
        elif env_value in ["staging", "stage"]:
            self._env = "staging"
            self._is_local_dev = False
            self._is_production = False
        elif env_value in ["prod", "production"]:
            self._env = "production"
            self._is_local_dev = False
            self._is_production = True
        else:
            # 未知环境，默认为本地开发
            self._env = "local"
            self._is_local_dev = True
            self._is_production = False
        
        # 生产环境启动时校验必需变量
        if self._is_production:
            self._validate_production_vars()
    
    def _validate_production_vars(self):
        """生产环境启动时校验必需环境变量"""
        import logging
        _logger = logging.getLogger(__name__)
        missing = [var for var in self.PRODUCTION_REQUIRED_VARS if not os.getenv(var)]
        if missing:
            _logger.error(
                f"❌ 生产环境缺少必需环境变量: {', '.join(missing)}。"
                f"请在 .env 文件或系统环境变量中配置。"
            )
            # 不抛异常，让服务尝试启动（在实际连接时会失败并给出具体错误）
    
    @property
    def env(self) -> Environment:
        """获取当前环境"""
        return self._env
    
    @property
    def is_local_dev(self) -> bool:
        """是否为本地开发环境"""
        return self._is_local_dev
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self._is_production
    
    @property
    def is_staging(self) -> bool:
        """是否为预发布环境"""
        return self._env == "staging"
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境（包括本地和开发）"""
        return self._is_local_dev
    
    def get_config(self, key: str, default: str = None, required: bool = False) -> Optional[str]:
        """
        获取配置值（从环境变量）
        
        Args:
            key: 配置键
            default: 默认值
            required: 是否必需（如果为True且不存在则抛出异常）
        
        Returns:
            配置值
        
        Raises:
            ValueError: 如果 required=True 且配置不存在
        """
        value = os.getenv(key, default)
        if required and value is None:
            raise ValueError(f"必需的环境变量 {key} 未设置")
        return value
    
    def get_bool_config(self, key: str, default: bool = False) -> bool:
        """
        获取布尔类型配置
        
        Args:
            key: 配置键
            default: 默认值
        
        Returns:
            布尔值
        """
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")
    
    def get_int_config(self, key: str, default: int = 0) -> int:
        """
        获取整数类型配置
        
        Args:
            key: 配置键
            default: 默认值
        
        Returns:
            整数值
        """
        value = os.getenv(key, str(default))
        try:
            return int(value)
        except ValueError:
            return default


# 全局单例实例
_env_config: Optional[EnvConfig] = None


def get_env_config() -> EnvConfig:
    """
    获取环境配置实例（全局单例）
    
    Returns:
        EnvConfig: 环境配置实例
    """
    global _env_config
    if _env_config is None:
        _env_config = EnvConfig()
    return _env_config


# 便捷函数
def is_local_dev() -> bool:
    """是否为本地开发环境（便捷函数）"""
    return get_env_config().is_local_dev


def is_production() -> bool:
    """是否为生产环境（便捷函数）"""
    return get_env_config().is_production


def get_env() -> Environment:
    """获取当前环境（便捷函数）"""
    return get_env_config().env
