#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存工具模块 - 用于高并发场景下的结果缓存

性能优化：
- 使用 threading.RLock 保证线程安全
- 使用 OrderedDict 实现 O(1) 的 LRU 淘汰
"""

import hashlib
import json
from collections import OrderedDict
from functools import lru_cache
from typing import Any, Optional
import time
import threading


class BaziCache:
    """
    八字计算结果缓存（线程安全）
    
    使用 OrderedDict 实现 LRU 淘汰策略，保证 O(1) 的删除性能。
    """
    
    def __init__(self, max_size: int = 10000, ttl: int = 3600):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间（秒），默认1小时
        """
        self.max_size = max_size
        self.ttl = ttl
        # 使用 OrderedDict 维护插入顺序，便于 LRU 淘汰
        self._cache: OrderedDict = OrderedDict()
        self._cache_times: dict = {}
        # 线程锁，保证并发安全
        self._lock = threading.RLock()
    
    def _generate_key(self, solar_date: str, solar_time: str, gender: str, **kwargs) -> str:
        """生成缓存键"""
        # 将参数组合成字符串并生成哈希
        cache_str = f"{solar_date}:{solar_time}:{gender}"
        if kwargs:
            cache_str += ":" + json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def get(self, solar_date: str, solar_time: str, gender: str, **kwargs) -> Optional[Any]:
        """
        从缓存获取结果（线程安全）
        
        Returns:
            缓存的结果，如果不存在或已过期则返回None
        """
        key = self._generate_key(solar_date, solar_time, gender, **kwargs)
        
        with self._lock:
            if key not in self._cache:
                return None
            
            # 检查是否过期
            if time.time() - self._cache_times[key] > self.ttl:
                del self._cache[key]
                del self._cache_times[key]
                return None
            
            # 移动到末尾（LRU：最近访问的放到最后）
            self._cache.move_to_end(key)
            return self._cache[key]
    
    def set(self, solar_date: str, solar_time: str, gender: str, value: Any, **kwargs):
        """
        设置缓存（线程安全）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            value: 要缓存的值
            **kwargs: 其他参数
        """
        key = self._generate_key(solar_date, solar_time, gender, **kwargs)
        
        with self._lock:
            # 如果 key 已存在，先删除（后面会重新插入到末尾）
            if key in self._cache:
                del self._cache[key]
            
            # 如果缓存已满，删除最旧的条目（O(1) 操作）
            while len(self._cache) >= self.max_size:
                # popitem(last=False) 删除最早插入的条目
                oldest_key, _ = self._cache.popitem(last=False)
                if oldest_key in self._cache_times:
                    del self._cache_times[oldest_key]
            
            self._cache[key] = value
            self._cache_times[key] = time.time()
    
    def clear(self):
        """清空缓存（线程安全）"""
        with self._lock:
            self._cache.clear()
            self._cache_times.clear()
    
    def stats(self) -> dict:
        """获取缓存统计信息（线程安全）"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl
            }


# 全局缓存实例
bazi_cache = BaziCache(max_size=10000, ttl=3600)








































