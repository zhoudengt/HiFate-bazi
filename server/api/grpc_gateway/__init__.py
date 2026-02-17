#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC-Web 网关模块

这是项目的 gRPC-Web 网关，提供：
- 端点注册机制
- gRPC-Web 协议编解码
- 流式响应处理
- 热更新支持

⚠️ 兼容性说明：
原 grpc_gateway.py 已拆分为多个模块，此文件提供向后兼容的导出。
"""

# 从同级的 grpc_gateway.py 文件导入 router（用于向后兼容）
# 由于目录和文件同名，需要使用 importlib 显式加载
import importlib.util
import os

_module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'grpc_gateway.py')
_spec = importlib.util.spec_from_file_location("grpc_gateway_file", _module_path)
_grpc_gateway_file = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_grpc_gateway_file)

# 导出 router（热更新用）
router = _grpc_gateway_file.router

# 端点注册表（与 grpc_gateway.py 和 handlers 使用的 endpoints 一致）
from .endpoints import SUPPORTED_ENDPOINTS, _register

# 热更新恢复函数
from .recovery import _reload_endpoints, _ensure_endpoints_registered

# 协议编解码
from .protocol import (
    # 编码
    encode_frontend_response,
    write_varint,
    wrap_frame,
    # 解码
    extract_grpc_web_message,
    decode_frontend_request,
    read_varint,
    # 响应
    build_grpc_web_response,
    build_error_response,
    map_http_to_grpc_status,
    grpc_cors_headers,
)

# 端点注册（registry 为备用接口）
from .registry import (
    register,
    clear_endpoints,
    get_endpoint,
    list_endpoints,
    endpoint_count,
    is_endpoint_registered,
    register_endpoint,
    log_registered_endpoints,
)

__all__ = [
    # 向后兼容：从 grpc_gateway.py 导出
    'router',
    '_ensure_endpoints_registered',
    '_reload_endpoints',
    'SUPPORTED_ENDPOINTS',
    '_register',
    # 协议编解码
    'encode_frontend_response',
    'write_varint',
    'wrap_frame',
    'extract_grpc_web_message',
    'decode_frontend_request',
    'read_varint',
    'build_grpc_web_response',
    'build_error_response',
    'map_http_to_grpc_status',
    'grpc_cors_headers',
    # 端点注册
    'SUPPORTED_ENDPOINTS',
    'register',
    'clear_endpoints',
    'get_endpoint',
    'list_endpoints',
    'endpoint_count',
    'is_endpoint_registered',
    'register_endpoint',
    'log_registered_endpoints',
]
