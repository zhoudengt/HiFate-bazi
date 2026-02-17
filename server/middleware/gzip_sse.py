#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自定义中间件 - 从 server/main.py 提取"""

import gzip
import io
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

class SSEAwareGZipMiddleware(BaseHTTPMiddleware):
    """
    自定义 GZip 中间件，对 SSE (text/event-stream) 响应禁用压缩。
    SSE 流需要实时传输数据，gzip 压缩会导致浏览器无法正确读取流。
    """
    def __init__(self, app, minimum_size: int = 1000):
        super().__init__(app)
        self.minimum_size = minimum_size
    
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        
        # 检查是否是 SSE 响应，如果是则跳过压缩
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            return response
        
        # 检查响应头中是否已设置 Content-Encoding: identity
        if response.headers.get("content-encoding") == "identity":
            return response
        
        # 其他响应使用默认 GZip 压缩逻辑
        # 这里简化处理，不实现完整的 gzip 压缩
        # 交给 FastAPI 默认的 GZipMiddleware 处理
        return response
