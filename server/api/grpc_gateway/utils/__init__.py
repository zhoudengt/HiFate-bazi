# -*- coding: utf-8 -*-
"""
gRPC-Web 网关工具模块
"""

from .stream_collector import collect_sse_stream
from .serialization import deep_clean_for_serialization

# 向后兼容：保持 _ 前缀别名
_collect_sse_stream = collect_sse_stream
_deep_clean_for_serialization = deep_clean_for_serialization

__all__ = ['collect_sse_stream', 'deep_clean_for_serialization', '_collect_sse_stream', '_deep_clean_for_serialization']
