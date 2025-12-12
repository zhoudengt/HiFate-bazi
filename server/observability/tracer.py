#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式追踪模块

功能：
- 请求追踪
- 跨服务追踪
- 性能分析
"""

import time
import uuid
import threading
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable
from contextvars import ContextVar
from functools import wraps
from enum import Enum
import json

logger = logging.getLogger(__name__)

# 上下文变量
_trace_context: ContextVar[Optional['TraceContext']] = ContextVar('trace_context', default=None)


class SpanStatus(Enum):
    """Span 状态"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TraceContext:
    """追踪上下文"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def to_headers(self) -> Dict[str, str]:
        """转换为 HTTP 头"""
        return {
            "X-Trace-ID": self.trace_id,
            "X-Span-ID": self.span_id,
            "X-Parent-Span-ID": self.parent_span_id or "",
        }
    
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional['TraceContext']:
        """从 HTTP 头解析"""
        trace_id = headers.get("X-Trace-ID") or headers.get("x-trace-id")
        if not trace_id:
            return None
        
        return cls(
            trace_id=trace_id,
            span_id=headers.get("X-Span-ID") or headers.get("x-span-id") or cls.generate_id(),
            parent_span_id=headers.get("X-Parent-Span-ID") or headers.get("x-parent-span-id") or None
        )
    
    @staticmethod
    def generate_id() -> str:
        """生成 ID"""
        return uuid.uuid4().hex[:16]


@dataclass
class Span:
    """追踪 Span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.OK
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    
    def finish(self, status: SpanStatus = SpanStatus.OK, error: Optional[str] = None):
        """结束 Span"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error
    
    def set_tag(self, key: str, value: Any):
        """设置标签"""
        self.tags[key] = value
    
    def log(self, message: str, **kwargs):
        """记录日志"""
        self.logs.append({
            "timestamp": time.time(),
            "message": message,
            **kwargs
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "tags": self.tags,
            "logs": self.logs,
            "error": self.error
        }


class Tracer:
    """
    分布式追踪器
    
    使用示例：
        tracer = Tracer.get_instance()
        
        # 开始追踪
        with tracer.start_span("handle_request") as span:
            span.set_tag("user_id", 123)
            
            # 嵌套 span
            with tracer.start_span("db_query") as child_span:
                result = db.query()
                child_span.set_tag("rows", len(result))
        
        # 作为装饰器
        @tracer.trace("handle_request")
        def handle_request():
            pass
    """
    
    _instance: Optional['Tracer'] = None
    _lock = threading.Lock()
    
    def __init__(self, service_name: str = "hifate-bazi"):
        self.service_name = service_name
        self._spans: List[Span] = []
        self._max_spans = 10000
        self._lock = threading.Lock()
        self._exporters: List[Callable[[Span], None]] = []
    
    @classmethod
    def get_instance(cls, service_name: str = "hifate-bazi") -> 'Tracer':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(service_name)
        return cls._instance
    
    def add_exporter(self, exporter: Callable[[Span], None]):
        """添加 Span 导出器"""
        self._exporters.append(exporter)
    
    def start_span(
        self,
        operation_name: str,
        parent_context: Optional[TraceContext] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> 'SpanContext':
        """
        开始一个新的 Span
        
        Args:
            operation_name: 操作名称
            parent_context: 父上下文
            tags: 标签
            
        Returns:
            SpanContext: Span 上下文管理器
        """
        # 获取当前上下文
        current_context = parent_context or _trace_context.get()
        
        # 创建新的 Span
        if current_context:
            trace_id = current_context.trace_id
            parent_span_id = current_context.span_id
        else:
            trace_id = TraceContext.generate_id()
            parent_span_id = None
        
        span_id = TraceContext.generate_id()
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=time.time(),
            tags=tags or {}
        )
        
        # 创建新的上下文
        new_context = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        return SpanContext(self, span, new_context)
    
    def _finish_span(self, span: Span):
        """完成 Span"""
        # 存储 Span
        with self._lock:
            self._spans.append(span)
            if len(self._spans) > self._max_spans:
                self._spans = self._spans[-self._max_spans:]
        
        # 导出 Span
        for exporter in self._exporters:
            try:
                exporter(span)
            except Exception as e:
                logger.error(f"导出 Span 失败: {e}")
    
    def get_current_context(self) -> Optional[TraceContext]:
        """获取当前追踪上下文"""
        return _trace_context.get()
    
    def set_context(self, context: TraceContext):
        """设置追踪上下文"""
        _trace_context.set(context)
    
    def clear_context(self):
        """清除追踪上下文"""
        _trace_context.set(None)
    
    def trace(self, operation_name: str, **tags):
        """
        追踪装饰器
        
        使用示例：
            @tracer.trace("handle_request", user_id=123)
            def handle_request():
                pass
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.start_span(operation_name, tags=tags) as span:
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.span.error = str(e)
                        span.span.status = SpanStatus.ERROR
                        raise
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.start_span(operation_name, tags=tags) as span:
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.span.error = str(e)
                        span.span.status = SpanStatus.ERROR
                        raise
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return wrapper
        
        return decorator
    
    def get_traces(self, trace_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取追踪数据"""
        with self._lock:
            if trace_id:
                spans = [s for s in self._spans if s.trace_id == trace_id]
            else:
                spans = self._spans[-limit:]
            
            return [s.to_dict() for s in spans]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._spans)
            if not total:
                return {"total_spans": 0}
            
            durations = [s.duration_ms for s in self._spans if s.duration_ms]
            errors = sum(1 for s in self._spans if s.status == SpanStatus.ERROR)
            
            return {
                "total_spans": total,
                "error_count": errors,
                "error_rate": errors / total if total > 0 else 0,
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
            }


class SpanContext:
    """Span 上下文管理器"""
    
    def __init__(self, tracer: Tracer, span: Span, context: TraceContext):
        self.tracer = tracer
        self.span = span
        self.context = context
        self._token = None
    
    def __enter__(self) -> 'SpanContext':
        # 保存旧上下文，设置新上下文
        self._token = _trace_context.set(self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 完成 Span
        if exc_type:
            self.span.finish(SpanStatus.ERROR, str(exc_val))
        else:
            self.span.finish(SpanStatus.OK)
        
        # 恢复旧上下文
        _trace_context.set(self._token)
        
        # 通知追踪器
        self.tracer._finish_span(self.span)
        
        return False
    
    def set_tag(self, key: str, value: Any):
        """设置标签"""
        self.span.set_tag(key, value)
    
    def log(self, message: str, **kwargs):
        """记录日志"""
        self.span.log(message, **kwargs)


# 便捷函数
def get_tracer(service_name: str = "hifate-bazi") -> Tracer:
    """获取追踪器实例"""
    return Tracer.get_instance(service_name)


def trace(operation_name: str, **tags):
    """追踪装饰器"""
    return get_tracer().trace(operation_name, **tags)
