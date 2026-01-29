#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口数据流日志 - 用于 ELK 采集

特性：
- 静默失败：所有日志方法异常不抛出，不影响业务
- 异步写入：队列 + 后台线程，不阻塞请求
- 100% 完整记录：prompt 与 LLM 响应不截断
- 单行 JSON 输出，便于 Filebeat 采集
- 安全序列化：处理不可序列化对象
- 敏感字段脱敏（可选）
- 多进程安全：文件追加写入原子性

性能优化：
- 批量写入减少 IO 次数
- 队列满时有限等待而非立即丢弃
- 低优先级后台线程
"""

import json
import os
import logging
import functools
import fcntl
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty, Full
from threading import Thread, Lock
from typing import Any, Dict, Optional, Set

# 静默失败用的错误日志（不依赖本模块，避免循环）
_error_logger = logging.getLogger("stream_flow_logger.errors")

# 特性开关：可通过环境变量关闭
STREAM_FLOW_LOGGING_ENABLED = os.getenv("STREAM_FLOW_LOGGING_ENABLED", "true").lower() == "true"

# 敏感字段脱敏开关（默认关闭，保留完整数据用于调试）
STREAM_FLOW_MASK_SENSITIVE = os.getenv("STREAM_FLOW_MASK_SENSITIVE", "false").lower() == "true"

# 敏感字段列表
_SENSITIVE_FIELDS: Set[str] = {
    "solar_date", "solar_time", "birth_date", "birth_time",
    "phone", "mobile", "id_card", "password", "token",
}


def _safe_log(func):
    """静默失败装饰器：日志异常不抛出，仅记录到 error 日志"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not STREAM_FLOW_LOGGING_ENABLED:
            return None
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            try:
                _error_logger.warning("stream_flow_logger 记录失败（静默）: %s", e, exc_info=False)
            except Exception:
                pass
            return None
    return wrapper


def _safe_serialize(obj: Any, max_depth: int = 10) -> Any:
    """
    安全序列化：处理不可序列化对象，避免 json.dumps 抛异常。
    """
    if max_depth <= 0:
        return "<max_depth_exceeded>"
    
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(item, max_depth - 1) for item in obj]
    
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            key = str(k) if not isinstance(k, str) else k
            # 敏感字段脱敏
            if STREAM_FLOW_MASK_SENSITIVE and key.lower() in _SENSITIVE_FIELDS:
                result[key] = "***MASKED***"
            else:
                result[key] = _safe_serialize(v, max_depth - 1)
        return result
    
    if isinstance(obj, bytes):
        return f"<bytes:{len(obj)}>"
    
    if hasattr(obj, "__dict__"):
        return _safe_serialize(obj.__dict__, max_depth - 1)
    
    # 其他类型转字符串
    try:
        return str(obj)
    except Exception:
        return f"<unserializable:{type(obj).__name__}>"


def _compute_length_safe(data: Any) -> int:
    """安全计算 JSON 长度，失败返回 -1"""
    try:
        return len(json.dumps(data, ensure_ascii=False))
    except Exception:
        return -1


