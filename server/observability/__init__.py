#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可观测性模块

包含：
- 结构化日志 (StructuredLogger)
- 性能指标 (MetricsCollector)
- 分布式追踪 (Tracer)
- 监控告警 (AlertManager)
"""

from .structured_logger import StructuredLogger, get_logger, LogLevel
from .metrics_collector import MetricsCollector, get_metrics, Counter, Gauge, Histogram
from .tracer import Tracer, get_tracer, Span, TraceContext
from .alert_manager import AlertManager, get_alert_manager, Alert, AlertSeverity

__all__ = [
    # 日志
    'StructuredLogger',
    'get_logger',
    'LogLevel',
    # 指标
    'MetricsCollector',
    'get_metrics',
    'Counter',
    'Gauge',
    'Histogram',
    # 追踪
    'Tracer',
    'get_tracer',
    'Span',
    'TraceContext',
    # 告警
    'AlertManager',
    'get_alert_manager',
    'Alert',
    'AlertSeverity',
]
