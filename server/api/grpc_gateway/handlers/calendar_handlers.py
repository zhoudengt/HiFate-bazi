# -*- coding: utf-8 -*-
"""
日历与运势 gRPC-Web 端点处理器
"""

from typing import Any, Dict

from server.api.grpc_gateway.endpoints import _register
from server.api.v1.calendar_api import CalendarRequest, query_calendar
from server.api.v1.daily_fortune_calendar import (
    DailyFortuneCalendarRequest,
    daily_fortune_calendar_test,
)


@_register("/calendar/query")
async def _handle_calendar_query(payload: Dict[str, Any]):
    """处理万年历查询请求"""
    request_model = CalendarRequest(**payload)
    return await query_calendar(request_model)


@_register("/daily-fortune-calendar/test")
async def _handle_daily_fortune_calendar_test(payload: Dict[str, Any]):
    """处理每日运势日历测试接口请求"""
    request_model = DailyFortuneCalendarRequest(**payload)
    return await daily_fortune_calendar_test(request_model)


@_register("/daily-fortune-calendar/stream")
async def _handle_daily_fortune_calendar_stream(payload: Dict[str, Any]):
    """处理每日运势日历流式查询请求（gRPC-Web 转发）"""
    from server.api.v1.daily_fortune_calendar import daily_fortune_stream_generator
    from server.api.grpc_gateway.utils import _collect_sse_stream
    request_model = DailyFortuneCalendarRequest(**payload)
    generator = daily_fortune_stream_generator(request_model)
    return await _collect_sse_stream(generator)
