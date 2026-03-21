#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多级缓存系统 - 支持500万用户
架构：L1(内存) -> L2(Redis) -> L3(数据库/持久化)

缓存版本机制（ENABLE_CACHE_VERSION=true 时）：
- 所有 key 自动加版本前缀，版本号存 Redis，多 worker 共享
- 部署/热更新时 bump_cache_version() 使旧缓存自动失效，无需逐个清理
"""

import json
import hashlib
import logging
import os
import random
import threading
import time
from collections import OrderedDict
from typing import Any, Optional, Dict
from functools import lru_cache

logger = logging.getLogger(__name__)

# Redis 中存储的版本 key
_CACHE_VERSION_REDIS_KEY = "_cache_version"
_VERSION_REFRESH_TTL = 60  # 内存缓存版本的有效秒数

# L1: 本地内存缓存（热点数据）
class L1MemoryCache:
    """L1缓存：本地内存，存储最热的数据。使用 OrderedDict 实现 O(1) LRU 淘汰。"""
    
    def __init__(self, max_size: int = 50000, ttl: int = 300):
        self._cache: OrderedDict = OrderedDict()
        self._cache_expiry: dict = {}
        self.max_size = max_size
        self.ttl = ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            expiry = self._cache_expiry.get(key)
            if expiry and time.time() > expiry:
                del self._cache[key]
                self._cache_expiry.pop(key, None)
                self._misses += 1
                return None
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            effective = ttl if ttl is not None else self.ttl
            if effective:
                effective = effective + random.randint(0, max(1, int(effective * 0.1)))
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    oldest_key, _ = self._cache.popitem(last=False)
                    self._cache_expiry.pop(oldest_key, None)
            self._cache[key] = value
            if effective:
                self._cache_expiry[key] = time.time() + effective
    
    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)
            self._cache_expiry.pop(key, None)
    
    def clear(self):
        with self._lock:
            self._cache.clear()
            self._cache_expiry.clear()
    
    def stats(self) -> dict:
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
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存；ttl 为可选，不传则使用实例默认 TTL。TTL 会加 0–10% 随机偏移以防雪崩。"""
        if not self._available:
            return
        try:
            effective = ttl if ttl is not None else self.ttl
            if effective:
                effective = effective + random.randint(0, max(1, int(effective * 0.1)))
            data = json.dumps(value, ensure_ascii=False)
            self.redis.setex(key, effective, data)
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


# 空值占位符（缓存穿透保护：将“无结果”也缓存，避免反复击穿到 DB）
_NULL_VALUE = "__NULL__"


# 版本缓存（进程内，定期从 Redis 刷新）
_version_cache: Dict[str, Any] = {"version": "v1", "expiry": 0.0}
_version_lock = threading.Lock()


def _is_cache_version_enabled() -> bool:
    return os.getenv("ENABLE_CACHE_VERSION", "false").lower() == "true"


def _get_cache_version(redis_client) -> str:
    """从 Redis 获取当前缓存版本，带 60s 内存缓存"""
    if not _is_cache_version_enabled():
        return ""
    with _version_lock:
        now = time.time()
        if now < _version_cache["expiry"]:
            return _version_cache["version"]
    if not redis_client:
        return "v1"
    try:
        v = redis_client.get(_CACHE_VERSION_REDIS_KEY)
        ver = (v.decode() if isinstance(v, bytes) else v) or "v1"
        with _version_lock:
            _version_cache["version"] = ver
            _version_cache["expiry"] = now + _VERSION_REFRESH_TTL
        return ver
    except Exception:
        return "v1"


def _effective_key(redis_client, key: str) -> str:
    """获取带版本前缀的 key（若启用版本机制）"""
    if not _is_cache_version_enabled():
        return key
    ver = _get_cache_version(redis_client)
    if not ver:
        return key
    if key.startswith(f"{ver}:"):
        return key
    return f"{ver}:{key}"


def bump_cache_version(redis_client=None) -> str:
    """
    增加缓存版本号，使所有旧缓存自动失效。
    部署/热更新时调用。
    """
    if not redis_client:
        try:
            from shared.config.redis import get_redis_client
            redis_client = get_redis_client()
        except Exception as e:
            logger.warning(f"bump_cache_version: Redis 不可用: {e}")
            return "v1"
    try:
        cur = redis_client.get(_CACHE_VERSION_REDIS_KEY)
        cur_str = (cur.decode() if isinstance(cur, bytes) else cur) or "v1"
        try:
            num = int(cur_str.lstrip("v"))
        except ValueError:
            num = 1
        ver_str = f"v{num + 1}"
        redis_client.set(_CACHE_VERSION_REDIS_KEY, ver_str)
        with _version_lock:
            _version_cache["version"] = ver_str
            _version_cache["expiry"] = 0  # 强制下次刷新
        logger.info(f"缓存版本已更新: {cur_str} -> {ver_str}")
        return ver_str
    except Exception as e:
        logger.warning(f"bump_cache_version 失败: {e}")
        return "v1"


# 多级缓存管理器
class MultiLevelCache:
    """多级缓存管理器（支持空值缓存，防穿透）"""
    NULL_VALUE = _NULL_VALUE

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
        self._redis = redis_client

    def _key(self, key: str) -> str:
        return _effective_key(getattr(self.l2, "redis", None), key)
    
    def get(self, key: str) -> Optional[Any]:
        """
        多级缓存读取：L1 -> L2
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回None
        """
        k = self._key(key)
        # L1: 本地内存（最快）
        value = self.l1.get(k)
        if value is not None:
            if value == self.NULL_VALUE:
                return None
            return value

        # L2: Redis（较快）
        value = self.l2.get(k)
        if value is not None:
            if value == self.NULL_VALUE:
                return None
            # 回填L1
            self.l1.set(k, value)
            return value

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        多级缓存写入：同时写入L1和L2
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 可选，过期时间（秒）；不传则使用各层默认 TTL
        """
        k = self._key(key)
        if ttl is not None:
            self.l1.set(k, value, ttl=ttl)
            self.l2.set(k, value, ttl=ttl)
        else:
            self.l1.set(k, value)
            self.l2.set(k, value)

    def set_null(self, key: str, ttl: int = 60):
        """缓存空值，防止穿透（同一 key 短时间内不再请求下游）"""
        self.set(key, self.NULL_VALUE, ttl=ttl)
    
    def delete(self, key: str):
        """删除缓存（所有层级）"""
        k = self._key(key)
        self.l1.delete(k)
        self.l2.delete(k)
    
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
        """按模式删除缓存（支持通配符）"""
        with self.l1._lock:
            keys_to_delete = [k for k in self.l1._cache if self._match_pattern(k, pattern)]
            for key in keys_to_delete:
                self.l1._cache.pop(key, None)
                self.l1._cache_expiry.pop(key, None)
        
        # L2: Redis 支持模式删除（使用 SCAN）
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
            from shared.config.redis import get_redis_client
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








































