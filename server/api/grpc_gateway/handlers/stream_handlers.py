# -*- coding: utf-8 -*-
"""
流式分析 gRPC-Web 端点处理器
"""

import importlib
import logging
import uuid
from typing import Any, Dict

from server.api.grpc_gateway.endpoints import _register
from server.api.grpc_gateway.utils import _collect_sse_stream
from server.api.v1.marriage_analysis import (
    MarriageAnalysisRequest,
    marriage_analysis_stream_generator,
)
from server.api.v1.career_wealth_analysis import (
    CareerWealthRequest,
    career_wealth_stream_generator,
)
from server.api.v1.children_study_analysis import (
    ChildrenStudyRequest,
    children_study_analysis_stream_generator,
)
from server.api.v1.health_analysis import (
    HealthAnalysisRequest,
    health_analysis_stream_generator,
)
from server.api.v1.general_review_analysis import (
    GeneralReviewRequest,
    general_review_analysis_stream_generator,
)
from server.api.v1.annual_report_analysis import (
    AnnualReportRequest,
    annual_report_debug,
    annual_report_stream_generator,
)

logger = logging.getLogger(__name__)


@_register("/career-wealth/test")
async def _handle_career_wealth_test(payload: Dict[str, Any]):
    """处理事业财富测试接口请求"""
    try:
        career_module = importlib.import_module('server.api.v1.career_wealth_analysis')
        importlib.reload(career_module)
        CareerWealthRequest = getattr(career_module, 'CareerWealthRequest')
        career_wealth_analysis_test = getattr(career_module, 'career_wealth_analysis_test')
        request_model = CareerWealthRequest(**payload)
        return await career_wealth_analysis_test(request_model)
    except Exception as e:
        logger.error(f"career_wealth_test 处理失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@_register("/career-wealth/debug")
async def _handle_career_wealth_debug(payload: Dict[str, Any]):
    """处理事业财富调试接口请求"""
    try:
        career_module = importlib.import_module('server.api.v1.career_wealth_analysis')
        importlib.reload(career_module)
        CareerWealthRequest = getattr(career_module, 'CareerWealthRequest')
        career_wealth_analysis_debug = getattr(career_module, 'career_wealth_analysis_debug')
        request_model = CareerWealthRequest(**payload)
        return await career_wealth_analysis_debug(request_model)
    except Exception as e:
        logger.error(f"career_wealth_debug 处理失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@_register("/bazi/marriage-analysis/stream")
async def _handle_marriage_analysis_stream(payload: Dict[str, Any]):
    """处理感情婚姻流式分析请求"""
    request_model = MarriageAnalysisRequest(**payload)
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[{trace_id}] 📥 收到婚姻分析请求: solar_date={request_model.solar_date}, gender={request_model.gender}")
    generator = marriage_analysis_stream_generator(
        request_model.solar_date, request_model.solar_time, request_model.gender,
        request_model.calendar_type, request_model.location,
        request_model.latitude, request_model.longitude,
        request_model.bot_id, trace_id=trace_id
    )
    return await _collect_sse_stream(generator)


@_register("/bazi/marriage-analysis/debug")
async def _handle_marriage_analysis_debug(payload: Dict[str, Any]):
    """处理感情婚姻调试接口请求"""
    try:
        marriage_module = importlib.import_module('server.api.v1.marriage_analysis')
        importlib.reload(marriage_module)
        MarriageAnalysisRequest = getattr(marriage_module, 'MarriageAnalysisRequest')
        marriage_analysis_debug = getattr(marriage_module, 'marriage_analysis_debug')
        request_model = MarriageAnalysisRequest(**payload)
        return await marriage_analysis_debug(request_model)
    except Exception as e:
        logger.error(f"marriage_analysis_debug 处理失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@_register("/career-wealth/stream")
async def _handle_career_wealth_stream(payload: Dict[str, Any]):
    """处理事业财富流式分析请求"""
    request_model = CareerWealthRequest(**payload)
    generator = career_wealth_stream_generator(
        request_model.solar_date, request_model.solar_time, request_model.gender,
        request_model.calendar_type, request_model.location,
        request_model.latitude, request_model.longitude, request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/children-study/stream")
async def _handle_children_study_stream(payload: Dict[str, Any]):
    """处理子女学习流式分析请求"""
    request_model = ChildrenStudyRequest(**payload)
    generator = children_study_analysis_stream_generator(
        request_model.solar_date, request_model.solar_time, request_model.gender,
        request_model.calendar_type, request_model.location,
        request_model.latitude, request_model.longitude, request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/children-study/debug")
async def _handle_children_study_debug(payload: Dict[str, Any]):
    """处理子女学习调试接口请求"""
    try:
        children_module = importlib.import_module('server.api.v1.children_study_analysis')
        importlib.reload(children_module)
        ChildrenStudyRequest = getattr(children_module, 'ChildrenStudyRequest')
        children_study_analysis_debug = getattr(children_module, 'children_study_analysis_debug')
        request_model = ChildrenStudyRequest(**payload)
        return await children_study_analysis_debug(request_model)
    except Exception as e:
        logger.error(f"children_study_debug 处理失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@_register("/health/stream")
async def _handle_health_stream(payload: Dict[str, Any]):
    """处理健康分析流式请求"""
    request_model = HealthAnalysisRequest(**payload)
    generator = health_analysis_stream_generator(
        request_model.solar_date, request_model.solar_time, request_model.gender,
        request_model.calendar_type, request_model.location,
        request_model.latitude, request_model.longitude, request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/health/debug")
async def _handle_health_debug(payload: Dict[str, Any]):
    """处理身体健康调试接口请求"""
    try:
        health_module = importlib.import_module('server.api.v1.health_analysis')
        importlib.reload(health_module)
        HealthAnalysisRequest = getattr(health_module, 'HealthAnalysisRequest')
        health_analysis_debug = getattr(health_module, 'health_analysis_debug')
        request_model = HealthAnalysisRequest(**payload)
        return await health_analysis_debug(request_model)
    except Exception as e:
        logger.error(f"health_debug 处理失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@_register("/general-review/stream")
async def _handle_general_review_stream(payload: Dict[str, Any]):
    """处理总评分析流式请求"""
    request_model = GeneralReviewRequest(**payload)
    generator = general_review_analysis_stream_generator(
        request_model.solar_date, request_model.solar_time, request_model.gender,
        request_model.calendar_type, request_model.location,
        request_model.latitude, request_model.longitude, request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/general-review/debug")
async def _handle_general_review_debug(payload: Dict[str, Any]):
    """处理总评调试接口请求"""
    try:
        general_module = importlib.import_module('server.api.v1.general_review_analysis')
        importlib.reload(general_module)
        GeneralReviewRequest = getattr(general_module, 'GeneralReviewRequest')
        general_review_analysis_debug = getattr(general_module, 'general_review_analysis_debug')
        request_model = GeneralReviewRequest(**payload)
        return await general_review_analysis_debug(request_model)
    except Exception as e:
        logger.error(f"general_review_debug 处理失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@_register("/annual-report/stream")
async def _handle_annual_report_stream(payload: Dict[str, Any]):
    """处理年运报告流式请求"""
    request_model = AnnualReportRequest(**payload)
    generator = annual_report_stream_generator(
        request_model.solar_date, request_model.solar_time,
        request_model.gender, request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/annual-report/debug")
async def _handle_annual_report_debug(payload: Dict[str, Any]):
    """处理年运报告调试接口请求"""
    request_model = AnnualReportRequest(**payload)
    return await annual_report_debug(request_model)


@_register("/annual-report/test")
async def _handle_annual_report_test(payload: Dict[str, Any]):
    """处理年运报告测试接口请求"""
    request_model = AnnualReportRequest(**payload)
    return await annual_report_debug(request_model)
