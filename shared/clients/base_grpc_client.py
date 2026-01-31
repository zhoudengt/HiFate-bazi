#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC 客户端基类
提供公共的初始化、健康检查等功能，减少代码重复
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import grpc

# 导入公共工具函数
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "server", "utils"))
from grpc_config import get_standard_grpc_options
from grpc_helpers import parse_grpc_address

logger = logging.getLogger(__name__)

# 重试策略：仅对可重试状态码重试，指数退避
RETRY_MAX_ATTEMPTS = 3
RETRY_INITIAL_BACKOFF_S = 0.1
RETRY_MAX_BACKOFF_S = 1.0
RETRY_BACKOFF_MULTIPLIER = 2.0
RETRYABLE_STATUS_CODES = (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)


class BaseGrpcClient:
    """
    gRPC 客户端基类
    
    提供公共的初始化、健康检查等功能
    子类只需要实现具体的业务方法
    使用 Channel 连接池复用连接，避免频繁创建/销毁带来的延迟
    """

    _channels: Dict[str, grpc.Channel] = {}
    _channel_lock = threading.Lock()

    @classmethod
    def get_channel(cls, address: str, options: List[Tuple[str, Any]]) -> grpc.Channel:
        """
        获取复用的 gRPC Channel，同一 address+options 共用一个 Channel。

        Args:
            address: 服务地址（如 "localhost:9001"）
            options: gRPC 配置选项列表

        Returns:
            grpc.Channel: 复用的 Channel
        """
        opt_tuple = tuple((k, v) for k, v in options)
        key = f"{address}:{hash(opt_tuple)}"
        if key not in cls._channels:
            with cls._channel_lock:
                if key not in cls._channels:
                    kwargs = {"options": options}
                    try:
                        from grpc_config import GRPC_COMPRESSION
                        if GRPC_COMPRESSION is not None:
                            kwargs["compression"] = GRPC_COMPRESSION
                    except Exception:
                        pass
                    cls._channels[key] = grpc.insecure_channel(address, **kwargs)
        return cls._channels[key]

    def __init__(
        self,
        service_name: str,
        env_key: str,
        default_port: int,
        base_url: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        初始化 gRPC 客户端
        
        Args:
            service_name: 服务名称（用于日志）
            env_key: 环境变量键名（如 "BAZI_CORE_SERVICE_URL"）
            default_port: 默认端口号
            base_url: 服务地址（可选，优先使用环境变量）
            timeout: 超时时间（秒）
        """
        # 获取服务地址
        base_url = base_url or os.getenv(env_key, "")
        if not base_url:
            raise RuntimeError(f"{env_key} is not configured")
        
        # 使用公共工具函数解析地址
        self.address = parse_grpc_address(base_url, default_port=default_port)
        self.timeout = timeout
        self.service_name = service_name
        self.env_key = env_key
        self.default_port = default_port
    
    def call_with_retry(
        self,
        rpc_call: Callable[[], Any],
        max_attempts: int = RETRY_MAX_ATTEMPTS,
        initial_backoff: float = RETRY_INITIAL_BACKOFF_S,
        max_backoff: float = RETRY_MAX_BACKOFF_S,
        backoff_multiplier: float = RETRY_BACKOFF_MULTIPLIER,
    ) -> Any:
        """
        执行 gRPC 调用并在 UNAVAILABLE/DEADLINE_EXCEEDED 时重试（指数退避）。
        """
        last_error = None
        backoff = initial_backoff
        for attempt in range(max_attempts):
            try:
                return rpc_call()
            except grpc.RpcError as e:
                last_error = e
                if e.code() not in RETRYABLE_STATUS_CODES or attempt == max_attempts - 1:
                    raise
                sleep_time = min(backoff, max_backoff)
                logger.warning(
                    "%s gRPC 调用失败 (attempt %d/%d): %s，%.2fs 后重试",
                    self.service_name, attempt + 1, max_attempts, e.code(), sleep_time,
                )
                time.sleep(sleep_time)
                backoff *= backoff_multiplier
        if last_error is not None:
            raise last_error
        raise RuntimeError("call_with_retry: unexpected state")

    def get_grpc_options(self, include_message_size: bool = False, max_message_size_mb: int = 50) -> list:
        """
        获取 gRPC 配置选项
        
        Args:
            include_message_size: 是否包含消息大小限制
            max_message_size_mb: 最大消息大小（MB）
        
        Returns:
            list: gRPC 配置选项列表
        """
        if include_message_size:
            from grpc_config import get_grpc_options_with_message_size
            return get_grpc_options_with_message_size(max_message_size_mb=max_message_size_mb)
        else:
            return get_standard_grpc_options()
    
    def health_check(self, stub_class, request_class) -> bool:
        """
        通用健康检查方法
        
        Args:
            stub_class: gRPC stub 类（如 bazi_core_pb2_grpc.BaziCoreServiceStub）
            request_class: 健康检查请求类（如 bazi_core_pb2.HealthCheckRequest）
        
        Returns:
            bool: 健康检查是否通过
        """
        request = request_class()
        try:
            options = self.get_grpc_options()
            channel = self.get_channel(self.address, options)
            stub = stub_class(channel)
            response = stub.HealthCheck(request, timeout=5.0)
            return response.status == "ok"
        except grpc.RpcError:
            logger.exception(f"{self.service_name} health check failed")
            return False
        except Exception as e:
            logger.exception(f"{self.service_name} health check error: {e}")
            return False
