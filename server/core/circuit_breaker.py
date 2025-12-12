#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
熔断器

功能：
- 防止级联故障
- 快速失败
- 自动恢复

状态：
- CLOSED: 正常状态，请求正常通过
- OPEN: 熔断状态，请求直接失败
- HALF_OPEN: 半开状态，允许部分请求通过测试
"""

import time
import threading
import logging
from enum import Enum
from typing import Dict, Optional, Callable, Any
from functools import wraps
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"       # 关闭状态（正常）
    OPEN = "open"           # 打开状态（熔断）
    HALF_OPEN = "half_open" # 半开状态（测试恢复）


class CircuitBreakerOpen(Exception):
    """熔断器打开异常"""
    def __init__(self, name: str, message: str = "Circuit breaker is open"):
        self.name = name
        super().__init__(f"[{name}] {message}")


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5          # 失败阈值
    success_threshold: int = 3          # 恢复成功阈值
    timeout: float = 30.0               # 熔断超时时间（秒）
    half_open_max_calls: int = 3        # 半开状态最大调用数
    excluded_exceptions: tuple = ()     # 不计入失败的异常类型


@dataclass
class CircuitBreakerStats:
    """熔断器统计"""
    total_calls: int = 0
    success_calls: int = 0
    failure_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: float = 0
    state_changes: int = 0


class CircuitBreaker:
    """
    熔断器
    
    使用示例：
        # 作为装饰器使用
        breaker = CircuitBreaker("bazi-core")
        
        @breaker
        def call_service():
            # 调用远程服务
            pass
        
        # 手动使用
        breaker = CircuitBreaker("bazi-core")
        
        if breaker.allow_request():
            try:
                result = call_service()
                breaker.record_success()
            except Exception as e:
                breaker.record_failure()
                raise
        else:
            raise CircuitBreakerOpen("bazi-core")
    """
    
    # 全局熔断器存储
    _breakers: Dict[str, 'CircuitBreaker'] = {}
    _lock = threading.Lock()
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0
        self._half_open_calls = 0
        self._stats = CircuitBreakerStats()
        self._lock = threading.Lock()
        
        # 注册到全局存储
        CircuitBreaker._breakers[name] = self
        
        logger.info(f"熔断器创建: {name} (failure_threshold={self.config.failure_threshold})")
    
    @classmethod
    def get(cls, name: str, config: Optional[CircuitBreakerConfig] = None) -> 'CircuitBreaker':
        """获取或创建熔断器"""
        with cls._lock:
            if name not in cls._breakers:
                cls._breakers[name] = cls(name, config)
            return cls._breakers[name]
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        self._check_state_transition()
        return self._state
    
    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN
    
    def allow_request(self) -> bool:
        """检查是否允许请求"""
        with self._lock:
            self._check_state_transition()
            
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                self._stats.rejected_calls += 1
                return False
            
            # HALF_OPEN 状态
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            
            self._stats.rejected_calls += 1
            return False
    
    def record_success(self):
        """记录成功"""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.success_calls += 1
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0  # 重置失败计数
    
    def record_failure(self, exception: Optional[Exception] = None):
        """记录失败"""
        # 检查是否是排除的异常
        if exception and isinstance(exception, self.config.excluded_exceptions):
            return
        
        with self._lock:
            self._stats.total_calls += 1
            self._stats.failure_calls += 1
            self._last_failure_time = time.time()
            self._stats.last_failure_time = self._last_failure_time
            
            if self._state == CircuitState.HALF_OPEN:
                # 半开状态下失败，立即转为打开状态
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
    
    def _check_state_transition(self):
        """检查状态转换"""
        if self._state == CircuitState.OPEN:
            # 检查是否超时，可以转为半开状态
            if time.time() - self._last_failure_time >= self.config.timeout:
                self._transition_to(CircuitState.HALF_OPEN)
    
    def _transition_to(self, new_state: CircuitState):
        """状态转换"""
        old_state = self._state
        self._state = new_state
        self._stats.state_changes += 1
        
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
        elif new_state == CircuitState.OPEN:
            self._last_failure_time = time.time()
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
            self._half_open_calls = 0
        
        logger.warning(f"熔断器状态变更: {self.name} {old_state.value} -> {new_state.value}")
    
    def reset(self):
        """重置熔断器"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            logger.info(f"熔断器重置: {self.name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "stats": {
                "total_calls": self._stats.total_calls,
                "success_calls": self._stats.success_calls,
                "failure_calls": self._stats.failure_calls,
                "rejected_calls": self._stats.rejected_calls,
                "state_changes": self._stats.state_changes,
            }
        }
    
    def __call__(self, func: Callable) -> Callable:
        """作为装饰器使用"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.allow_request():
                raise CircuitBreakerOpen(self.name)
            
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except self.config.excluded_exceptions:
                # 排除的异常不计入失败
                self.record_success()
                raise
            except Exception as e:
                self.record_failure(e)
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self.allow_request():
                raise CircuitBreakerOpen(self.name)
            
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except self.config.excluded_exceptions:
                self.record_success()
                raise
            except Exception as e:
                self.record_failure(e)
                raise
        
        # 判断是否是异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout: float = 30.0
) -> Callable:
    """
    熔断器装饰器工厂
    
    使用示例：
        @circuit_breaker("bazi-core", failure_threshold=3)
        def call_bazi_service():
            pass
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timeout
    )
    breaker = CircuitBreaker.get(name, config)
    return breaker


def get_all_breakers() -> Dict[str, CircuitBreaker]:
    """获取所有熔断器"""
    return CircuitBreaker._breakers.copy()


def get_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """获取所有熔断器统计"""
    return {name: breaker.get_stats() for name, breaker in CircuitBreaker._breakers.items()}
