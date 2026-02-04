#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC-Web 协议处理模块

提供 gRPC-Web 协议的编码、解码和响应构建功能。
"""

from .encoder import (
    encode_frontend_response,
    write_varint,
    wrap_frame,
)
from .decoder import (
    extract_grpc_web_message,
    decode_frontend_request,
    read_varint,
)
from .response import (
    build_grpc_web_response,
    build_error_response,
    map_http_to_grpc_status,
    grpc_cors_headers,
)

__all__ = [
    # 编码
    'encode_frontend_response',
    'write_varint',
    'wrap_frame',
    # 解码
    'extract_grpc_web_message',
    'decode_frontend_request',
    'read_varint',
    # 响应
    'build_grpc_web_response',
    'build_error_response',
    'map_http_to_grpc_status',
    'grpc_cors_headers',
]
