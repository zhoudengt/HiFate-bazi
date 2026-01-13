#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控指标收集器（简化版）

功能：
- 收集 gRPC 调用指标（调用次数、成功率、响应时间）
- 收集缓存命中率
- 收集服务健康状态

使用方式：
    from server.utils.metrics_collector import MetricsCollector
    
    collector = MetricsCollector()
    collector.record_grpc_call("bazi-core", "calculate_bazi", success=True, duration=0.1)
    collector.record_cache_hit("bazi:user:123", hit=True)
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

# 尝试使用现有的 MetricsCollector（如果可用）
try:
    from server.observability.metrics_collector import MetricsCollector as BaseMetricsCollector
    BASE_METRICS_AVAILABLE = True
except ImportError:
    BASE_METRICS_AVAILABLE = False
    BaseMetricsCollector = None


class MetricsCollector:
    """
    监控指标收集器（简化版）
    
    功能：
    - gRPC 调用指标收集
    - 缓存命中率统计
    - 服务健康状态监控
    
    默认启用，但可以通过环境变量关闭
    """
    
    _instance: Optional['MetricsCollector'] = None
    _lock = None
    
    def __init__(self):
        """初始化指标收集器"""
        import threading
        self._lock = threading.Lock()
        
        # 检查是否启用（默认启用）
        self._enabled = os.getenv("ENABLE_METRICS_COLLECTION", "true").lower() == "true"
        
        # 如果基础指标收集器可用，使用它
        if BASE_METRICS_AVAILABLE and self._enabled:
            try:
                self._base_metrics = BaseMetricsCollector.get_instance()
                self._use_base = True
            except Exception as e:
                logger.warning(f"无法使用基础指标收集器: {e}，使用简化版本")
                self._use_base = False
        else:
            self._use_base = False
        
        # 简化的指标存储（如果基础收集器不可用）
        if not self._use_base:
            self._grpc_calls: Dict[str, Dict[str, Any]] = {}
            self._cache_stats: Dict[str, Dict[str, int]] = {}
            self._service_health: Dict[str, bool] = {}
        
        if self._enabled:
            logger.info("监控指标收集器已启用")
        else:
            logger.info("监控指标收集器已禁用")
    
    @classmethod
    def get_instance(cls) -> 'MetricsCollector':
        """获取单例实例"""
        if cls._instance is None:
            import threading
            if cls._lock is None:
                cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def record_grpc_call(
        self,
        service: str,
        method: str,
        success: bool = True,
        duration: float = 0.0,
        error_type: Optional[str] = None
    ):
        """
        记录 gRPC 调用指标
        
        Args:
            service: 服务名称（如 "bazi-core"）
            method: 方法名称（如 "calculate_bazi"）
            success: 是否成功
            duration: 调用耗时（秒）
            error_type: 错误类型（如果失败）
        """
        if not self._enabled:
            return
        
        try:
            if self._use_base:
                # 使用基础指标收集器
                counter = self._base_metrics.counter(
                    "grpc_requests_total",
                    "gRPC 请求总数",
                    ["service", "method", "status"]
                )
                counter.inc(
                    service=service,
                    method=method,
                    status="success" if success else "failure"
                )
                
                histogram = self._base_metrics.histogram(
                    "grpc_request_duration_seconds",
                    "gRPC 请求延迟",
                    ["service", "method"]
                )
                histogram.observe(duration, service=service, method=method)
            else:
                # 使用简化版本
                key = f"{service}:{method}"
                with self._lock:
                    if key not in self._grpc_calls:
                        self._grpc_calls[key] = {
                            "total": 0,
                            "success": 0,
                            "failure": 0,
                            "total_duration": 0.0,
                            "max_duration": 0.0,
                            "min_duration": float('inf')
                        }
                    
                    stats = self._grpc_calls[key]
                    stats["total"] += 1
                    if success:
                        stats["success"] += 1
                    else:
                        stats["failure"] += 1
                    
                    stats["total_duration"] += duration
                    stats["max_duration"] = max(stats["max_duration"], duration)
                    if duration > 0:
                        stats["min_duration"] = min(stats["min_duration"], duration)
        except Exception as e:
            logger.warning(f"记录 gRPC 调用指标失败: {e}")
    
    def record_cache_hit(self, cache_key: str, hit: bool = True, cache_type: str = "default"):
        """
        记录缓存命中率
        
        Args:
            cache_key: 缓存 key（可选，用于调试）
            hit: 是否命中
            cache_type: 缓存类型（如 "bazi", "rule", "fortune"）
        """
        if not self._enabled:
            return
        
        try:
            if self._use_base:
                # 使用基础指标收集器
                counter = self._base_metrics.counter(
                    "cache_operations_total",
                    "缓存操作总数",
                    ["cache_type", "result"]
                )
                counter.inc(
                    cache_type=cache_type,
                    result="hit" if hit else "miss"
                )
            else:
                # 使用简化版本
                with self._lock:
                    if cache_type not in self._cache_stats:
                        self._cache_stats[cache_type] = {
                            "hits": 0,
                            "misses": 0
                        }
                    
                    stats = self._cache_stats[cache_type]
                    if hit:
                        stats["hits"] += 1
                    else:
                        stats["misses"] += 1
        except Exception as e:
            logger.warning(f"记录缓存指标失败: {e}")
    
    def record_service_health(self, service: str, healthy: bool):
        """
        记录服务健康状态
        
        Args:
            service: 服务名称
            healthy: 是否健康
        """
        if not self._enabled:
            return
        
        try:
            if self._use_base:
                # 使用基础指标收集器
                gauge = self._base_metrics.gauge(
                    "service_health",
                    "服务健康状态",
                    ["service"]
                )
                gauge.set(1.0 if healthy else 0.0, service=service)
            else:
                # 使用简化版本
                with self._lock:
                    self._service_health[service] = healthy
        except Exception as e:
            logger.warning(f"记录服务健康状态失败: {e}")
    
    def get_grpc_stats(self, service: Optional[str] = None) -> Dict[str, Any]:
        """
        获取 gRPC 调用统计
        
        Args:
            service: 服务名称，None 表示所有服务
            
        Returns:
            统计信息
        """
        if not self._enabled:
            return {}
        
        try:
            if self._use_base:
                # 从基础指标收集器获取
                all_metrics = self._base_metrics.collect_all()
                return all_metrics.get("histograms", {}).get("grpc_request_duration_seconds", {})
            else:
                # 从简化版本获取
                with self._lock:
                    if service:
                        key = f"{service}:"
                        filtered = {
                            k: v for k, v in self._grpc_calls.items()
                            if k.startswith(key)
                        }
                        return filtered
                    return self._grpc_calls.copy()
        except Exception as e:
            logger.warning(f"获取 gRPC 统计失败: {e}")
            return {}
    
    def get_cache_stats(self, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """
        获取缓存统计
        
        Args:
            cache_type: 缓存类型，None 表示所有类型
            
        Returns:
            统计信息，包含命中率
        """
        if not self._enabled:
            return {}
        
        try:
            if self._use_base:
                # 从基础指标收集器获取
                all_metrics = self._base_metrics.collect_all()
                return all_metrics.get("counters", {}).get("cache_operations_total", {})
            else:
                # 从简化版本获取
                with self._lock:
                    stats = {}
                    for ct, data in self._cache_stats.items():
                        if cache_type is None or ct == cache_type:
                            total = data["hits"] + data["misses"]
                            hit_rate = (data["hits"] / total * 100) if total > 0 else 0
                            stats[ct] = {
                                **data,
                                "total": total,
                                "hit_rate": hit_rate
                            }
                    return stats
        except Exception as e:
            logger.warning(f"获取缓存统计失败: {e}")
            return {}
    
    def get_service_health(self) -> Dict[str, bool]:
        """获取所有服务健康状态"""
        if not self._enabled:
            return {}
        
        try:
            if self._use_base:
                # 从基础指标收集器获取
                all_metrics = self._base_metrics.collect_all()
                return all_metrics.get("gauges", {}).get("service_health", {})
            else:
                # 从简化版本获取
                with self._lock:
                    return self._service_health.copy()
        except Exception as e:
            logger.warning(f"获取服务健康状态失败: {e}")
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计信息"""
        return {
            "grpc_calls": self.get_grpc_stats(),
            "cache_stats": self.get_cache_stats(),
            "service_health": self.get_service_health(),
            "enabled": self._enabled
        }


# 便捷函数
def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器实例"""
    return MetricsCollector.get_instance()


def record_grpc_call(service: str, method: str, success: bool = True, duration: float = 0.0):
    """记录 gRPC 调用的便捷函数"""
    collector = get_metrics_collector()
    collector.record_grpc_call(service, method, success, duration)


def record_cache_hit(cache_key: str, hit: bool = True, cache_type: str = "default"):
    """记录缓存命中的便捷函数"""
    collector = get_metrics_collector()
    collector.record_cache_hit(cache_key, hit, cache_type)


# 装饰器
def monitor_grpc_call(service: str, method: str):
    """
    gRPC 调用监控装饰器
    
    使用示例：
        @monitor_grpc_call("bazi-core", "calculate_bazi")
        def call_bazi_service():
            # 调用代码
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                duration = time.time() - start_time
                collector.record_grpc_call(service, method, success, duration, error_type)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                duration = time.time() - start_time
                collector.record_grpc_call(service, method, success, duration, error_type)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator
