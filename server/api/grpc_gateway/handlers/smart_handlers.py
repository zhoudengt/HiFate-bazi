# -*- coding: utf-8 -*-
"""
智能分析 gRPC-Web 端点处理器
"""

from typing import Any, Dict

from server.api.grpc_gateway.endpoints import _register
from server.api.v1.smart_fortune import smart_analyze, get_smart_analyze_stream_generator
from server.api.grpc_gateway.utils import _collect_sse_stream


@_register("/smart-analyze")
async def _handle_smart_analyze(payload: Dict[str, Any]):
    """处理智能分析请求（将 POST body 转换为 GET query 参数格式）"""
    question = payload.get("question", "")
    year = payload.get("year", 0)
    month = payload.get("month", 1)
    day = payload.get("day", 1)
    hour = payload.get("hour", 12)
    gender = payload.get("gender", "male")
    user_id = payload.get("user_id")
    include_fortune_context = payload.get("include_fortune_context", False)
    return await smart_analyze(
        question=question,
        year=year,
        month=month,
        day=day,
        hour=hour,
        gender=gender,
        user_id=user_id,
        include_fortune_context=include_fortune_context
    )


@_register("/smart-fortune/smart-analyze-stream")
async def _handle_smart_analyze_stream(payload: Dict[str, Any]):
    """处理智能运势流式分析请求（全量收集后返回单次 JSON）"""
    generator, error = await get_smart_analyze_stream_generator(payload)
    if error is not None:
        return error
    return await _collect_sse_stream(generator)
