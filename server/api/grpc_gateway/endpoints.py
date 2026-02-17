# -*- coding: utf-8 -*-
"""
gRPC-Web 端点注册表

供 grpc_gateway.py 和 handlers 共同使用，避免循环导入。
"""

import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

SUPPORTED_ENDPOINTS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}


def _register(endpoint: str):
    """装饰器：注册 endpoint -> handler"""

    def decorator(func: Callable[[Dict[str, Any]], Any]):
        SUPPORTED_ENDPOINTS[endpoint] = func
        logger.info(f"✅ 注册 gRPC 端点: {endpoint} (总端点数: {len(SUPPORTED_ENDPOINTS)})")
        return func

    return decorator
