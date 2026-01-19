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
        # 缓存统计
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """从缓存获取结果"""
        if key not in self._cache:
            self._misses += 1
            return None
        if time.time() - self._cache_times[key] > self.ttl:
            del self._cache[key]
            del self._cache_times[key]
            self._misses += 1
            return None
        self._hits += 1
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
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
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
        # 缓存统计
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """从缓存获取结果"""
        if not self._available:
            self._misses += 1
            return None
        try:
            data = self.redis.get(key)
            if data:
                self._hits += 1
                return json.loads(data)
            else:
                self._misses += 1
        except Exception:
            self._misses += 1
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
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            
            stats = {
                "status": "available",
                "used_memory": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 0),
                "keyspace": info.get('db0', {}),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests
            }
            return stats
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
        # L1: 从内存缓存删除
        if key in self.l1._cache:
            del self.l1._cache[key]
        if key in self.l1._cache_times:
            del self.l1._cache_times[key]
        # L2: 从Redis删除
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
        l1_stats = self.l1.stats()
        l2_stats = self.l2.stats()
        
        # 计算总体命中率
        total_hits = l1_stats.get('hits', 0) + l2_stats.get('hits', 0)
        total_misses = l1_stats.get('misses', 0) + l2_stats.get('misses', 0)
        total_requests = total_hits + total_misses
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "l1": l1_stats,
            "l2": l2_stats,
            "overall": {
                "hits": total_hits,
                "misses": total_misses,
                "total_requests": total_requests,
                "hit_rate_percent": round(overall_hit_rate, 2)
            }
        }
    
    def invalidate_pattern(self, pattern: str):
        """
        按模式删除缓存（支持通配符）
        
        Args:
            pattern: 缓存键模式（支持 * 通配符）
        """
        # L1: 遍历内存缓存
        keys_to_delete = []
        for key in list(self.l1._cache.keys()):
            if self._match_pattern(key, pattern):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            if key in self.l1._cache:
                del self.l1._cache[key]
            if key in self.l1._cache_times:
                del self.l1._cache_times[key]
        
        # L2: Redis支持模式删除（使用SCAN）
        if self.l2._available:
            try:
                # 使用Redis的SCAN命令查找匹配的键
                cursor = 0
                while True:
                    cursor, keys = self.l2.redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        self.l2.redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception:
                pass  # Redis不可用时忽略
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """简单的模式匹配（支持 * 通配符）"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)


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








































