#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 配置模块
"""

import redis
from redis.connection import ConnectionPool
from typing import Optional
import os

# Redis 连接配置（从环境变量读取）
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', '6379')),
    'db': int(os.getenv('REDIS_DB', '0')),
    'password': os.getenv('REDIS_PASSWORD', None),  # 如果设置了密码，从环境变量读取
    'max_connections': 100,  # 增加到100以支持更高并发（优化方案1）
    'decode_responses': False  # 存储二进制数据，需要手动序列化/反序列化
}

# 全局 Redis 连接池
redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


def init_redis(host: str = 'localhost', port: int = 6379, db: int = 0, 
                password: Optional[str] = None, max_connections: int = 100):
    """
    初始化 Redis 连接
    
    Args:
        host: Redis 主机地址
        port: Redis 端口
        db: 数据库编号
        password: 密码
        max_connections: 最大连接数
    """
    global redis_pool, redis_client, REDIS_CONFIG
    
    REDIS_CONFIG.update({
        'host': host,
        'port': port,
        'db': db,
        'password': password,
        'max_connections': max_connections
    })
    
    # 创建连接池
    redis_pool = ConnectionPool(
        host=host,
        port=port,
        db=db,
        password=password,
        max_connections=max_connections,
        decode_responses=False
    )
    
    # 创建 Redis 客户端
    redis_client = redis.Redis(connection_pool=redis_pool)
    
    # 测试连接
    try:
        redis_client.ping()
        print(f"✓ Redis 连接成功: {host}:{port}")
        return True
    except Exception as e:
        print(f"✗ Redis 连接失败: {e}")
        redis_client = None
        return False


def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端"""
    global redis_client
    
    if redis_client is None:
        # 自动初始化
        init_redis()
    
    return redis_client


# 自动初始化（如果 Redis 可用）
try:
    # 从环境变量读取配置
    init_redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=int(os.getenv('REDIS_DB', '0')),
        password=os.getenv('REDIS_PASSWORD', None),
        max_connections=100
    )
except Exception as e:
    print(f"Redis 初始化失败（可选依赖）: {e}")
    redis_client = None








































