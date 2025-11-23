#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存工具模块 - 用于高并发场景下的结果缓存
"""

import hashlib
import json
from functools import lru_cache
from typing import Any, Optional
import time


class BaziCache:
    """八字计算结果缓存"""
    
    def __init__(self, max_size: int = 10000, ttl: int = 3600):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间（秒），默认1小时
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache = {}
        self._cache_times = {}
    
    def _generate_key(self, solar_date: str, solar_time: str, gender: str, **kwargs) -> str:
        """生成缓存键"""
        # 将参数组合成字符串并生成哈希
        cache_str = f"{solar_date}:{solar_time}:{gender}"
        if kwargs:
            cache_str += ":" + json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def get(self, solar_date: str, solar_time: str, gender: str, **kwargs) -> Optional[Any]:
        """
        从缓存获取结果
        
        Returns:
            缓存的结果，如果不存在或已过期则返回None
        """
        key = self._generate_key(solar_date, solar_time, gender, **kwargs)
        
        if key not in self._cache:
            return None
        
        # 检查是否过期
        if time.time() - self._cache_times[key] > self.ttl:
            del self._cache[key]
            del self._cache_times[key]
            return None
        
        return self._cache[key]
    
    def set(self, solar_date: str, solar_time: str, gender: str, value: Any, **kwargs):
        """
        设置缓存
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            value: 要缓存的值
            **kwargs: 其他参数
        """
        key = self._generate_key(solar_date, solar_time, gender, **kwargs)
        
        # 如果缓存已满，删除最旧的条目
        if len(self._cache) >= self.max_size:
            # 删除最旧的条目
            oldest_key = min(self._cache_times.keys(), key=lambda k: self._cache_times[k])
            del self._cache[oldest_key]
            del self._cache_times[oldest_key]
        
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


# 全局缓存实例
bazi_cache = BaziCache(max_size=10000, ttl=3600)








































