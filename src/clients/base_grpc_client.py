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
from typing import Optional

import grpc

# 导入公共工具函数
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "server", "utils"))
from grpc_config import get_standard_grpc_options
from grpc_helpers import parse_grpc_address

logger = logging.getLogger(__name__)


class BaseGrpcClient:
    """
    gRPC 客户端基类
    
    提供公共的初始化、健康检查等功能
    子类只需要实现具体的业务方法
    """
    
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
            with grpc.insecure_channel(self.address, options=options) as channel:
                stub = stub_class(channel)
                response = stub.HealthCheck(request, timeout=5.0)
                return response.status == "ok"
        except grpc.RpcError:
            logger.exception(f"{self.service_name} health check failed")
            return False
        except Exception as e:
            logger.exception(f"{self.service_name} health check error: {e}")
            return False
