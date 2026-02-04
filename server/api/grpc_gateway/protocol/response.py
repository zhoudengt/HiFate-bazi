#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC-Web 响应构建模块

提供 gRPC-Web 响应构建和 CORS 头处理功能。
"""

import json
import urllib.parse
from typing import Dict

from fastapi import Response

from .encoder import encode_frontend_response, wrap_frame


def grpc_cors_headers(request_origin: str = None) -> Dict[str, str]:
    """
    返回 gRPC-Web 所需的 CORS 头（使用统一配置）
    
    Args:
        request_origin: 请求的 Origin 头（可选，用于动态 CORS）
    
    Returns:
        Dict[str, str]: CORS 响应头字典
    """
    try:
        from server.utils.cors_config import get_grpc_cors_headers
        return get_grpc_cors_headers(request_origin)
    except Exception:
        # 回退到默认配置（确保服务可用）
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": (
                "Content-Type, X-Grpc-Web, X-User-Agent, Accept, Authorization, "
                "X-Requested-With, X-Client-Version, grpc-timeout, "
                "x-grpc-web, x-requested-with"
            ),
            "Access-Control-Expose-Headers": "grpc-status, grpc-message, grpc-encoding, grpc-accept-encoding",
            "Access-Control-Max-Age": "86400",
        }


def map_http_to_grpc_status(status_code: int) -> int:
    """
    将 HTTP 状态码映射到 gRPC 状态码
    
    Args:
        status_code: HTTP 状态码
        
    Returns:
        int: 对应的 gRPC 状态码
    """
    mapping = {
        400: 3,   # INVALID_ARGUMENT
        401: 16,  # UNAUTHENTICATED
        403: 7,   # PERMISSION_DENIED
        404: 12,  # UNIMPLEMENTED
        422: 3,   # INVALID_ARGUMENT
    }
    return mapping.get(status_code, 13)  # 默认 INTERNAL


def build_grpc_web_response(message: bytes, grpc_status: int, grpc_message: str) -> Response:
    """
    构建 gRPC-Web 响应
    
    Args:
        message: protobuf 编码的消息
        grpc_status: gRPC 状态码
        grpc_message: gRPC 消息
        
    Returns:
        Response: FastAPI Response 对象
    """
    data_frame = wrap_frame(0x00, message)
    
    # grpc-message 在 trailer 中需要使用 URL 编码来支持非 ASCII 字符
    encoded_message = urllib.parse.quote(grpc_message, safe='')
    
    # trailer payload 使用 ASCII 编码（因为已经 URL 编码了）
    trailer_payload = f"grpc-status:{grpc_status}\r\ngrpc-message:{encoded_message}\r\n".encode(
        "ascii", errors="ignore"
    )
    trailer_frame = wrap_frame(0x80, trailer_payload)
    body = data_frame + trailer_frame

    headers = {
        **grpc_cors_headers(),
        "grpc-status": str(grpc_status),
        "grpc-message": encoded_message,
        "Content-Type": "application/grpc-web+proto",
    }

    return Response(content=body, media_type="application/grpc-web+proto", headers=headers)


def build_error_response(message: str, http_status: int, grpc_status: int) -> Response:
    """
    构建错误响应
    
    Args:
        message: 错误消息
        http_status: HTTP 状态码
        grpc_status: gRPC 状态码
        
    Returns:
        Response: FastAPI Response 对象
    """
    payload = encode_frontend_response(
        success=False,
        data_json=json.dumps({"detail": message}, ensure_ascii=False),
        error=message,
        status_code=http_status,
    )
    return build_grpc_web_response(payload, grpc_status, message)
