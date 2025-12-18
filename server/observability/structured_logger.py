#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化日志模块

功能：
- 统一日志格式
- 支持 JSON 输出
- 支持请求追踪
- 支持日志级别过滤
"""

import json
import logging
import os
import sys
import time
import threading
import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from contextvars import ContextVar
import uuid

# 上下文变量，用于存储请求级别的信息
_request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogRecord:
    """日志记录"""
    timestamp: str
    level: str
    logger: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    service: str = "hifate-bazi"
    host: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 移除空值
        return {k: v for k, v in data.items() if v is not None and v != {}}
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class JsonFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def __init__(self, service: str = "hifate-bazi"):
        super().__init__()
        self.service = service
        self.host = os.uname().nodename if hasattr(os, 'uname') else "unknown"
    
    def format(self, record: logging.LogRecord) -> str:
        # 获取上下文
        context = _request_context.get()
        
        # 构建日志记录
        log_record = LogRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            trace_id=context.get("trace_id"),
            span_id=context.get("span_id"),
            service=self.service,
            host=self.host,
            extra=getattr(record, 'extra', {}),
            duration_ms=getattr(record, 'duration_ms', None)
        )
        
        # 处理异常
        if record.exc_info:
            log_record.error = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return log_record.to_json()


class TextFormatter(logging.Formatter):
    """文本格式化器（带颜色）"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        context = _request_context.get()
        trace_id = context.get("trace_id", "-")[:8] if context.get("trace_id") else "-"
        
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # 基本格式
        msg = f"{timestamp} {color}[{record.levelname:8}]{reset} [{trace_id}] {record.name}: {record.getMessage()}"
        
        # 添加额外信息
        extra = getattr(record, 'extra', {})
        if extra:
            msg += f" | {json.dumps(extra, ensure_ascii=False)}"
        
        # 添加耗时
        duration = getattr(record, 'duration_ms', None)
        if duration is not None:
            msg += f" | duration={duration:.2f}ms"
        
        # 添加异常信息
        if record.exc_info:
            msg += f"\n{''.join(traceback.format_exception(*record.exc_info))}"
        
        return msg


class StructuredLogger:
    """
    结构化日志器
    
    使用示例：
        logger = StructuredLogger("my_module")
        
        # 基本使用
        logger.info("处理请求", user_id=123, action="login")
        
        # 带计时
        with logger.timed("数据库查询"):
            result = db.query()
        
        # 设置上下文
        logger.set_context(trace_id="abc123", user_id=123)
    """
    
    _instances: Dict[str, 'StructuredLogger'] = {}
    _lock = threading.Lock()
    _configured = False
    
    def __init__(self, name: str):
        self.name = name
        self._logger = logging.getLogger(name)
    
    @classmethod
    def configure(
        cls,
        level: Union[str, LogLevel] = LogLevel.INFO,
        json_output: bool = False,
        log_file: Optional[str] = None,
        service: str = "hifate-bazi"
    ):
        """
        配置日志系统
        
        Args:
            level: 日志级别
            json_output: 是否输出 JSON 格式
            log_file: 日志文件路径
            service: 服务名称
        """
        if cls._configured:
            return
        
        with cls._lock:
            if cls._configured:
                return
            
            # 获取级别
            if isinstance(level, LogLevel):
                level_name = level.value
            else:
                level_name = level.upper()
            
            log_level = getattr(logging, level_name, logging.INFO)
            
            # 创建根日志器
            root_logger = logging.getLogger()
            root_logger.setLevel(log_level)
            
            # 清除现有处理器
            root_logger.handlers.clear()
            
            # 创建格式化器
            if json_output:
                formatter = JsonFormatter(service)
            else:
                formatter = TextFormatter()
            
            # 控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            
            # 文件处理器
            if log_file:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(log_level)
                file_handler.setFormatter(JsonFormatter(service))  # 文件始终用 JSON
                root_logger.addHandler(file_handler)
            
            cls._configured = True
    
    @classmethod
    def get(cls, name: str) -> 'StructuredLogger':
        """获取日志器实例"""
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    cls._instances[name] = cls(name)
        return cls._instances[name]
    
    def _log(
        self,
        level: int,
        message: str,
        exc_info: bool = False,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """内部日志方法"""
        extra = kwargs
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(unknown file)",
            0,
            message,
            (),
            None if not exc_info else sys.exc_info()
        )
        record.extra = extra
        record.duration_ms = duration_ms
        self._logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info: bool = True, **kwargs):
        """错误日志"""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = True, **kwargs):
        """严重错误日志"""
        self._log(logging.CRITICAL, message, exc_info=exc_info, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """异常日志（自动记录堆栈）"""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        source_ip: str,
        endpoint: Optional[str] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录安全事件"""
        level_map = {
            'critical': logging.CRITICAL,
            'high': logging.ERROR,
            'medium': logging.WARNING,
            'low': logging.INFO,
        }
        level = level_map.get(severity.lower(), logging.WARNING)
        
        self._log(
            level,
            f"[安全事件] {event_type}: {description}",
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            endpoint=endpoint,
            **(metadata or {})
        )
    
    class _TimedContext:
        """计时上下文"""
        def __init__(self, logger: 'StructuredLogger', operation: str, **kwargs):
            self.logger = logger
            self.operation = operation
            self.kwargs = kwargs
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration_ms = (time.time() - self.start_time) * 1000
            if exc_type:
                self.logger._log(
                    logging.ERROR,
                    f"{self.operation} 失败",
                    exc_info=True,
                    duration_ms=duration_ms,
                    **self.kwargs
                )
            else:
                self.logger._log(
                    logging.INFO,
                    f"{self.operation} 完成",
                    duration_ms=duration_ms,
                    **self.kwargs
                )
            return False
    
    def timed(self, operation: str, **kwargs) -> _TimedContext:
        """
        计时上下文管理器
        
        使用示例：
            with logger.timed("数据库查询", table="users"):
                result = db.query()
        """
        return self._TimedContext(self, operation, **kwargs)
    
    @staticmethod
    def set_context(**kwargs):
        """设置请求上下文"""
        context = _request_context.get().copy()
        context.update(kwargs)
        _request_context.set(context)
    
    @staticmethod
    def get_context() -> Dict[str, Any]:
        """获取请求上下文"""
        return _request_context.get().copy()
    
    @staticmethod
    def clear_context():
        """清除请求上下文"""
        _request_context.set({})
    
    @staticmethod
    def generate_trace_id() -> str:
        """生成追踪 ID"""
        return uuid.uuid4().hex


# 便捷函数
def get_logger(name: str) -> StructuredLogger:
    """获取日志器"""
    return StructuredLogger.get(name)


def configure_logging(
    level: Union[str, LogLevel] = LogLevel.INFO,
    json_output: bool = False,
    log_file: Optional[str] = None
):
    """配置日志系统"""
    StructuredLogger.configure(level, json_output, log_file)
