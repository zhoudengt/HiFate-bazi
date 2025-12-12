#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
限流器

功能：
- 保护服务不被过载
- 支持多种限流算法
- 支持全局和按 key 限流

算法：
- 令牌桶（Token Bucket）
- 滑动窗口（Sliding Window）
- 固定窗口（Fixed Window）
"""

import time
import threading
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Any
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """限流异常"""
    def __init__(self, name: str, retry_after: float = 0):
        self.name = name
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {name}, retry after {retry_after:.2f}s")


class LimitAlgorithm(Enum):
    """限流算法"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimiterConfig:
    """限流器配置"""
    rate: float                           # 速率（请求/秒）
    capacity: int = 100                   # 容量（令牌桶容量）
    algorithm: LimitAlgorithm = LimitAlgorithm.TOKEN_BUCKET


class BaseLimiter(ABC):
    """限流器基类"""
    
    @abstractmethod
    def allow(self, key: str = "default") -> bool:
        """检查是否允许请求"""
        pass
    
    @abstractmethod
    def get_wait_time(self, key: str = "default") -> float:
        """获取需要等待的时间"""
        pass


class TokenBucketLimiter(BaseLimiter):
    """
    令牌桶限流器
    
    特点：
    - 允许突发流量
    - 平滑限流
    """
    
    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: 令牌生成速率（令牌/秒）
            capacity: 桶容量
        """
        self.rate = rate
        self.capacity = capacity
        self._buckets: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()
    
    def _get_bucket(self, key: str) -> Dict[str, float]:
        """获取或创建令牌桶"""
        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": self.capacity,
                "last_time": time.time()
            }
        return self._buckets[key]
    
    def _refill(self, bucket: Dict[str, float]):
        """补充令牌"""
        current_time = time.time()
        elapsed = current_time - bucket["last_time"]
        
        # 添加新令牌
        new_tokens = elapsed * self.rate
        bucket["tokens"] = min(self.capacity, bucket["tokens"] + new_tokens)
        bucket["last_time"] = current_time
    
    def allow(self, key: str = "default") -> bool:
        """检查是否允许请求"""
        with self._lock:
            bucket = self._get_bucket(key)
            self._refill(bucket)
            
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True
            return False
    
    def get_wait_time(self, key: str = "default") -> float:
        """获取需要等待的时间"""
        with self._lock:
            bucket = self._get_bucket(key)
            self._refill(bucket)
            
            if bucket["tokens"] >= 1:
                return 0
            
            # 计算需要等待多久才能获得一个令牌
            tokens_needed = 1 - bucket["tokens"]
            return tokens_needed / self.rate


class SlidingWindowLimiter(BaseLimiter):
    """
    滑动窗口限流器
    
    特点：
    - 更精确的限流
    - 内存占用较大
    """
    
    def __init__(self, rate: float, window_size: float = 1.0):
        """
        Args:
            rate: 速率（请求/窗口）
            window_size: 窗口大小（秒）
        """
        self.rate = rate
        self.window_size = window_size
        self._windows: Dict[str, list] = {}
        self._lock = threading.Lock()
    
    def _clean_old_requests(self, key: str):
        """清理过期请求"""
        current_time = time.time()
        cutoff = current_time - self.window_size
        
        if key in self._windows:
            self._windows[key] = [t for t in self._windows[key] if t > cutoff]
    
    def allow(self, key: str = "default") -> bool:
        """检查是否允许请求"""
        with self._lock:
            if key not in self._windows:
                self._windows[key] = []
            
            self._clean_old_requests(key)
            
            if len(self._windows[key]) < self.rate:
                self._windows[key].append(time.time())
                return True
            return False
    
    def get_wait_time(self, key: str = "default") -> float:
        """获取需要等待的时间"""
        with self._lock:
            if key not in self._windows:
                return 0
            
            self._clean_old_requests(key)
            
            if len(self._windows[key]) < self.rate:
                return 0
            
            # 等待最早的请求过期
            oldest = self._windows[key][0]
            return max(0, oldest + self.window_size - time.time())


class FixedWindowLimiter(BaseLimiter):
    """
    固定窗口限流器
    
    特点：
    - 简单高效
    - 可能有边界问题
    """
    
    def __init__(self, rate: float, window_size: float = 1.0):
        """
        Args:
            rate: 速率（请求/窗口）
            window_size: 窗口大小（秒）
        """
        self.rate = rate
        self.window_size = window_size
        self._counters: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def _get_window_key(self) -> int:
        """获取当前窗口 key"""
        return int(time.time() / self.window_size)
    
    def allow(self, key: str = "default") -> bool:
        """检查是否允许请求"""
        with self._lock:
            window_key = self._get_window_key()
            
            if key not in self._counters:
                self._counters[key] = {"window": window_key, "count": 0}
            
            counter = self._counters[key]
            
            # 新窗口，重置计数
            if counter["window"] != window_key:
                counter["window"] = window_key
                counter["count"] = 0
            
            if counter["count"] < self.rate:
                counter["count"] += 1
                return True
            return False
    
    def get_wait_time(self, key: str = "default") -> float:
        """获取需要等待的时间"""
        window_key = self._get_window_key()
        next_window = (window_key + 1) * self.window_size
        return max(0, next_window - time.time())


class RateLimiter:
    """
    限流器
    
    使用示例：
        # 创建限流器
        limiter = RateLimiter("api", rate=100)  # 每秒100次
        
        # 检查是否允许
        if limiter.allow(user_id):
            # 处理请求
            pass
        else:
            raise RateLimitExceeded("api")
        
        # 作为装饰器
        @limiter
        def handle_request():
            pass
    """
    
    # 全局限流器存储
    _limiters: Dict[str, 'RateLimiter'] = {}
    _lock = threading.Lock()
    
    def __init__(
        self,
        name: str,
        rate: float,
        capacity: int = 100,
        algorithm: LimitAlgorithm = LimitAlgorithm.TOKEN_BUCKET
    ):
        self.name = name
        self.rate = rate
        self.capacity = capacity
        self.algorithm = algorithm
        
        # 创建底层限流器
        if algorithm == LimitAlgorithm.TOKEN_BUCKET:
            self._limiter = TokenBucketLimiter(rate, capacity)
        elif algorithm == LimitAlgorithm.SLIDING_WINDOW:
            self._limiter = SlidingWindowLimiter(rate)
        else:
            self._limiter = FixedWindowLimiter(rate)
        
        # 统计
        self._stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "rejected_requests": 0,
        }
        self._stats_lock = threading.Lock()
        
        # 注册到全局
        RateLimiter._limiters[name] = self
        
        logger.info(f"限流器创建: {name} (rate={rate}/s, algorithm={algorithm.value})")
    
    @classmethod
    def get(
        cls,
        name: str,
        rate: float = 100,
        capacity: int = 100,
        algorithm: LimitAlgorithm = LimitAlgorithm.TOKEN_BUCKET
    ) -> 'RateLimiter':
        """获取或创建限流器"""
        with cls._lock:
            if name not in cls._limiters:
                cls._limiters[name] = cls(name, rate, capacity, algorithm)
            return cls._limiters[name]
    
    def allow(self, key: str = "default") -> bool:
        """检查是否允许请求"""
        with self._stats_lock:
            self._stats["total_requests"] += 1
        
        allowed = self._limiter.allow(key)
        
        with self._stats_lock:
            if allowed:
                self._stats["allowed_requests"] += 1
            else:
                self._stats["rejected_requests"] += 1
        
        return allowed
    
    def get_wait_time(self, key: str = "default") -> float:
        """获取需要等待的时间"""
        return self._limiter.get_wait_time(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            return {
                "name": self.name,
                "rate": self.rate,
                "algorithm": self.algorithm.value,
                **self._stats.copy()
            }
    
    def __call__(self, func: Callable) -> Callable:
        """作为装饰器使用"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 尝试从参数中获取 key
            key = kwargs.get("user_id") or kwargs.get("key") or "default"
            
            if not self.allow(str(key)):
                wait_time = self.get_wait_time(str(key))
                raise RateLimitExceeded(self.name, wait_time)
            
            return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = kwargs.get("user_id") or kwargs.get("key") or "default"
            
            if not self.allow(str(key)):
                wait_time = self.get_wait_time(str(key))
                raise RateLimitExceeded(self.name, wait_time)
            
            return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper


def rate_limit(
    name: str,
    rate: float = 100,
    capacity: int = 100,
    algorithm: LimitAlgorithm = LimitAlgorithm.TOKEN_BUCKET
) -> Callable:
    """
    限流装饰器工厂
    
    使用示例：
        @rate_limit("api", rate=100)
        def handle_request():
            pass
    """
    limiter = RateLimiter.get(name, rate, capacity, algorithm)
    return limiter


def get_all_limiters() -> Dict[str, RateLimiter]:
    """获取所有限流器"""
    return RateLimiter._limiters.copy()


def get_limiter_stats() -> Dict[str, Dict[str, Any]]:
    """获取所有限流器统计"""
    return {name: limiter.get_stats() for name, limiter in RateLimiter._limiters.items()}
