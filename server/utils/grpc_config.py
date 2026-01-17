#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC 配置工具类
统一管理 gRPC 连接配置，避免在多个文件中重复配置
"""

from typing import List, Tuple


def get_standard_grpc_options() -> List[Tuple[str, int]]:
    """
    获取标准的 gRPC keepalive 配置选项
    
    这些配置用于避免 "Too many pings" 错误，优化连接性能
    
    Returns:
        List[Tuple[str, int]]: gRPC 配置选项列表
    """
    return [
        ('grpc.keepalive_time_ms', 300000),  # 5分钟，减少 ping 频率
        ('grpc.keepalive_timeout_ms', 20000),  # 20秒超时
        ('grpc.keepalive_permit_without_calls', False),  # 没有调用时不发送 ping
        ('grpc.http2.max_pings_without_data', 2),  # 允许最多2个 ping
        ('grpc.http2.min_time_between_pings_ms', 60000),  # ping 之间至少间隔60秒
    ]


def get_grpc_options_with_message_size(max_message_size_mb: int = 50) -> List[Tuple[str, int]]:
    """
    获取包含消息大小限制的 gRPC 配置选项
    
    Args:
        max_message_size_mb: 最大消息大小（MB），默认 50MB
    
    Returns:
        List[Tuple[str, int]]: gRPC 配置选项列表
    """
    options = get_standard_grpc_options()
    max_message_size_bytes = max_message_size_mb * 1024 * 1024
    options.extend([
        ('grpc.max_send_message_length', max_message_size_bytes),
        ('grpc.max_receive_message_length', max_message_size_bytes),
    ])
    return options
