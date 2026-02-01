# -*- coding: utf-8 -*-
"""
Stream endpoint definitions for profiling.

Self-contained: no imports from server/scripts. Payload builders use simple defaults.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# Default test params (aligned with common bazi-style APIs)
DEFAULT_SOLAR_DATE = "1990-01-15"
DEFAULT_SOLAR_TIME = "12:00"
DEFAULT_GENDER = "male"
DEFAULT_CALENDAR_TYPE = "solar"


@dataclass
class StreamEndpoint:
    """Single stream endpoint definition."""
    name: str
    path: str
    method: str  # "GET" | "POST"
    payload_builder: Optional[Callable[[], Dict[str, Any]]] = None
    params_builder: Optional[Callable[[], Dict[str, Any]]] = None
    skip_reason: Optional[str] = None


def _bazi_payload() -> Dict[str, Any]:
    return {
        "solar_date": DEFAULT_SOLAR_DATE,
        "solar_time": DEFAULT_SOLAR_TIME,
        "gender": DEFAULT_GENDER,
        "calendar_type": DEFAULT_CALENDAR_TYPE,
    }


def _daily_fortune_payload() -> Dict[str, Any]:
    return {
        "date": None,
        "solar_date": DEFAULT_SOLAR_DATE,
        "solar_time": DEFAULT_SOLAR_TIME,
        "gender": DEFAULT_GENDER,
    }


def _annual_report_payload() -> Dict[str, Any]:
    return {
        "solar_date": DEFAULT_SOLAR_DATE,
        "solar_time": DEFAULT_SOLAR_TIME,
        "gender": DEFAULT_GENDER,
    }


def _smart_analyze_params() -> Dict[str, Any]:
    return {
        "year": 1990,
        "month": 1,
        "day": 15,
        "hour": 12,
        "gender": DEFAULT_GENDER,
        "category": "事业财富",
        "user_id": "stream_profiler_test",
    }


def _action_suggestions_payload() -> Dict[str, Any]:
    return {
        "yi": ["解除", "扫舍", "馀事勿取"],
        "ji": ["诸事不宜"],
    }


STREAM_ENDPOINTS: List[StreamEndpoint] = [
    StreamEndpoint(
        name="总评分析",
        path="/api/v1/general-review/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="事业财富",
        path="/api/v1/career-wealth/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="感情婚姻",
        path="/api/v1/bazi/marriage-analysis/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="健康分析",
        path="/api/v1/health/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="子女学习",
        path="/api/v1/children-study/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="五行占比",
        path="/api/v1/bazi/wuxing-proportion/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="喜神忌神",
        path="/api/v1/bazi/xishen-jishen/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="每日运势日历",
        path="/api/v1/daily-fortune-calendar/stream",
        method="POST",
        payload_builder=_daily_fortune_payload,
    ),
    StreamEndpoint(
        name="行动建议流式",
        path="/api/v1/daily-fortune-calendar/action-suggestions/stream",
        method="POST",
        payload_builder=_action_suggestions_payload,
    ),
    StreamEndpoint(
        name="年运报告",
        path="/api/v1/annual-report/stream",
        method="POST",
        payload_builder=_annual_report_payload,
    ),
    StreamEndpoint(
        name="智能分析流",
        path="/api/v1/smart-fortune/smart-analyze-stream",
        method="GET",
        params_builder=_smart_analyze_params,
    ),
    StreamEndpoint(
        name="办公桌风水(需图片)",
        path="/api/v2/desk-fengshui/analyze/stream",
        method="POST",
        skip_reason="需要上传图片",
    ),
    StreamEndpoint(
        name="面相分析V2(需图片)",
        path="/api/v2/face/analyze/stream",
        method="POST",
        skip_reason="需要上传图片",
    ),
    StreamEndpoint(
        name="手相分析(需图片)",
        path="/api/v1/fortune/hand/analyze/stream",
        method="POST",
        skip_reason="需要上传图片",
    ),
    StreamEndpoint(
        name="面相分析(需图片)",
        path="/api/v1/fortune/face/analyze/stream",
        method="POST",
        skip_reason="需要上传图片",
    ),
]


def get_endpoint_by_path(path: str) -> Optional[StreamEndpoint]:
    """Return the endpoint with the given path, or None."""
    path_stripped = path.rstrip("/")
    for ep in STREAM_ENDPOINTS:
        if ep.path.rstrip("/") == path_stripped:
            return ep
    return None


def get_endpoint_by_name(name: str) -> Optional[StreamEndpoint]:
    """Return the first endpoint with the given name, or None."""
    for ep in STREAM_ENDPOINTS:
        if ep.name == name:
            return ep
    return None
