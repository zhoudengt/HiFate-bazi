#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC 辅助工具函数
统一处理 gRPC 地址解析等公共逻辑
"""

from typing import Optional


def parse_grpc_address(base_url: Optional[str], default_port: int) -> str:
    """
    解析 gRPC 地址，统一处理地址格式
    
    支持以下格式：
    - "http://localhost:9001" -> "localhost:9001"
    - "https://localhost:9001" -> "localhost:9001"
    - "localhost:9001" -> "localhost:9001"
    - "localhost" -> "localhost:9001" (添加默认端口)
    
    Args:
        base_url: 基础 URL，可以是完整 URL 或 host:port 格式
        default_port: 默认端口号，如果 URL 中没有端口则使用此端口
    
    Returns:
        str: 解析后的地址，格式为 "host:port"
    
    Raises:
        ValueError: 如果 base_url 为空或无效
    """
    if not base_url:
        raise ValueError("base_url cannot be empty")
    
    # 移除 http:// 或 https:// 前缀
    if base_url.startswith("http://"):
        base_url = base_url[7:]
    elif base_url.startswith("https://"):
        base_url = base_url[8:]
    
    # 如果没有端口，添加默认端口
    if ":" not in base_url:
        base_url = f"{base_url}:{default_port}"
    
    return base_url
