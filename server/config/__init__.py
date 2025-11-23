# -*- coding: utf-8 -*-
"""
配置模块
"""

# 可选导入，避免依赖缺失导致整个模块无法导入
try:
    from .redis_config import redis_client, redis_pool, REDIS_CONFIG, get_redis_client
    REDIS_AVAILABLE = True
except ImportError:
    redis_client = None
    redis_pool = None
    REDIS_CONFIG = {}
    get_redis_client = None
    REDIS_AVAILABLE = False

try:
    from .mysql_config import mysql_config, get_mysql_connection
    MYSQL_AVAILABLE = True
except ImportError:
    mysql_config = {}
    get_mysql_connection = None
    MYSQL_AVAILABLE = False

__all__ = ['redis_client', 'redis_pool', 'REDIS_CONFIG', 'get_redis_client', 
           'mysql_config', 'get_mysql_connection', 'REDIS_AVAILABLE', 'MYSQL_AVAILABLE']

