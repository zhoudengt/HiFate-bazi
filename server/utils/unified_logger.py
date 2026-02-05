#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志系统 - 异步、详细、结构化日志
要求：每个环节都必须有详细日志，包括输入输出
"""

import json
import logging
import logging.handlers
import os
import sys
import traceback
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue
from threading import Thread, Lock
from typing import Any, Dict, Optional, Union
from contextlib import contextmanager

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class UnifiedLogger:
    """
    统一日志系统 - 异步写入，详细记录所有输入输出
    
    特性：
    1. 异步写入，不阻塞业务逻辑
    2. 结构化JSON格式，便于查询和分析
    3. 详细记录所有输入输出参数
    4. 支持请求追踪（request_id）
    5. 自动脱敏敏感信息
    6. 自动记录异常堆栈
    """
    
    _instance: Optional['UnifiedLogger'] = None
    _lock = Lock()
    
    def __init__(self, 
                 log_dir: str = "logs",
                 log_file: str = "unified.log",
                 max_bytes: int = 100 * 1024 * 1024,  # 100MB
                 backup_count: int = 10,
                 async_write: bool = True,
                 enable_console: bool = True):
        """
        初始化统一日志系统
        
        Args:
            log_dir: 日志目录
            log_file: 日志文件名
            max_bytes: 单个日志文件最大大小
            backup_count: 保留的备份文件数量
            async_write: 是否异步写入
            enable_console: 是否输出到控制台
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.log_dir / log_file
        self.async_write = async_write
        self.enable_console = enable_console
        
        # 创建日志记录器
        self.logger = logging.getLogger("UnifiedLogger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # 清除已有处理器
        
        # 文件处理器（异步写入）
        if async_write:
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
        else:
            file_handler = logging.FileHandler(
                self.log_file,
                encoding='utf-8'
            )
        
        # 控制台处理器
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # 异步队列（如果启用异步写入）
        if async_write:
            self.log_queue = Queue(maxsize=10000)
            self.worker_thread = Thread(target=self._async_worker, daemon=True)
            self.worker_thread.start()
        
        # 敏感信息字段（需要脱敏）
        self.sensitive_fields = {
            'password', 'passwd', 'pwd',
            'token', 'access_token', 'api_key', 'secret',
            'authorization', 'auth',
            'credit_card', 'card_number',
            'id_card', 'identity',
            'phone', 'mobile', 'tel'
        }
    
    @classmethod
    def get_instance(cls) -> 'UnifiedLogger':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _mask_sensitive_data(self, data: Any) -> Any:
        """
        脱敏处理敏感数据
        
        Args:
            data: 需要脱敏的数据
            
        Returns:
            脱敏后的数据
        """
        if isinstance(data, str):
            if len(data) <= 8:
                return '*' * len(data)
            return data[:4] + '*' * (len(data) - 8) + data[-4:]
        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                key_lower = key.lower()
                # 检查是否是敏感字段
                is_sensitive = any(sensitive in key_lower for sensitive in self.sensitive_fields)
                if is_sensitive:
                    result[key] = self._mask_sensitive_data(value)
                else:
                    result[key] = self._mask_sensitive_data(value) if isinstance(value, (dict, list)) else value
            return result
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        return data
    
    def _build_log_entry(self,
                        level: LogLevel,
                        service: str,
                        function: str,
                        message: str,
                        request_id: Optional[str] = None,
                        input_data: Optional[Dict] = None,
                        output_data: Optional[Dict] = None,
                        error: Optional[Exception] = None,
                        duration_ms: Optional[float] = None,
                        extra: Optional[Dict] = None) -> Dict[str, Any]:
        """
        构建结构化日志条目
        
        Args:
            level: 日志级别
            service: 服务名称
            function: 函数/方法名称
            message: 日志消息
            request_id: 请求ID（用于追踪）
            input_data: 输入数据
            output_data: 输出数据
            error: 异常对象
            duration_ms: 耗时（毫秒）
            extra: 额外信息
            
        Returns:
            结构化日志条目
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level.value,
            'service': service,
            'function': function,
            'message': message,
            'request_id': request_id or str(uuid.uuid4()),
        }
        
        # 添加输入数据（脱敏）
        if input_data is not None:
            log_entry['input'] = self._mask_sensitive_data(input_data)
        
        # 添加输出数据（脱敏）
        if output_data is not None:
            log_entry['output'] = self._mask_sensitive_data(output_data)
        
        # 添加异常信息
        if error is not None:
            log_entry['error'] = {
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        
        # 添加耗时
        if duration_ms is not None:
            log_entry['duration_ms'] = duration_ms
        
        # 添加额外信息
        if extra:
            log_entry['extra'] = self._mask_sensitive_data(extra)
        
        return log_entry
    
    def _async_worker(self):
        """异步写入工作线程"""
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=100 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        
        # JSON格式化器
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                if isinstance(record.msg, dict):
                    return json.dumps(record.msg, ensure_ascii=False, indent=2)
                return json.dumps({
                    'timestamp': datetime.utcnow().isoformat(),
                    'level': record.levelname,
                    'message': record.getMessage(),
                }, ensure_ascii=False)
        
        file_handler.setFormatter(JSONFormatter())
        
        logger = logging.getLogger("AsyncFileLogger")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        logger.propagate = False
        
        while True:
            try:
                log_entry = self.log_queue.get(timeout=1)
                if log_entry is None:  # 退出信号
                    break
                logger.log(logging.getLevelName(log_entry.get('level', 'INFO')), log_entry)
                self.log_queue.task_done()
            except Exception as e:
                # 异步写入失败，输出到控制台
                logger.warning(f"⚠️ 异步日志写入失败: {e}")
    
    def _log(self, level: LogLevel, **kwargs):
        """内部日志方法"""
        log_entry = self._build_log_entry(level=level, **kwargs)
        
        if self.async_write:
            try:
                self.log_queue.put_nowait(log_entry)
            except Exception as e:
                # 队列满，同步写入
                logger.warning(f"⚠️ 日志队列满，同步写入: {e}")
                self._sync_log(log_entry, level)
        else:
            self._sync_log(log_entry, level)
    
    def _sync_log(self, log_entry: Dict, level: LogLevel):
        """同步写入日志"""
        log_message = json.dumps(log_entry, ensure_ascii=False)
        
        if level == LogLevel.DEBUG:
            self.logger.debug(log_message)
        elif level == LogLevel.INFO:
            self.logger.info(log_message)
        elif level == LogLevel.WARNING:
            self.logger.warning(log_message)
        elif level == LogLevel.ERROR:
            self.logger.error(log_message)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(log_message)
    
    def log_request(self,
                   service: str,
                   function: str,
                   request_id: Optional[str] = None,
                   input_data: Optional[Dict] = None,
                   **kwargs):
        """记录请求日志"""
        self._log(
            level=LogLevel.INFO,
            service=service,
            function=function,
            message=f"[{service}] {function} - 收到请求",
            request_id=request_id,
            input_data=input_data,
            **kwargs
        )
    
    def log_response(self,
                    service: str,
                    function: str,
                    request_id: Optional[str] = None,
                    output_data: Optional[Dict] = None,
                    duration_ms: Optional[float] = None,
                    **kwargs):
        """记录响应日志"""
        self._log(
            level=LogLevel.INFO,
            service=service,
            function=function,
            message=f"[{service}] {function} - 响应成功",
            request_id=request_id,
            output_data=output_data,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_error(self,
                 service: str,
                 function: str,
                 error: Exception,
                 request_id: Optional[str] = None,
                 input_data: Optional[Dict] = None,
                 duration_ms: Optional[float] = None,
                 **kwargs):
        """记录错误日志"""
        self._log(
            level=LogLevel.ERROR,
            service=service,
            function=function,
            message=f"[{service}] {function} - 处理失败: {str(error)}",
            request_id=request_id,
            input_data=input_data,
            error=error,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_function(self,
                    service: str,
                    function: str,
                    message: str,
                    request_id: Optional[str] = None,
                    input_data: Optional[Dict] = None,
                    output_data: Optional[Dict] = None,
                    level: LogLevel = LogLevel.INFO,
                    duration_ms: Optional[float] = None,
                    **kwargs):
        """记录函数调用日志"""
        self._log(
            level=level,
            service=service,
            function=function,
            message=message,
            request_id=request_id,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            **kwargs
        )
    
    @contextmanager
    def trace_function(self,
                      service: str,
                      function: str,
                      request_id: Optional[str] = None,
                      input_data: Optional[Dict] = None):
        """
        函数追踪上下文管理器
        自动记录函数调用、输入、输出、耗时和异常
        
        Usage:
            with logger.trace_function('BaziService', 'calculate_bazi', request_id='123', input_data={'date': '1990-01-01'}):
                result = do_something()
                logger.log_response(..., output_data=result)
        """
        start_time = datetime.utcnow()
        try:
            self.log_request(service, function, request_id=request_id, input_data=input_data)
            yield
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.log_error(
                service, function, e,
                request_id=request_id,
                input_data=input_data,
                duration_ms=duration_ms
            )
            raise
    
    def shutdown(self):
        """关闭日志系统"""
        if self.async_write:
            self.log_queue.put(None)  # 发送退出信号
            self.worker_thread.join(timeout=5)


# 全局单例实例
_logger_instance: Optional[UnifiedLogger] = None


def get_unified_logger() -> UnifiedLogger:
    """获取统一日志系统实例"""
    global _logger_instance
    if _logger_instance is None:
        log_dir = os.getenv('LOG_DIR', 'logs')
        log_file = os.getenv('LOG_FILE', 'unified.log')
        async_write = os.getenv('LOG_ASYNC', 'true').lower() == 'true'
        enable_console = os.getenv('LOG_CONSOLE', 'true').lower() == 'true'
        
        _logger_instance = UnifiedLogger(
            log_dir=log_dir,
            log_file=log_file,
            async_write=async_write,
            enable_console=enable_console
        )
    return _logger_instance


# 便捷函数
def log_request(service: str, function: str, request_id: Optional[str] = None, input_data: Optional[Dict] = None, **kwargs):
    """记录请求日志"""
    get_unified_logger().log_request(service, function, request_id, input_data, **kwargs)


def log_response(service: str, function: str, request_id: Optional[str] = None, output_data: Optional[Dict] = None, duration_ms: Optional[float] = None, **kwargs):
    """记录响应日志"""
    get_unified_logger().log_response(service, function, request_id, output_data, duration_ms, **kwargs)


def log_error(service: str, function: str, error: Exception, request_id: Optional[str] = None, input_data: Optional[Dict] = None, duration_ms: Optional[float] = None, **kwargs):
    """记录错误日志"""
    get_unified_logger().log_error(service, function, error, request_id, input_data, duration_ms, **kwargs)


def log_function(service: str, function: str, message: str, request_id: Optional[str] = None, input_data: Optional[Dict] = None, output_data: Optional[Dict] = None, level: LogLevel = LogLevel.INFO, duration_ms: Optional[float] = None, **kwargs):
    """记录函数调用日志"""
    get_unified_logger().log_function(service, function, message, request_id, input_data, output_data, level, duration_ms, **kwargs)


def trace_function(service: str, function: str, request_id: Optional[str] = None, input_data: Optional[Dict] = None):
    """函数追踪上下文管理器"""
    return get_unified_logger().trace_function(service, function, request_id, input_data)

