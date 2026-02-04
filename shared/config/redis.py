#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 配置模块

这是项目的统一 Redis 配置模块，位于 shared/config/ 目录下。
所有新代码应该使用此模块，server/config/redis_config.py 是兼容层。
"""

import redis
import logging
from redis.connection import ConnectionPool
from typing import Optional, Dict, Any
import os
import time

logger = logging.getLogger(__name__)

# Redis 连接配置（从环境变量读取）
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', '6379')),
    'db': int(os.getenv('REDIS_DB', '0')),
    'password': os.getenv('REDIS_PASSWORD', None),  # 如果设置了密码，从环境变量读取
    'max_connections': 200,  # 增加到200以支持更高并发（优化方案1.1）
    'socket_connect_timeout': 5,  # 连接超时 5秒（优化方案1.1）
    'socket_timeout': 5,  # 读写超时 5秒（优化方案1.1）
    'socket_keepalive': True,  # 启用 TCP keepalive（优化方案1.1）
    'socket_keepalive_options': {},  # keepalive 参数（优化方案1.1）
    'retry_on_timeout': True,  # 超时重试（优化方案1.1）
    'health_check_interval': 30,  # 健康检查间隔 30秒（优化方案1.1）
    'decode_responses': False  # 存储二进制数据，需要手动序列化/反序列化
}

# 全局 Redis 连接池
redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


def init_redis(host: str = 'localhost', port: int = 6379, db: int = 0, 
                password: Optional[str] = None, max_connections: int = 200,
                socket_connect_timeout: int = 5, socket_timeout: int = 5,
                socket_keepalive: bool = True, health_check_interval: int = 30):
    """
    初始化 Redis 连接（优化方案1.1）
    
    Args:
        host: Redis 主机地址
        port: Redis 端口
        db: 数据库编号
        password: 密码
        max_connections: 最大连接数（默认200）
        socket_connect_timeout: 连接超时（秒）
        socket_timeout: 读写超时（秒）
        socket_keepalive: 启用 TCP keepalive
        health_check_interval: 健康检查间隔（秒）
    """
    global redis_pool, redis_client, REDIS_CONFIG
    
    REDIS_CONFIG.update({
        'host': host,
        'port': port,
        'db': db,
        'password': password,
        'max_connections': max_connections,
        'socket_connect_timeout': socket_connect_timeout,
        'socket_timeout': socket_timeout,
        'socket_keepalive': socket_keepalive,
        'health_check_interval': health_check_interval
    })
    
    # 创建连接池（优化方案1.1：添加超时和健康检查配置）
    redis_pool = ConnectionPool(
        host=host,
        port=port,
        db=db,
        password=password,
        max_connections=max_connections,
        socket_connect_timeout=socket_connect_timeout,
        socket_timeout=socket_timeout,
        socket_keepalive=socket_keepalive,
        health_check_interval=health_check_interval,
        decode_responses=False
    )
    
    # 创建 Redis 客户端
    redis_client = redis.Redis(connection_pool=redis_pool)
    
    # 测试连接
    try:
        redis_client.ping()
        logger.info(f"✓ Redis 连接成功: {host}:{port} (连接池大小: {max_connections})")
        return True
    except Exception as e:
        logger.info(f"✗ Redis 连接失败: {e}")
        redis_client = None
        return False


def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端"""
    global redis_client
    
    if redis_client is None:
        # 自动初始化
        init_redis()
    
    return redis_client


def get_redis_pool() -> Optional[ConnectionPool]:
    """
    获取 Redis 连接池
    
    Returns:
        Redis 连接池实例，如果未初始化则自动初始化后返回
    """
    global redis_pool
    
    if redis_pool is None:
        # 自动初始化
        init_redis()
    
    return redis_pool


# 用于字符串响应的连接池（decode_responses=True）
_redis_pool_str: Optional[ConnectionPool] = None
_redis_client_str: Optional[redis.Redis] = None


def get_redis_client_str() -> Optional[redis.Redis]:
    """
    获取 Redis 客户端（字符串模式，自动解码响应）
    
    适用于需要直接操作字符串数据的场景（如 chat_service）。
    使用独立的连接池，与二进制模式客户端分开。
    
    Returns:
        Redis 客户端实例（decode_responses=True）
    """
    global _redis_pool_str, _redis_client_str
    
    if _redis_client_str is None:
        try:
            # 创建字符串模式的连接池
            _redis_pool_str = ConnectionPool(
                host=REDIS_CONFIG['host'],
                port=REDIS_CONFIG['port'],
                db=REDIS_CONFIG['db'],
                password=REDIS_CONFIG.get('password'),
                max_connections=50,  # 字符串模式连接数较少
                socket_connect_timeout=REDIS_CONFIG.get('socket_connect_timeout', 5),
                socket_timeout=REDIS_CONFIG.get('socket_timeout', 5),
                socket_keepalive=REDIS_CONFIG.get('socket_keepalive', True),
                decode_responses=True  # 自动解码字符串
            )
            _redis_client_str = redis.Redis(connection_pool=_redis_pool_str)
            _redis_client_str.ping()
            logger.info(f"✓ Redis 字符串模式客户端初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ Redis 字符串模式客户端初始化失败: {e}")
            _redis_client_str = None
    
    return _redis_client_str


