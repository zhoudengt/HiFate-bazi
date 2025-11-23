#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多级缓存系统 - 支持500万用户
架构：L1(内存) -> L2(Redis) -> L3(数据库/持久化)
"""

import json
import hashlib
import time
from typing import Any, Optional, Dict
from functools import lru_cache

# L1: 本地内存缓存（热点数据）
class L1MemoryCache:
    """L1缓存：本地内存，存储最热的数据"""
    
    def __init__(self, max_size: int = 50000, ttl: int = 300):
        """
        初始化 L1 缓存
        
        Args:
            max_size: 最大缓存条目数（默认5万）
            ttl: 缓存过期时间（秒），默认5分钟
        """
        self._cache = {}
        self._cache_times = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """从缓存获取结果"""
        if key not in self._cache:
            return None
        if time.time() - self._cache_times[key] > self.ttl:
            del self._cache[key]
            del self._cache_times[key]
            return None
        return self._cache[key]
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        if len(self._cache) >= self.max_size:
            oldest = min(self._cache_times.keys(), key=lambda k: self._cache_times[k])
            del self._cache[oldest]
            del self._cache_times[oldest]
        self._cache[key] = value
        self._cache_times[key] = time.time()
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_times.clear()
    
    def stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl
        }


# L2: Redis分布式缓存（推荐）
class L2RedisCache:
    """L2缓存：Redis分布式缓存，支持多服务器共享"""
    
    def __init__(self, redis_client=None, ttl: int = 3600):
        """
        初始化 L2 缓存
        
        Args:
            redis_client: Redis 客户端对象
            ttl: 缓存过期时间（秒），默认1小时
        """
        self.redis = redis_client
        self.ttl = ttl
        self._available = redis_client is not None
    
    def get(self, key: str) -> Optional[Any]:
        """从缓存获取结果"""
        if not self._available:
            return None
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            return None
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        if not self._available:
            return
        try:
            data = json.dumps(value, ensure_ascii=False)
            self.redis.setex(key, self.ttl, data)
        except Exception:
            pass
    
    def delete(self, key: str):
        """删除缓存"""
        if not self._available:
            return
        try:
            self.redis.delete(key)
        except Exception:
            pass
    
    def stats(self) -> dict:
        """获取缓存统计信息"""
        if not self._available:
            return {"status": "unavailable"}
        try:
            info = self.redis.info()
            return {
                "status": "available",
                "used_memory": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 0),
                "keyspace": info.get('db0', {})
            }
        except Exception:
            return {"status": "error"}


# 多级缓存管理器
class MultiLevelCache:
    """多级缓存管理器"""
    
    def __init__(self, 
                 l1_max_size: int = 50000,
                 l1_ttl: int = 300,
                 redis_client=None,
                 redis_ttl: int = 3600):
        """
        初始化多级缓存
        
        Args:
            l1_max_size: L1缓存最大条目数
            l1_ttl: L1缓存过期时间（秒）
            redis_client: Redis客户端
            redis_ttl: L2缓存过期时间（秒）
        """
        self.l1 = L1MemoryCache(max_size=l1_max_size, ttl=l1_ttl)
        self.l2 = L2RedisCache(redis_client=redis_client, ttl=redis_ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """
        多级缓存读取：L1 -> L2
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回None
        """
        # L1: 本地内存（最快）
        value = self.l1.get(key)
        if value is not None:
            return value
        
        # L2: Redis（较快）
        value = self.l2.get(key)
        if value is not None:
            # 回填L1
            self.l1.set(key, value)
            return value
        
        return None
    
    def set(self, key: str, value: Any):
        """
        多级缓存写入：同时写入L1和L2
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        self.l1.set(key, value)
        self.l2.set(key, value)
    
    def delete(self, key: str):
        """删除缓存（所有层级）"""
        self.l1.delete(key) if hasattr(self.l1, 'delete') else None
        self.l2.delete(key)
    
    def clear(self):
        """清空所有缓存"""
        self.l1.clear()
        # L2 清空需要特殊处理，这里不实现
    
    def _generate_key(self, solar_date: str, solar_time: str, gender: str, **kwargs) -> str:
        """生成缓存键"""
        cache_str = f"{solar_date}:{solar_time}:{gender}"
        if kwargs:
            cache_str += ":" + json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def get_bazi(self, solar_date: str, solar_time: str, gender: str, **kwargs) -> Optional[Any]:
        """获取八字缓存"""
        key = self._generate_key(solar_date, solar_time, gender, **kwargs)
        return self.get(key)
    
    def set_bazi(self, solar_date: str, solar_time: str, gender: str, value: Any, **kwargs):
        """设置八字缓存"""
        key = self._generate_key(solar_date, solar_time, gender, **kwargs)
        self.set(key, value)
    
    def stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "l1": self.l1.stats(),
            "l2": self.l2.stats()
        }


# 全局多级缓存实例（延迟初始化）
_multi_cache: Optional[MultiLevelCache] = None


def get_multi_cache() -> MultiLevelCache:
    """获取多级缓存实例（单例模式）"""
    global _multi_cache
    
    if _multi_cache is None:
        # 尝试导入 Redis 客户端
        try:
            from server.config.redis_config import get_redis_client
            redis_client = get_redis_client()
        except Exception:
            redis_client = None
        
        _multi_cache = MultiLevelCache(
            l1_max_size=50000,
            l1_ttl=300,
            redis_client=redis_client,
            redis_ttl=3600
        )
    
    return _multi_cache








