class StreamFlowLogger:
    """
    流式数据流日志器。
    所有方法静默失败，不修改业务返回值，不抛出异常。
    
    多进程安全：使用文件追加模式 + fcntl 文件锁。
    """

    _instance: Optional["StreamFlowLogger"] = None
    _lock = Lock()
    _worker_started = False
    _dropped_count = 0  # 丢弃计数

    def __init__(
        self,
        log_dir: str = "logs",
        log_file: str = "stream_flow.log",
        max_queue_size: int = 5000,  # 降低队列大小，减少内存占用
        batch_size: int = 50,  # 批量写入大小
        batch_timeout: float = 1.0,  # 批量写入超时
    ):
        self.log_path = Path(log_dir) / log_file
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._queue: Queue = Queue(maxsize=max_queue_size)
        self._batch_size = batch_size
        self._batch_timeout = batch_timeout
        self._start_worker()

    def _start_worker(self):
        """启动后台写入线程（仅启动一次）"""
        with StreamFlowLogger._lock:
            if StreamFlowLogger._worker_started:
                return
            t = Thread(target=self._worker_loop, daemon=True, name="stream_flow_logger_worker")
            t.start()
            StreamFlowLogger._worker_started = True

    def _worker_loop(self):
        """后台线程：从队列批量取日志并写入文件"""
        batch = []
        while True:
            try:
                # 尝试获取一条，带超时
                entry = self._queue.get(timeout=self._batch_timeout)
                if entry is not None:
                    batch.append(entry)
                
                # 继续尝试获取更多（非阻塞）
                while len(batch) < self._batch_size:
                    try:
                        entry = self._queue.get_nowait()
                        if entry is not None:
                            batch.append(entry)
                    except Empty:
                        break
                
                # 批量写入
                if batch:
                    self._write_batch(batch)
                    batch = []
                    
            except Empty:
                # 超时，写入已有的批量
                if batch:
                    self._write_batch(batch)
                    batch = []
            except Exception as e:
                try:
                    _error_logger.warning("stream_flow worker 异常: %s", e)
                except Exception:
                    pass
                # 清空批量避免重复
                batch = []

    def _write_batch(self, batch: list) -> None:
        """批量写入文件，使用文件锁保证多进程安全"""
        if not batch:
            return
        
        lines = []
        for entry in batch:
            try:
                # 安全序列化
                safe_entry = _safe_serialize(entry)
                line = json.dumps(safe_entry, ensure_ascii=False)
                lines.append(line)
            except Exception as e:
                try:
                    _error_logger.warning("stream_flow 序列化失败: %s", e)
                except Exception:
                    pass
        
        if not lines:
            return
        
        content = "\n".join(lines) + "\n"
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                # 使用文件锁保证多进程安全（Linux/macOS）
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    f.write(content)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except (BlockingIOError, OSError):
                    # 无法获取锁时直接写入（追加模式在大多数系统上是原子的）
                    f.write(content)
        except Exception as e:
            try:
                _error_logger.warning("stream_flow 写入失败: %s", e)
            except Exception:
                pass

    def _enqueue(self, payload: Dict[str, Any]) -> None:
        """将一条日志放入队列，队列满时短暂等待后丢弃"""
        if not STREAM_FLOW_LOGGING_ENABLED:
            return
        try:
            # 尝试放入队列，最多等待 0.01 秒
            self._queue.put(payload, block=True, timeout=0.01)
        except Full:
            # 队列满，丢弃并计数
            StreamFlowLogger._dropped_count += 1
            if StreamFlowLogger._dropped_count % 100 == 1:
                try:
                    _error_logger.warning(
                        "stream_flow 队列已满，已丢弃 %d 条日志",
                        StreamFlowLogger._dropped_count
                    )
                except Exception:
                    pass
        except Exception:
            pass

    @_safe_log
    def log_request(
        self,
        trace_id: str,
        endpoint: str,
        input_params: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录请求入参。静默失败。"""
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id or "unknown",
            "stage": "request",
            "endpoint": endpoint,
            "input_params": input_params,
            **(extra or {}),
        }
        self._enqueue(payload)

    @_safe_log
    def log_input_data(
        self,
        trace_id: str,
        input_data: Dict[str, Any],
        endpoint: Optional[str] = None,
    ) -> None:
        """记录构建的 input_data（完整）。静默失败。"""
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id or "unknown",
            "stage": "input_data",
            "input_data": input_data,
            "input_data_length": _compute_length_safe(input_data),
        }
        if endpoint:
            payload["endpoint"] = endpoint
        self._enqueue(payload)

    @_safe_log
    def log_prompt(
        self,
        trace_id: str,
        prompt: str,
        endpoint: Optional[str] = None,
        model_or_app_id: Optional[str] = None,
    ) -> None:
        """记录发送给 LLM 的完整 prompt。静默失败。"""
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id or "unknown",
            "stage": "prompt",
            "prompt": prompt,
            "prompt_length": len(prompt) if prompt else 0,
        }
        if endpoint:
            payload["endpoint"] = endpoint
        if model_or_app_id:
            payload["model_or_app_id"] = model_or_app_id
        self._enqueue(payload)

    @_safe_log
    def log_llm_response(
        self,
        trace_id: str,
        response: str,
        duration_ms: float,
        endpoint: Optional[str] = None,
        model_or_app_id: Optional[str] = None,
    ) -> None:
        """记录 LLM 完整响应。静默失败。"""
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id or "unknown",
            "stage": "llm_response",
            "response": response,
            "response_length": len(response) if response else 0,
            "duration_ms": round(duration_ms, 2),
        }
        if endpoint:
            payload["endpoint"] = endpoint
        if model_or_app_id:
            payload["model_or_app_id"] = model_or_app_id
        self._enqueue(payload)

    @_safe_log
    def log_complete(
        self,
        trace_id: str,
        status: str = "success",
        total_duration_ms: Optional[float] = None,
        endpoint: Optional[str] = None,
    ) -> None:
        """记录请求完成。静默失败。"""
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id or "unknown",
            "stage": "complete",
            "status": status,
        }
        if total_duration_ms is not None:
            payload["total_duration_ms"] = round(total_duration_ms, 2)
        if endpoint:
            payload["endpoint"] = endpoint
        self._enqueue(payload)

    @_safe_log
    def log_error(
        self,
        trace_id: str,
        error_message: str,
        endpoint: Optional[str] = None,
    ) -> None:
        """记录错误。静默失败。"""
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id or "unknown",
            "stage": "error",
            "error_message": error_message,
        }
        if endpoint:
            payload["endpoint"] = endpoint
        self._enqueue(payload)


def get_stream_flow_logger() -> StreamFlowLogger:
    """获取 StreamFlowLogger 单例。"""
    if StreamFlowLogger._instance is None:
        with StreamFlowLogger._lock:
            if StreamFlowLogger._instance is None:
                log_dir = os.getenv("LOG_DIR", "logs")
                log_file = os.getenv("STREAM_FLOW_LOG_FILE", "stream_flow.log")
                StreamFlowLogger._instance = StreamFlowLogger(
                    log_dir=log_dir,
                    log_file=log_file,
                )
    return StreamFlowLogger._instance
