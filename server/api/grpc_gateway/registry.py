#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC-Web 端点注册模块

提供端点注册、清理和热更新支持。
"""

import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

# 支持的前端接口列表（全局注册表）
SUPPORTED_ENDPOINTS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}


def register(endpoint: str):
    """
    装饰器：注册 endpoint -> handler
    
    Args:
        endpoint: 端点路径
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[[Dict[str, Any]], Any]):
        SUPPORTED_ENDPOINTS[endpoint] = func
        logger.info(f"✅ 注册 gRPC 端点: {endpoint} (总端点数: {len(SUPPORTED_ENDPOINTS)})")
        return func
    return decorator


def clear_endpoints():
    """清空已注册的端点（用于热更新）"""
    global SUPPORTED_ENDPOINTS
    SUPPORTED_ENDPOINTS.clear()
    logger.info("已清空 gRPC 端点注册表（热更新）")


def get_endpoint(endpoint: str) -> Callable[[Dict[str, Any]], Any] | None:
    """
    获取指定端点的处理函数
    
    Args:
        endpoint: 端点路径
        
    Returns:
        处理函数或 None
    """
    return SUPPORTED_ENDPOINTS.get(endpoint)


def list_endpoints() -> list:
    """
    列出所有已注册的端点
    
    Returns:
        端点路径列表
    """
    return list(SUPPORTED_ENDPOINTS.keys())


def endpoint_count() -> int:
    """
    获取已注册的端点数量
    
    Returns:
        端点数量
    """
    return len(SUPPORTED_ENDPOINTS)


def is_endpoint_registered(endpoint: str) -> bool:
    """
    检查端点是否已注册
    
    Args:
        endpoint: 端点路径
        
    Returns:
        是否已注册
    """
    return endpoint in SUPPORTED_ENDPOINTS


def register_endpoint(endpoint: str, handler: Callable[[Dict[str, Any]], Any]):
    """
    手动注册端点（用于热更新后恢复）
    
    Args:
        endpoint: 端点路径
        handler: 处理函数
    """
    SUPPORTED_ENDPOINTS[endpoint] = handler
    logger.info(f"✅ 手动注册 gRPC 端点: {endpoint} (总端点数: {len(SUPPORTED_ENDPOINTS)})")


def log_registered_endpoints():
    """记录已注册的端点（调试用）"""
    if SUPPORTED_ENDPOINTS:
        logger.info(f"已注册的 gRPC 端点数量: {len(SUPPORTED_ENDPOINTS)}")
        logger.debug(f"已注册的端点列表: {list(SUPPORTED_ENDPOINTS.keys())}")
