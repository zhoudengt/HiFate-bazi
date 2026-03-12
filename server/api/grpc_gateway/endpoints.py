# -*- coding: utf-8 -*-
"""
gRPC-Web 端点注册表

供 grpc_gateway.py 和 handlers 共同使用，避免循环导入。
"""

import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

SUPPORTED_ENDPOINTS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

# 热更新期间，将 @_register 写入重定向到这个临时 dict，避免清空 SUPPORTED_ENDPOINTS
_pending_endpoints: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None


@contextmanager
def _capture_registrations():
    """
    上下文管理器：在此 with 块内调用 @_register 会写入临时 dict 而非 SUPPORTED_ENDPOINTS。
    退出时返回收集到的端点（不自动写入 SUPPORTED_ENDPOINTS，由调用方决定）。

    用于热更新原子替换：先 capture，全部成功后再 swap。
    """
    global _pending_endpoints
    _pending_endpoints = {}
    try:
        yield _pending_endpoints
    finally:
        _pending_endpoints = None


def _register(endpoint: str):
    """装饰器：注册 endpoint -> handler（热更新期间写入临时 dict）"""

    def decorator(func: Callable[[Dict[str, Any]], Any]):
        target = _pending_endpoints if _pending_endpoints is not None else SUPPORTED_ENDPOINTS
        target[endpoint] = func
        logger.info(f"✅ 注册 gRPC 端点: {endpoint} (目标={'临时' if _pending_endpoints is not None else '生产'}, 总数: {len(target)})")
        return func

    return decorator