def get_redis_client_with_retry(max_retries: int = 3, retry_delay: float = 1.0) -> Optional[redis.Redis]:
    """
    获取 Redis 客户端（带重试机制）（优化方案1.2）
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        
    Returns:
        Redis 客户端实例，如果失败则返回 None
    """
    for attempt in range(max_retries):
        try:
            client = get_redis_client()
            if client and client.ping():
                return client
        except Exception as e:
            if attempt < max_retries - 1:
                logger.info(f"⚠️ Redis 连接失败（尝试 {attempt + 1}/{max_retries}），{retry_delay}秒后重试: {e}")
                time.sleep(retry_delay)
            else:
                logger.info(f"✗ Redis 连接失败（已重试 {max_retries} 次）: {e}")
                return None
    return None


def check_redis_health() -> bool:
    """
    检查 Redis 健康状态（优化方案1.3）
    
    Returns:
        True 如果 Redis 健康，False 否则
    """
    try:
        client = get_redis_client()
        if client:
            return client.ping()
        return False
    except Exception as e:
        logger.info(f"⚠️ Redis 健康检查失败: {e}")
        return False


def get_redis_pool_stats() -> Dict[str, Any]:
    """
    获取连接池统计信息（优化方案1.5）
    
    Returns:
        连接池统计信息字典
    """
    global redis_pool, redis_client
    
    if redis_pool is None:
        return {"status": "not_initialized"}
    
    try:
        if redis_client is None:
            redis_client = get_redis_client()
        
        if redis_client is None:
            return {"status": "unavailable"}
        
        # 获取 Redis 信息
        info = redis_client.info()
        
        stats = {
            "status": "active",
            "max_connections": redis_pool.max_connections,
        }
        
        # 尝试获取连接使用情况（如果可用）
        if hasattr(redis_pool, '_in_use_connections'):
            stats['connections_in_use'] = len(redis_pool._in_use_connections)
        if hasattr(redis_pool, '_available_connections'):
            stats['available_connections'] = len(redis_pool._available_connections)
        if hasattr(redis_pool, '_created_connections'):
            stats['created_connections'] = redis_pool._created_connections
        
        # 添加 Redis 服务器信息
        stats.update({
            "connected_clients": info.get('connected_clients', 0),
            "used_memory": info.get('used_memory_human', 'N/A'),
            "used_memory_bytes": info.get('used_memory', 0),
            "keyspace": info.get('db0', {}),
            "total_commands_processed": info.get('total_commands_processed', 0),
            "instantaneous_ops_per_sec": info.get('instantaneous_ops_per_sec', 0)
        })
        
        return stats
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "max_connections": redis_pool.max_connections if redis_pool else 0
        }


def refresh_redis_connection() -> bool:
    """
    刷新 Redis 连接（热更新时使用）
    
    重新初始化 Redis 连接池和客户端。
    用于配置变更后刷新 Redis 连接。
    
    Returns:
        bool: 刷新是否成功
    """
    global redis_pool, redis_client
    
    try:
        # 关闭现有连接池
        if redis_pool is not None:
            try:
                redis_pool.disconnect()
            except Exception:
                pass
        
        # 重新初始化
        success = init_redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD', None),
            max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '200')),
            socket_connect_timeout=int(os.getenv('REDIS_CONNECT_TIMEOUT', '5')),
            socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            socket_keepalive=os.getenv('REDIS_KEEPALIVE', 'true').lower() == 'true',
            health_check_interval=int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30'))
        )
        
        if success:
            logger.info("✓ Redis 连接已刷新")
        return success
    except Exception as e:
        logger.warning(f"⚠️ Redis 连接刷新失败: {e}")
        return False


# 自动初始化（如果 Redis 可用）（优化方案1.1：使用新的默认参数）
try:
    # 从环境变量读取配置
    init_redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=int(os.getenv('REDIS_DB', '0')),
        password=os.getenv('REDIS_PASSWORD', None),
        max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '200')),  # 默认200
        socket_connect_timeout=int(os.getenv('REDIS_CONNECT_TIMEOUT', '5')),  # 默认5秒
        socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),  # 默认5秒
        socket_keepalive=os.getenv('REDIS_KEEPALIVE', 'true').lower() == 'true',  # 默认启用
        health_check_interval=int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30'))  # 默认30秒
    )
except Exception as e:
    logger.info(f"Redis 初始化失败（可选依赖）: {e}")
    redis_client = None








































