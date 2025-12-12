#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能指标采集器

功能：
- 计数器 (Counter)
- 仪表盘 (Gauge)
- 直方图 (Histogram)
- 指标导出
"""

import time
import threading
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict
from functools import wraps


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricValue:
    """指标值"""
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """
    计数器
    
    只能增加，用于计数请求数、错误数等
    """
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def inc(self, value: float = 1, **labels):
        """增加计数"""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] += value
    
    def get(self, **labels) -> float:
        """获取计数"""
        key = self._make_key(labels)
        return self._values.get(key, 0)
    
    def _make_key(self, labels: Dict[str, str]) -> tuple:
        """生成标签键"""
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[MetricValue]:
        """收集所有指标值"""
        results = []
        with self._lock:
            for key, value in self._values.items():
                results.append(MetricValue(
                    name=self.name,
                    type=MetricType.COUNTER,
                    value=value,
                    labels=dict(key)
                ))
        return results


class Gauge:
    """
    仪表盘
    
    可以增加或减少，用于当前连接数、内存使用等
    """
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def set(self, value: float, **labels):
        """设置值"""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] = value
    
    def inc(self, value: float = 1, **labels):
        """增加值"""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] += value
    
    def dec(self, value: float = 1, **labels):
        """减少值"""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] -= value
    
    def get(self, **labels) -> float:
        """获取值"""
        key = self._make_key(labels)
        return self._values.get(key, 0)
    
    def _make_key(self, labels: Dict[str, str]) -> tuple:
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[MetricValue]:
        results = []
        with self._lock:
            for key, value in self._values.items():
                results.append(MetricValue(
                    name=self.name,
                    type=MetricType.GAUGE,
                    value=value,
                    labels=dict(key)
                ))
        return results


class Histogram:
    """
    直方图
    
    用于记录请求延迟分布等
    """
    
    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._values: Dict[tuple, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._max_samples = 10000  # 保留最近的样本数
    
    def observe(self, value: float, **labels):
        """记录一个观测值"""
        key = self._make_key(labels)
        with self._lock:
            samples = self._values[key]
            samples.append(value)
            # 限制样本数量
            if len(samples) > self._max_samples:
                self._values[key] = samples[-self._max_samples:]
    
    def get_stats(self, **labels) -> Dict[str, float]:
        """获取统计信息"""
        key = self._make_key(labels)
        samples = self._values.get(key, [])
        
        if not samples:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_samples = sorted(samples)
        count = len(samples)
        
        return {
            "count": count,
            "sum": sum(samples),
            "avg": statistics.mean(samples),
            "min": min(samples),
            "max": max(samples),
            "p50": self._percentile(sorted_samples, 50),
            "p95": self._percentile(sorted_samples, 95),
            "p99": self._percentile(sorted_samples, 99),
        }
    
    def _percentile(self, sorted_data: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not sorted_data:
            return 0
        k = (len(sorted_data) - 1) * (percentile / 100)
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)
    
    def _make_key(self, labels: Dict[str, str]) -> tuple:
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[MetricValue]:
        results = []
        with self._lock:
            for key, samples in self._values.items():
                if samples:
                    stats = self.get_stats(**dict(key))
                    results.append(MetricValue(
                        name=self.name,
                        type=MetricType.HISTOGRAM,
                        value=stats["avg"],
                        labels={**dict(key), "_stats": str(stats)}
                    ))
        return results


class MetricsCollector:
    """
    指标采集器
    
    使用示例：
        metrics = MetricsCollector.get_instance()
        
        # 创建指标
        request_count = metrics.counter("http_requests_total", "HTTP请求总数", ["method", "path"])
        request_latency = metrics.histogram("http_request_duration_seconds", "HTTP请求延迟")
        active_connections = metrics.gauge("active_connections", "活跃连接数")
        
        # 记录指标
        request_count.inc(method="POST", path="/api/bazi")
        request_latency.observe(0.5, method="POST", path="/api/bazi")
        active_connections.inc()
    """
    
    _instance: Optional['MetricsCollector'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._start_time = time.time()
    
    @classmethod
    def get_instance(cls) -> 'MetricsCollector':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def counter(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None
    ) -> Counter:
        """创建或获取计数器"""
        if name not in self._counters:
            self._counters[name] = Counter(name, description, labels)
        return self._counters[name]
    
    def gauge(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None
    ) -> Gauge:
        """创建或获取仪表盘"""
        if name not in self._gauges:
            self._gauges[name] = Gauge(name, description, labels)
        return self._gauges[name]
    
    def histogram(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None
    ) -> Histogram:
        """创建或获取直方图"""
        if name not in self._histograms:
            self._histograms[name] = Histogram(name, description, labels, buckets)
        return self._histograms[name]
    
    def collect_all(self) -> Dict[str, Any]:
        """收集所有指标"""
        result = {
            "uptime_seconds": time.time() - self._start_time,
            "counters": {},
            "gauges": {},
            "histograms": {}
        }
        
        for name, counter in self._counters.items():
            values = counter.collect()
            result["counters"][name] = [v.value for v in values] if values else [0]
        
        for name, gauge in self._gauges.items():
            values = gauge.collect()
            result["gauges"][name] = [v.value for v in values] if values else [0]
        
        for name, histogram in self._histograms.items():
            result["histograms"][name] = {}
            for key in histogram._values.keys():
                labels = dict(key)
                stats = histogram.get_stats(**labels)
                label_str = ",".join(f"{k}={v}" for k, v in labels.items()) or "default"
                result["histograms"][name][label_str] = stats
        
        return result
    
    def export_prometheus(self) -> str:
        """导出 Prometheus 格式"""
        lines = []
        
        # 计数器
        for name, counter in self._counters.items():
            lines.append(f"# HELP {name} {counter.description}")
            lines.append(f"# TYPE {name} counter")
            for value in counter.collect():
                labels_str = ",".join(f'{k}="{v}"' for k, v in value.labels.items())
                if labels_str:
                    lines.append(f"{name}{{{labels_str}}} {value.value}")
                else:
                    lines.append(f"{name} {value.value}")
        
        # 仪表盘
        for name, gauge in self._gauges.items():
            lines.append(f"# HELP {name} {gauge.description}")
            lines.append(f"# TYPE {name} gauge")
            for value in gauge.collect():
                labels_str = ",".join(f'{k}="{v}"' for k, v in value.labels.items())
                if labels_str:
                    lines.append(f"{name}{{{labels_str}}} {value.value}")
                else:
                    lines.append(f"{name} {value.value}")
        
        # 直方图
        for name, histogram in self._histograms.items():
            lines.append(f"# HELP {name} {histogram.description}")
            lines.append(f"# TYPE {name} histogram")
            for key, samples in histogram._values.items():
                labels = dict(key)
                stats = histogram.get_stats(**labels)
                labels_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                base = f"{name}{{{labels_str}}}" if labels_str else name
                lines.append(f"{base}_count {stats['count']}")
                lines.append(f"{base}_sum {stats['sum']}")
        
        return "\n".join(lines)


def get_metrics() -> MetricsCollector:
    """获取指标采集器实例"""
    return MetricsCollector.get_instance()


def timed(histogram_name: str, **labels):
    """
    计时装饰器
    
    使用示例：
        @timed("http_request_duration_seconds", method="POST")
        def handle_request():
            pass
    """
    def decorator(func: Callable):
        metrics = get_metrics()
        hist = metrics.histogram(histogram_name)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                hist.observe(duration, **labels)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                hist.observe(duration, **labels)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def counted(counter_name: str, **labels):
    """
    计数装饰器
    
    使用示例：
        @counted("http_requests_total", method="POST")
        def handle_request():
            pass
    """
    def decorator(func: Callable):
        metrics = get_metrics()
        counter = metrics.counter(counter_name)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            counter.inc(**labels)
            return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            counter.inc(**labels)
            return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator
