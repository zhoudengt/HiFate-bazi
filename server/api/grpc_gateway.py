#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端 gRPC-Web 网关

- 接收浏览器 gRPC-Web 请求
- 解包通用 JSON 载荷
- 调用现有 FastAPI/Pydantic 处理逻辑
- 返回与原 REST 接口一致的 JSON 数据
"""

from __future__ import annotations

import json
from json import JSONDecodeError
import logging
import os
import uuid
from typing import Any, Callable, Dict, Tuple

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder

# 获取项目根目录（兼容本地和生产环境）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEBUG_LOG_PATH = os.path.join(PROJECT_ROOT, 'logs', 'debug.log')

# 认证相关代码已移除
from server.api.v1.bazi_display import (
    BaziDisplayRequest,
    DayunDisplayRequest,
    FortuneDisplayRequest,
    LiunianDisplayRequest,
    LiuyueDisplayRequest,
    get_dayun_display,
    get_fortune_display,
    get_liunian_display,
    get_liuyue_display,
    get_pan_display,
)
from server.api.v1.wangshuai import WangShuaiRequest, calculate_wangshuai
from server.api.v1.yigua import YiGuaRequest, divinate
from server.api.v1.payment import (
    CreatePaymentSessionRequest,
    VerifyPaymentRequest,
    create_payment_session,
    verify_payment,
)
from server.api.v1.smart_fortune import smart_analyze
from server.api.v1.formula_analysis import (
    FormulaAnalysisRequest,
    analyze_formula_rules,
)
from server.api.v1.daily_fortune import (
    DailyFortuneRequest,
    get_daily_fortune,
)
from server.api.v1.monthly_fortune import (
    MonthlyFortuneRequest,
    calculate_monthly_fortune,
)
from server.api.v1.unified_payment import (
    CreatePaymentRequest,
    VerifyPaymentRequest,
    create_unified_payment,
    verify_unified_payment,
    get_payment_providers,
)
from server.api.v1.calendar_api import (
    CalendarRequest,
    query_calendar,
)
from server.api.v1.daily_fortune_calendar import (
    DailyFortuneCalendarRequest,
    query_daily_fortune_calendar,
    daily_fortune_calendar_test,
)
from server.api.v1.bazi import (
    BaziInterfaceRequest, 
    ShengongMinggongRequest, 
    get_shengong_minggong,
    process_date_time_input
)
from server.utils.bazi_input_processor import BaziInputProcessor
try:
    from server.api.v1.rizhu_liujiazi import RizhuLiujiaziRequest, get_rizhu_liujiazi
    RIZHU_LIUJIAZI_AVAILABLE = True
except ImportError as e:
    import logging
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"⚠️  无法导入 rizhu_liujiazi 模块: {e}")
    RIZHU_LIUJIAZI_AVAILABLE = False
    # 创建占位符以避免 NameError
    RizhuLiujiaziRequest = None
    get_rizhu_liujiazi = None
from server.api.v1.wuxing_proportion import (
    WuxingProportionRequest,
    get_wuxing_proportion,
    wuxing_proportion_test,
)
from server.api.v1.xishen_jishen import (
    XishenJishenRequest,
    get_xishen_jishen,
    xishen_jishen_test,
)
from server.services.bazi_interface_service import BaziInterfaceService

# 流式接口导入
from server.api.v1.wuxing_proportion import (
    wuxing_proportion_stream_generator,
)
from server.api.v1.xishen_jishen import (
    xishen_jishen_stream_generator,
)
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
    annual_report_stream_generator,
)

# 文件上传相关
import base64
from io import BytesIO
from fastapi import UploadFile, File, Form

logger = logging.getLogger(__name__)
router = APIRouter()

# 在模块加载时打印已注册的端点（调试用）
def _log_registered_endpoints():
    """在模块加载完成后打印已注册的端点"""
    import atexit
    def log_on_exit():
        if SUPPORTED_ENDPOINTS:
            logger.info(f"已注册的 gRPC 端点数量: {len(SUPPORTED_ENDPOINTS)}")
            logger.debug(f"已注册的端点列表: {list(SUPPORTED_ENDPOINTS.keys())}")
    atexit.register(log_on_exit)


GrpcResult = Tuple[Dict[str, Any], int]

# 支持的前端接口列表
SUPPORTED_ENDPOINTS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}


def _clear_endpoints():
    """清空已注册的端点（用于热更新）"""
    global SUPPORTED_ENDPOINTS
    SUPPORTED_ENDPOINTS.clear()
    logger.info("已清空 gRPC 端点注册表（热更新）")


def _reload_endpoints():
    """重新注册所有端点（用于热更新后恢复端点）"""
    global SUPPORTED_ENDPOINTS
    # ⚠️ 重要：热更新时，装饰器 @_register 会在模块重新加载时执行
    # 但为了确保端点正确注册，我们需要：
    # 1. 先清空旧端点（避免残留）
    # 2. 重新导入模块以触发装饰器执行
    # 3. 验证端点数量
    
    # 记录当前端点数量（用于对比）
    old_count = len(SUPPORTED_ENDPOINTS)
    
    # 清空端点（热更新时会自动重新注册）
    SUPPORTED_ENDPOINTS.clear()
    logger.info(f"已清空 gRPC 端点注册表（旧端点数: {old_count}）")
    
    # 重新导入模块以触发装饰器执行
    try:
        import importlib
        import sys
        
        # ⭐ 关键修复：重新加载模块前，先确保模块在 sys.modules 中
        # 如果模块不在 sys.modules 中，装饰器不会执行
        if 'server.api.grpc_gateway' not in sys.modules:
            import server.api.grpc_gateway
        
        # 重新加载模块（触发装饰器 @_register 重新执行）
        gateway_module = sys.modules['server.api.grpc_gateway']
        importlib.reload(gateway_module)
        
        # ⭐ 关键修复：重新加载后，装饰器应该已经执行
        # 但如果端点仍未注册，手动重新注册关键端点
        endpoint_count = len(SUPPORTED_ENDPOINTS)
        logger.info(f"重新加载后端点数量: {endpoint_count}")
        
        # 如果端点数量为0或缺少关键端点，手动重新注册
        key_endpoints = ['/bazi/interface', '/bazi/shengong-minggong', '/bazi/rizhu-liujiazi']
        missing = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
        
        if endpoint_count == 0 or missing:
            logger.warning(f"⚠️  端点未正确注册（总数: {endpoint_count}, 缺失: {missing}），尝试手动注册...")
            
            # 手动重新注册关键端点
            try:
                # 重新导入关键函数
                from server.api.v1.bazi import BaziInterfaceRequest, ShengongMinggongRequest, get_shengong_minggong
                from server.services.bazi_interface_service import BaziInterfaceService
                
                # 手动注册 /bazi/interface
                async def _handle_bazi_interface(payload: Dict[str, Any]):
                    import asyncio
                    request_model = BaziInterfaceRequest(**payload)
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        BaziInterfaceService.generate_interface_full,
                        request_model.solar_date,
                        request_model.solar_time,
                        request_model.gender,
                        request_model.name or "",
                        request_model.location or "未知地",
                        request_model.latitude or 39.00,
                        request_model.longitude or 120.00
                    )
                    return {"success": True, "data": result}
                
                # 手动注册 /bazi/shengong-minggong
                async def _handle_shengong_minggong(payload: Dict[str, Any]):
                    from fastapi import Request
                    from unittest.mock import MagicMock
                    request_model = ShengongMinggongRequest(**payload)
                    mock_request = MagicMock(spec=Request)
                    result = await get_shengong_minggong(request_model, mock_request)
                    if hasattr(result, 'model_dump'):
                        return result.model_dump()
                    elif hasattr(result, 'dict'):
                        return result.dict()
                    return result
                
                # 手动注册 /bazi/rizhu-liujiazi 端点
                from server.api.v1.rizhu_liujiazi import (
                    RizhuLiujiaziRequest,
                    get_rizhu_liujiazi,
                )
                async def _handle_rizhu_liujiazi_reload(payload: Dict[str, Any]):
                    """处理日元-六十甲子查询请求（热更新后重新注册）"""
                    request_model = RizhuLiujiaziRequest(**payload)
                    return await get_rizhu_liujiazi(request_model)
                
                # 注册到 SUPPORTED_ENDPOINTS
                SUPPORTED_ENDPOINTS['/bazi/interface'] = _handle_bazi_interface
                SUPPORTED_ENDPOINTS['/bazi/shengong-minggong'] = _handle_shengong_minggong
                SUPPORTED_ENDPOINTS['/bazi/rizhu-liujiazi'] = _handle_rizhu_liujiazi_reload
                
                logger.info(f"✅ 手动注册关键端点成功（包含 /bazi/rizhu-liujiazi）")
            except Exception as e:
                logger.error(f"❌ 手动注册端点失败: {e}", exc_info=True)
        
        # 重新获取端点数量
        endpoint_count = len(SUPPORTED_ENDPOINTS)
        logger.info(f"✅ gRPC 端点已重新注册，当前端点数量: {endpoint_count}")
        
        if endpoint_count > 0:
            logger.debug(f"已注册的端点: {list(SUPPORTED_ENDPOINTS.keys())[:10]}...")
            # 验证关键端点
            key_endpoints = ['/bazi/interface', '/bazi/shengong-minggong', '/bazi/rizhu-liujiazi']
            missing = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
            if missing:
                logger.warning(f"⚠️  关键端点未注册: {missing}")
            else:
                logger.info(f"✅ 关键端点验证通过: {key_endpoints}")
        else:
            logger.error("❌ 端点重新注册后数量为0，可能存在模块加载问题")
        
        return endpoint_count > 0
    except Exception as e:
        logger.error(f"❌ gRPC 端点重新注册失败: {e}", exc_info=True)
        return False


def _register(endpoint: str):
    """装饰器：注册 endpoint -> handler"""

    def decorator(func: Callable[[Dict[str, Any]], Any]):
        SUPPORTED_ENDPOINTS[endpoint] = func
        logger.info(f"✅ 注册 gRPC 端点: {endpoint} (总端点数: {len(SUPPORTED_ENDPOINTS)})")
        return func

    return decorator


@_register("/bazi/pan/display")
async def _handle_pan(payload: Dict[str, Any]):
    request_model = BaziDisplayRequest(**payload)
    return await get_pan_display(request_model)


@_register("/bazi/fortune/display")
async def _handle_fortune(payload: Dict[str, Any]):
    """处理大运流年流月展示请求（gRPC-Web 转发）"""
    # ✅ 特殊处理：在创建 Pydantic 模型前处理 "今" 参数
    use_jin_mode = False
    if payload.get('current_time') == "今":
        from datetime import datetime
        use_jin_mode = True
        payload['current_time'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 创建请求模型对象（此时 current_time 已经是时间字符串，不会触发验证错误）
    request_model = FortuneDisplayRequest(**payload)
    
    # ✅ 调用内部处理函数（复用 get_fortune_display 的逻辑）
    from server.services.bazi_display_service import BaziDisplayService
    from server.utils.bazi_input_processor import BaziInputProcessor
    from datetime import datetime
    
    # 处理农历输入和时区转换
    final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
        request_model.solar_date,
        request_model.solar_time,
        request_model.calendar_type or "solar",
        request_model.location,
        request_model.latitude,
        request_model.longitude
    )
    
    # 解析 current_time（如果使用"今"模式，使用当前时间；否则解析时间字符串）
    current_time = None
    if request_model.current_time:
        if use_jin_mode:
            current_time = datetime.now()
        else:
            try:
                current_time = datetime.strptime(request_model.current_time, "%Y-%m-%d %H:%M")
            except ValueError:
                raise ValueError(f"current_time 参数格式错误: {request_model.current_time}")
    
    # 调用服务层
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    executor = ThreadPoolExecutor(max_workers=100)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        BaziDisplayService.get_fortune_display,
        final_solar_date,
        final_solar_time,
        request_model.gender,
        current_time,
        request_model.dayun_index,
        request_model.dayun_year_start,
        request_model.dayun_year_end,
        request_model.target_year,
        request_model.quick_mode if request_model.quick_mode is not None else True,
        request_model.async_warmup if request_model.async_warmup is not None else True
    )
    
    # 添加转换信息
    if result.get('success') and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
        result['conversion_info'] = conversion_info
    
    return result


@_register("/bazi/dayun/display")
async def _handle_dayun(payload: Dict[str, Any]):
    request_model = DayunDisplayRequest(**payload)
    return await get_dayun_display(request_model)


@_register("/bazi/liunian/display")
async def _handle_liunian(payload: Dict[str, Any]):
    request_model = LiunianDisplayRequest(**payload)
    return await get_liunian_display(request_model)


@_register("/bazi/liuyue/display")
async def _handle_liuyue(payload: Dict[str, Any]):
    request_model = LiuyueDisplayRequest(**payload)
    return await get_liuyue_display(request_model)


@_register("/bazi/wangshuai")
async def _handle_wangshuai(payload: Dict[str, Any]):
    request_model = WangShuaiRequest(**payload)
    return await calculate_wangshuai(request_model)


@_register("/bazi/yigua/divinate")
async def _handle_yigua(payload: Dict[str, Any]):
    request_model = YiGuaRequest(**payload)
    return await divinate(request_model)


@_register("/auth/login")
async def _handle_login(payload: Dict[str, Any]):
    """处理登录请求"""
    from server.api.v1.auth import LoginRequest, login
    request_model = LoginRequest(**payload)
    return await login(request_model)


@_register("/payment/create-session")
async def _handle_payment_create(payload: Dict[str, Any]):
    request_model = CreatePaymentSessionRequest(**payload)
    return create_payment_session(request_model)


@_register("/payment/verify")
async def _handle_payment_verify(payload: Dict[str, Any]):
    request_model = VerifyPaymentRequest(**payload)
    return verify_payment(request_model)


@_register("/smart-analyze")
async def _handle_smart_analyze(payload: Dict[str, Any]):
    """处理智能分析请求（将 POST body 转换为 GET query 参数格式）"""
    # smart_analyze 是 GET 接口，需要将 payload 转换为函数参数
    question = payload.get("question", "")
    year = payload.get("year", 0)
    month = payload.get("month", 1)
    day = payload.get("day", 1)
    hour = payload.get("hour", 12)
    gender = payload.get("gender", "male")
    user_id = payload.get("user_id")
    include_fortune_context = payload.get("include_fortune_context", False)
    
    # 调用原函数（需要手动传递参数，因为它是 GET 接口）
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


@_register("/bazi/formula-analysis")
async def _handle_formula_analysis(payload: Dict[str, Any]):
    """处理算法公式分析请求"""
    request_model = FormulaAnalysisRequest(**payload)
    return await analyze_formula_rules(request_model)


@_register("/bazi/daily-fortune")
async def _handle_daily_fortune(payload: Dict[str, Any]):
    """处理今日运势分析请求"""
    request_model = DailyFortuneRequest(**payload)
    return await get_daily_fortune(request_model)


@_register("/bazi/monthly-fortune")
async def _handle_monthly_fortune(payload: Dict[str, Any]):
    """处理当月运势分析请求"""
    request_model = MonthlyFortuneRequest(**payload)
    return await calculate_monthly_fortune(request_model)


@_register("/bazi/interface")
async def _handle_bazi_interface(payload: Dict[str, Any]):
    """处理八字界面信息请求（包含命宫、身宫、胎元、胎息、命卦等）"""
    import asyncio
    request_model = BaziInterfaceRequest(**payload)
    
    # 处理农历输入和时区转换
    final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
        request_model.solar_date,
        request_model.solar_time,
        request_model.calendar_type or "solar",
        request_model.location,
        request_model.latitude,
        request_model.longitude
    )
    
    # 在线程池中执行CPU密集型计算
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,  # 使用默认线程池
        BaziInterfaceService.generate_interface_full,
        final_solar_date,
        final_solar_time,
        request_model.gender,
        request_model.name or "",
        request_model.location or "未知地",
        request_model.latitude or 39.00,
        request_model.longitude or 120.00
    )
    
    # 添加转换信息到结果
    if conversion_info.get('converted') or conversion_info.get('timezone_info'):
        result['conversion_info'] = conversion_info
    
    # 返回格式与 REST API 一致
    return {
        "success": True,
        "data": result
    }


@_register("/bazi/shengong-minggong")
async def _handle_shengong_minggong(payload: Dict[str, Any]):
    """处理身宫命宫详细信息请求"""
    from fastapi import Request
    from unittest.mock import MagicMock
    
    request_model = ShengongMinggongRequest(**payload)
    # 创建一个模拟的Request对象（gRPC网关不需要真实的Request）
    mock_request = MagicMock(spec=Request)
    result = await get_shengong_minggong(request_model, mock_request)
    
    # 处理 BaziResponse 对象
    if hasattr(result, 'model_dump'):
        return result.model_dump()
    elif hasattr(result, 'dict'):
        return result.dict()
    return result


# 只有在模块可用时才注册端点
if RIZHU_LIUJIAZI_AVAILABLE:
    @_register("/bazi/rizhu-liujiazi")
    async def _handle_rizhu_liujiazi(payload: Dict[str, Any]):
        """处理日元-六十甲子查询请求"""
        request_model = RizhuLiujiaziRequest(**payload)
        return await get_rizhu_liujiazi(request_model)
else:
    logger.warning("⚠️  /bazi/rizhu-liujiazi 端点未注册（模块不可用）")


@_register("/bazi/data")
async def _handle_bazi_data(payload: Dict[str, Any]):
    """处理统一数据获取请求"""
    from server.api.v1.bazi_data import BaziDataRequest, get_bazi_data
    request_model = BaziDataRequest(**payload)
    return await get_bazi_data(request_model)


@_register("/bazi/xishen-jishen")
async def _handle_xishen_jishen(payload: Dict[str, Any]):
    """处理喜神忌神查询请求"""
    request_model = XishenJishenRequest(**payload)
    return await get_xishen_jishen(request_model)


@_register("/bazi/wuxing-proportion")
async def _handle_wuxing_proportion(payload: Dict[str, Any]):
    """处理五行占比查询请求"""
    request_model = WuxingProportionRequest(**payload)
    return await get_wuxing_proportion(request_model)


@_register("/bazi/wuxing-proportion/test")
async def _handle_wuxing_proportion_test(payload: Dict[str, Any]):
    """处理五行占比测试接口请求"""
    request_model = WuxingProportionRequest(**payload)
    return await wuxing_proportion_test(request_model)


@_register("/bazi/wuxing-proportion/stream")
async def _handle_wuxing_proportion_stream(payload: Dict[str, Any]):
    """处理五行占比流式分析请求（gRPC-Web 转发）"""
    request_model = WuxingProportionRequest(**payload)
    generator = wuxing_proportion_stream_generator(request_model)
    return await _collect_sse_stream(generator)


@_register("/bazi/xishen-jishen/test")
async def _handle_xishen_jishen_test(payload: Dict[str, Any]):
    """处理喜神忌神测试接口请求"""
    request_model = XishenJishenRequest(**payload)
    return await xishen_jishen_test(request_model)


@_register("/bazi/xishen-jishen/stream")
async def _handle_xishen_jishen_stream(payload: Dict[str, Any]):
    """处理喜神忌神流式分析请求（gRPC-Web 转发）"""
    request_model = XishenJishenRequest(**payload)
    generator = xishen_jishen_stream_generator(request_model)
    return await _collect_sse_stream(generator)


@_register("/career-wealth/test")
async def _handle_career_wealth_test(payload: Dict[str, Any]):
    """处理事业财富测试接口请求（使用动态导入确保获取最新代码）"""
    import importlib
    try:
        # 动态重新导入模块以获取最新代码
        career_module = importlib.import_module('server.api.v1.career_wealth_analysis')
        importlib.reload(career_module)
        
        # 获取请求模型和处理函数
        CareerWealthRequest = getattr(career_module, 'CareerWealthRequest')
        career_wealth_analysis_test = getattr(career_module, 'career_wealth_analysis_test')
        
        request_model = CareerWealthRequest(**payload)
        return await career_wealth_analysis_test(request_model)
    except Exception as e:
        logger.error(f"career_wealth_test 处理失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@_register("/bazi/marriage-analysis/stream")
async def _handle_marriage_analysis_stream(payload: Dict[str, Any]):
    """处理感情婚姻流式分析请求（gRPC-Web 转发）"""
    request_model = MarriageAnalysisRequest(**payload)
    # 生成 trace_id 用于请求追踪
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[{trace_id}] 📥 收到婚姻分析请求: solar_date={request_model.solar_date}, gender={request_model.gender}")
    generator = marriage_analysis_stream_generator(
        request_model.solar_date,
        request_model.solar_time,
        request_model.gender,
        request_model.calendar_type,
        request_model.location,
        request_model.latitude,
        request_model.longitude,
        request_model.bot_id,
        trace_id=trace_id
    )
    return await _collect_sse_stream(generator)


@_register("/career-wealth/stream")
async def _handle_career_wealth_stream(payload: Dict[str, Any]):
    """处理事业财富流式分析请求（gRPC-Web 转发）"""
    request_model = CareerWealthRequest(**payload)
    generator = career_wealth_stream_generator(
        request_model.solar_date,
        request_model.solar_time,
        request_model.gender,
        request_model.calendar_type,
        request_model.location,
        request_model.latitude,
        request_model.longitude,
        request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/children-study/stream")
async def _handle_children_study_stream(payload: Dict[str, Any]):
    """处理子女学习流式分析请求（gRPC-Web 转发）"""
    request_model = ChildrenStudyRequest(**payload)
    generator = children_study_analysis_stream_generator(
        request_model.solar_date,
        request_model.solar_time,
        request_model.gender,
        request_model.calendar_type,
        request_model.location,
        request_model.latitude,
        request_model.longitude,
        request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/health/stream")
async def _handle_health_stream(payload: Dict[str, Any]):
    """处理健康分析流式请求（gRPC-Web 转发）"""
    request_model = HealthAnalysisRequest(**payload)
    generator = health_analysis_stream_generator(
        request_model.solar_date,
        request_model.solar_time,
        request_model.gender,
        request_model.calendar_type,
        request_model.location,
        request_model.latitude,
        request_model.longitude,
        request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/general-review/stream")
async def _handle_general_review_stream(payload: Dict[str, Any]):
    """处理总评分析流式请求（gRPC-Web 转发）"""
    request_model = GeneralReviewRequest(**payload)
    generator = general_review_analysis_stream_generator(
        request_model.solar_date,
        request_model.solar_time,
        request_model.gender,
        request_model.calendar_type,
        request_model.location,
        request_model.latitude,
        request_model.longitude,
        request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/annual-report/stream")
async def _handle_annual_report_stream(payload: Dict[str, Any]):
    """处理年运报告流式请求（gRPC-Web 转发）"""
    request_model = AnnualReportRequest(**payload)
    generator = annual_report_stream_generator(
        request_model.solar_date,
        request_model.solar_time,
        request_model.gender,
        request_model.bot_id
    )
    return await _collect_sse_stream(generator)


@_register("/smart-fortune/smart-analyze-stream")
async def _handle_smart_analyze_stream(payload: Dict[str, Any]):
    """处理智能运势流式分析请求（gRPC-Web 转发）
    
    注意：原接口是 GET 请求，通过 query params 传参
    这里转换为 POST body 传参
    """
    from server.api.v1.smart_fortune import (
        _scenario_1_generator,
        _scenario_2_generator,
        _original_scenario_generator,
        PerformanceMonitor,
        _sse_message,
    )
    
    # 从 payload 提取参数
    question = payload.get("question")
    year = payload.get("year")
    month = payload.get("month")
    day = payload.get("day")
    hour = payload.get("hour", 12)
    gender = payload.get("gender")
    user_id = payload.get("user_id")
    category = payload.get("category")
    
    # 初始化性能监控器
    monitor = PerformanceMonitor()
    
    # 场景判断
    is_scenario_1 = category and (not question or question == category)
    is_scenario_2 = category and question and question != category
    
    # 根据场景选择生成器
    if is_scenario_1:
        if not user_id or not year or not month or not day or not gender:
            return {"success": False, "error": "场景1需要提供完整的生辰信息（year, month, day, gender, user_id）"}
        generator = _scenario_1_generator(year, month, day, hour, gender, category, user_id, monitor)
    elif is_scenario_2:
        if not user_id:
            return {"success": False, "error": "场景2需要提供user_id参数"}
        generator = _scenario_2_generator(question, category, user_id, year, month, day, hour, gender, monitor)
    elif question and year and month and day and gender:
        generator = _original_scenario_generator(question, year, month, day, hour, gender, user_id, monitor)
    else:
        return {"success": False, "error": "参数不完整，请检查输入"}
    
    return await _collect_sse_stream(generator)


@_register("/payment/unified/create")
async def _handle_unified_payment_create(payload: Dict[str, Any]):
    """处理统一支付创建请求"""
    request_model = CreatePaymentRequest(**payload)
    return create_unified_payment(request_model)


@_register("/payment/unified/verify")
async def _handle_unified_payment_verify(payload: Dict[str, Any]):
    """处理统一支付验证请求"""
    request_model = VerifyPaymentRequest(**payload)
    return verify_unified_payment(request_model)


@_register("/payment/providers")
async def _handle_payment_providers(payload: Dict[str, Any]):
    """处理获取支付渠道列表请求（GET 转 POST）"""
    # payment/providers 是 GET 接口，但 gRPC-Web 只支持 POST
    # 这里忽略 payload，直接调用原函数
    return get_payment_providers()


@_register("/calendar/query")
async def _handle_calendar_query(payload: Dict[str, Any]):
    """处理万年历查询请求"""
    request_model = CalendarRequest(**payload)
    return await query_calendar(request_model)


@_register("/daily-fortune-calendar/query")
async def _handle_daily_fortune_calendar_query(payload: Dict[str, Any]):
    """处理每日运势日历查询请求"""
    # ⚠️ 重要：DailyFortuneCalendarRequest 的所有字段都是可选的
    # 未登录用户只需要提供 date 参数
    request_model = DailyFortuneCalendarRequest(**payload)
    return await query_daily_fortune_calendar(request_model)


@_register("/daily-fortune-calendar/test")
async def _handle_daily_fortune_calendar_test(payload: Dict[str, Any]):
    """处理每日运势日历测试接口请求"""
    request_model = DailyFortuneCalendarRequest(**payload)
    return await daily_fortune_calendar_test(request_model)


@_register("/daily-fortune-calendar/stream")
async def _handle_daily_fortune_calendar_stream(payload: Dict[str, Any]):
    """处理每日运势日历流式查询请求"""
    from server.api.v1.daily_fortune_calendar import query_daily_fortune_calendar_stream
    request_model = DailyFortuneCalendarRequest(**payload)
    return await query_daily_fortune_calendar_stream(request_model)


@_register("/api/v2/face/analyze")
async def _handle_face_analysis_v2(payload: Dict[str, Any]):
    """处理面相分析V2请求（支持文件上传）"""
    from server.api.v2.face_analysis import analyze_face
    from fastapi.responses import JSONResponse
    
    # 处理 base64 编码的图片
    image_base64 = payload.get("image_base64", "")
    if not image_base64:
        raise HTTPException(status_code=400, detail="缺少图片数据")
    
    # 解码 base64
    try:
        # 移除 data:image/xxx;base64, 前缀（如果有）
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        image_bytes = base64.b64decode(image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片解码失败: {str(e)}")
    
    # 创建 UploadFile 对象
    image_file = UploadFile(
        file=BytesIO(image_bytes),
        filename=payload.get("filename", "face.jpg"),
        headers={"content-type": payload.get("content_type", "image/jpeg")}
    )
    
    # 调用原始接口
    result = await analyze_face(
        image=image_file,
        analysis_types=payload.get("analysis_types", "gongwei,liuqin,shishen"),
        birth_year=payload.get("birth_year"),
        birth_month=payload.get("birth_month"),
        birth_day=payload.get("birth_day"),
        birth_hour=payload.get("birth_hour"),
        gender=payload.get("gender")
    )
    
    # JSONResponse 对象需要提取 body 内容
    if isinstance(result, JSONResponse):
        body = result.body
        if isinstance(body, bytes):
            data = json.loads(body.decode('utf-8'))
        else:
            data = body
        # 深度清理，确保可以序列化（修复 Maximum call stack exceeded）
        return _deep_clean_for_serialization(data)
    
    return result


@_register("/api/v2/desk-fengshui/analyze")
async def _handle_desk_fengshui(payload: Dict[str, Any]):
    """处理办公桌风水分析请求（支持文件上传）"""
    
    from server.api.v2.desk_fengshui_api import analyze_desk_fengshui
    from fastapi.responses import JSONResponse
    
    # 处理 base64 编码的图片
    image_base64 = payload.get("image_base64", "")
    if not image_base64:
        raise HTTPException(status_code=400, detail="缺少图片数据")
    
    # 解码 base64
    try:
        # 移除 data:image/xxx;base64, 前缀（如果有）
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        image_bytes = base64.b64decode(image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片解码失败: {str(e)}")
    
    # 创建 UploadFile 对象
    image_file = UploadFile(
        file=BytesIO(image_bytes),
        filename=payload.get("filename", "desk.jpg"),
        headers={"content-type": payload.get("content_type", "image/jpeg")}
    )
    
    # 调用原始接口
    try:
        
        result = await analyze_desk_fengshui(
            image=image_file,
            solar_date=payload.get("solar_date"),
            solar_time=payload.get("solar_time"),
            gender=payload.get("gender"),
            use_bazi=payload.get("use_bazi", True)
        )
        
        
        
        # 🔴 防御性检查：确保 result 不为 None
        if result is None:
            logger.error("办公桌风水分析返回 None")
            
            return {"success": False, "error": "分析服务返回空结果，请稍后重试"}
        
        # JSONResponse 对象需要提取 body 内容
        if isinstance(result, JSONResponse):
            body = result.body
            if isinstance(body, bytes):
                data = json.loads(body.decode('utf-8'))
            else:
                data = body
            
            # 深度清理，确保可以序列化（修复 Maximum call stack exceeded）
            cleaned = _deep_clean_for_serialization(data)
            # 🔴 防御性检查：确保 cleaned 不为 None
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None (JSONResponse path)")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        elif hasattr(result, 'model_dump'):
            # Pydantic v2 模型
            # 🔴 修复：使用 exclude_none=False 确保包含所有字段（包括 None 值）
            data = result.model_dump(exclude_none=False)
            
            # 🔴 防御性检查：确保 data 不为 None
            if data is None:
                logger.error("model_dump() 返回了 None")
                return {"success": False, "error": "数据解析失败"}
            
            # 🔴 防御性检查：确保 data 是字典类型
            if not isinstance(data, dict):
                logger.error(f"model_dump() 返回了非字典类型: {type(data)}")
                return {"success": False, "error": "数据格式错误"}
            
            
            
            # 深度清理，确保可以序列化
            cleaned = _deep_clean_for_serialization(data)
            # 🔴 防御性检查：确保 cleaned 不为 None
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None (Pydantic v2 path)")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        elif hasattr(result, 'dict'):
            # Pydantic v1 模型
            data = result.dict()
            
            # 深度清理，确保可以序列化
            cleaned = _deep_clean_for_serialization(data)
            # 🔴 防御性检查：确保 cleaned 不为 None
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None (Pydantic v1 path)")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        elif isinstance(result, dict):
            # 普通字典，直接返回
            
            cleaned = _deep_clean_for_serialization(result)
            # 🔴 防御性检查：确保 cleaned 不为 None
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        
        # 未知类型，尝试转换
        logger.warning(f"办公桌风水分析返回了未知类型: {type(result)}")
        
        return {"success": False, "error": f"分析服务返回了无效的数据类型: {type(result).__name__}"}
        
    except Exception as e:
        logger.error(f"办公桌风水分析异常: {e}", exc_info=True)
        
        
        # 🔴 修复：正确处理 HTTPException，提取 detail 字段
        if isinstance(e, HTTPException):
            error_detail = e.detail if hasattr(e, 'detail') and e.detail else str(e)
            return {"success": False, "error": f"分析失败: {error_detail}"}
        else:
            error_msg = str(e) if e else "未知错误"
            return {"success": False, "error": f"分析失败: {error_msg}"}


def _deep_clean_for_serialization(obj: Any, visited: set = None) -> Any:
    """深度清理对象，确保可以 JSON 序列化
    
    递归清理字典、列表和对象，将无法序列化的类型转换为字符串。
    用于修复面相分析V2和办公桌风水的 Maximum call stack exceeded 错误。
    
    Args:
        obj: 要清理的对象
        visited: 已访问对象的ID集合，用于检测循环引用
    """
    if visited is None:
        visited = set()
    
    # 🔴 防御性检查：如果 obj 是 None，直接返回 None
    if obj is None:
        return None
    
    # 检测循环引用
    obj_id = id(obj)
    if obj_id in visited:
        return "[循环引用]"
    visited.add(obj_id)
    
    try:
        if isinstance(obj, dict):
            return {k: _deep_clean_for_serialization(v, visited) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_deep_clean_for_serialization(item, visited) for item in obj]
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif hasattr(obj, '__dict__'):
            # 对象，转换为字典
            return _deep_clean_for_serialization(obj.__dict__, visited)
        else:
            # 其他类型（如 numpy 数组、PIL 图片等），转换为字符串
            return str(obj)
    finally:
        visited.discard(obj_id)


async def _collect_sse_stream(generator) -> Dict[str, Any]:
    """
    收集 SSE 流式响应的所有数据
    
    将流式生成器的输出收集为统一的响应格式：
    - 收集所有 brief_response_chunk 内容到 stream_content
    - 收集 preset_questions 到 data
    - 收集 performance 到 data
    - 捕获 error 消息
    
    Args:
        generator: 流式生成器
        
    Returns:
        Dict: 包含 success, data, stream_content, error 的响应字典
    """
    data_content = {}
    stream_contents = []  # 收集所有流式内容
    error_content = None
    current_event_type = None
    
    try:
        chunk_count = 0
        async for chunk in generator:
            chunk_count += 1
            if not chunk:
                continue
            
            # 解析 SSE 格式：event: xxx\ndata: {...}
            chunk_str = chunk if isinstance(chunk, str) else chunk.decode('utf-8')
            
            # 处理多行 SSE 数据
            lines = chunk_str.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 解析 event: 行
                if line.startswith('event:'):
                    current_event_type = line[6:].strip()
                    logger.debug(f"[_collect_sse_stream] 收到事件: {current_event_type}")
                    continue
                
                # 解析 data: 行
                if line.startswith('data:'):
                    json_str = line[5:].strip()
                    if not json_str:
                        continue
                    
                    try:
                        msg = json.loads(json_str)
                        
                        # ⭐ 关键修复：如果消息中包含 type 字段（如 marriage_analysis_stream_generator 的格式），则从 JSON 数据中提取类型
                        # 这样既支持原有的 event: 行格式，也支持新的 data: {"type": "xxx"} 格式
                        msg_type = msg.get('type')
                        if msg_type:
                            # 使用消息中的 type 字段作为事件类型（优先级更高）
                            event_type_to_use = msg_type
                            logger.debug(f"[_collect_sse_stream] 从消息中提取类型: {event_type_to_use}")
                        else:
                            # 回退到使用 event: 行设置的类型（向后兼容）
                            event_type_to_use = current_event_type
                            logger.debug(f"[_collect_sse_stream] 使用 event 行类型: {event_type_to_use}")
                        
                        # 根据事件类型处理数据
                        # 支持 marriage_analysis_stream_generator 的格式：progress, complete, error
                        # 支持 wuxing_proportion_stream_generator 的格式：data, progress, complete, error
                        if event_type_to_use == 'data':
                            # 数据消息（如 wuxing_proportion 的完整数据）
                            content = msg.get('content', {})
                            if content:
                                data_content['data'] = content
                                logger.debug(f"[_collect_sse_stream] 保存数据消息: {type(content)}")
                        
                        elif event_type_to_use == 'progress' or event_type_to_use in ('brief_response_chunk', 'llm_chunk'):
                            # 流式内容块（progress 或场景1的 brief_response_chunk，场景2的 llm_chunk）
                            content = msg.get('content', '')
                            if content:
                                stream_contents.append(content)
                                logger.debug(f"[_collect_sse_stream] 收集到流式内容块: {len(content)} 字符")
                        
                        elif event_type_to_use == 'complete' or event_type_to_use == 'brief_response_end':
                            # 完成标记（marriage_analysis 的 complete 或场景1的 brief_response_end）
                            if event_type_to_use == 'complete':
                                # marriage_analysis 格式：complete 消息可能包含剩余的未发送内容
                                content = msg.get('content', '')
                                if content:
                                    stream_contents.append(content)
                                    logger.debug(f"[_collect_sse_stream] 收集到完成时的剩余内容: {len(content)} 字符")
                                # 标记流式传输完成
                                data_content['llm_completed'] = True
                                logger.debug(f"[_collect_sse_stream] 流式传输完成标记")
                            else:
                                # 简短答复结束，保存完整内容
                                content = msg.get('content', '')
                                if content:
                                    data_content['brief_response'] = content
                                    logger.debug(f"[_collect_sse_stream] 保存简短答复: {len(content)} 字符")
                        
                        elif event_type_to_use == 'llm_end':
                            # LLM结束（场景2），如果有完整响应可以保存
                            # 注意：完整响应在stream_content中，这里只标记结束
                            data_content['llm_completed'] = True
                            logger.debug(f"[_collect_sse_stream] LLM完成标记")
                        
                        elif event_type_to_use == 'preset_questions':
                            # 预设问题列表（场景1）
                            questions = msg.get('questions', [])
                            if questions:
                                data_content['preset_questions'] = questions
                                logger.debug(f"[_collect_sse_stream] 保存预设问题: {len(questions)} 个")
                        
                        elif event_type_to_use == 'related_questions':
                            # 相关问题列表（场景2）
                            questions = msg.get('questions', [])
                            if questions:
                                data_content['related_questions'] = questions
                                logger.debug(f"[_collect_sse_stream] 保存相关问题: {len(questions)} 个")
                        
                        elif event_type_to_use == 'basic_analysis':
                            # 基础分析结果（场景2）
                            data_content['basic_analysis'] = msg
                            logger.debug(f"[_collect_sse_stream] 保存基础分析结果")
                        
                        elif event_type_to_use == 'performance':
                            # 性能数据
                            data_content['performance'] = msg
                            logger.debug(f"[_collect_sse_stream] 保存性能数据")
                        
                        elif event_type_to_use == 'status':
                            # 状态信息，保存最后一个状态
                            data_content['last_status'] = msg
                            logger.debug(f"[_collect_sse_stream] 更新状态: {msg.get('stage', 'unknown')}")
                        
                        elif event_type_to_use == 'error':
                            # 错误信息（支持 marriage_analysis 的 error 格式）
                            error_content = msg.get('content') or msg.get('message') or str(msg)
                            logger.warning(f"[_collect_sse_stream] 收到错误: {error_content}")
                        
                        elif event_type_to_use == 'end':
                            # 结束标记，忽略
                            logger.debug(f"[_collect_sse_stream] 收到结束标记")
                            pass
                        else:
                            logger.debug(f"[_collect_sse_stream] 未处理的事件类型: {event_type_to_use} (原始: {current_event_type}, 消息type: {msg_type})")
                        
                    except json.JSONDecodeError:
                        # 非 JSON 格式，可能是普通文本
                        if current_event_type in ('brief_response_chunk', 'llm_chunk'):
                            stream_contents.append(json_str)
                            logger.debug(f"[_collect_sse_stream] 收集到非JSON流式内容: {len(json_str)} 字符")
                    except Exception as e:
                        logger.warning(f"解析 SSE 消息失败: {e}, 事件类型: {current_event_type}, 原始数据: {line[:100]}")
        
        logger.info(f"[_collect_sse_stream] 完成收集，共收到 {chunk_count} 个chunk, stream_contents={len(stream_contents)}, data_keys={list(data_content.keys())}")
        
        # 构建响应
        if error_content:
            return {
                "success": False,
                "error": error_content
            }
        
        # 合并流式内容
        stream_content = ''.join(stream_contents) if stream_contents else None
        
        # 如果没有收集到任何数据，记录警告
        if not data_content and not stream_content:
            logger.warning(f"[_collect_sse_stream] 警告：没有收集到任何数据，chunk_count={chunk_count}")
        
        result = {
            "success": True,
            "data": data_content if data_content else None,
            "stream_content": stream_content
        }
        
        logger.info(f"[_collect_sse_stream] 返回结果: success={result['success']}, data_keys={list(result['data'].keys()) if result['data'] else None}, stream_content_len={len(stream_content) if stream_content else 0}")
        
        return result
        
    except Exception as e:
        logger.error(f"收集 SSE 流失败: {e}", exc_info=True)
        import traceback
        logger.error(f"堆栈跟踪: {traceback.format_exc()}")
        return {
            "success": False,
            "error": f"流式处理失败: {str(e)}"
        }


def _grpc_cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": (
            "content-type,x-grpc-web,x-user-agent,grpc-timeout,authorization"
        ),
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Expose-Headers": "grpc-status,grpc-message",
    }


@router.options("/grpc-web/{path:path}")
async def grpc_web_options(path: str):
    """处理 gRPC-Web 预检请求"""
    return Response(status_code=204, headers=_grpc_cors_headers())


@router.post("/grpc-web/frontend.gateway.FrontendGateway/Call")
async def grpc_web_gateway(request: Request):
    """
    gRPC-Web 入口：
    - 解包 gRPC-Web 帧
    - 解析 protobuf payload（手写解析器，避免运行时生成代码）
    - 调度到已有业务 handler
    - 将响应再编码为 gRPC-Web 帧
    """
    # 确保 json 模块在函数作用域内可用（避免 UnboundLocalError）
    import json
    
    raw_body = await request.body()

    try:
        message_bytes = _extract_grpc_web_message(raw_body)
        frontend_request = _decode_frontend_request(message_bytes)
    except ValueError as exc:
        logger.error("gRPC-Web 请求解析失败: %s", exc, exc_info=True)
        return _build_error_response(str(exc), http_status=400, grpc_status=3)
    except Exception as exc:
        logger.error("gRPC-Web 请求解析异常: %s", exc, exc_info=True)
        return _build_error_response(f"请求解析异常: {str(exc)}", http_status=500, grpc_status=13)

    endpoint = frontend_request["endpoint"]
    payload_json = frontend_request["payload_json"]

    try:
        payload = json.loads(payload_json) if payload_json else {}
    except JSONDecodeError as exc:
        error_msg = f"payload_json 解析失败: {exc}"
        logger.warning(error_msg)
        return _build_error_response(error_msg, http_status=400, grpc_status=3)

    # 认证功能已移除，所有端点无需认证即可访问

    handler = SUPPORTED_ENDPOINTS.get(endpoint)
    logger.debug(f"🔍 查找端点处理器: {endpoint}, 是否存在: {handler is not None}, 总端点数: {len(SUPPORTED_ENDPOINTS)}")
    
    # ⭐ 关键修复：如果端点列表为空，说明热更新后装饰器未执行，立即恢复所有端点
    if len(SUPPORTED_ENDPOINTS) == 0:
        # 使用 print 强制输出（不依赖日志配置）
        print(f"🚨🚨 端点列表为空！端点: {endpoint}, 立即恢复所有端点...", flush=True)
        logger.error(f"🚨 端点列表为空！端点: {endpoint}, 立即恢复所有端点...")
        try:
            # 调用 _ensure_endpoints_registered 恢复关键端点
            _ensure_endpoints_registered()
            # 重新获取 handler
            handler = SUPPORTED_ENDPOINTS.get(endpoint)
            endpoint_count = len(SUPPORTED_ENDPOINTS)
            print(f"🚨 端点恢复完成，当前端点数量: {endpoint_count}, 目标端点: {endpoint}, 是否存在: {handler is not None}", flush=True)
            logger.error(f"🚨 端点恢复完成，当前端点数量: {endpoint_count}, 目标端点: {endpoint}, 是否存在: {handler is not None}, 已注册端点: {list(SUPPORTED_ENDPOINTS.keys())[:10]}")
            if not handler:
                print(f"🚨 端点恢复后仍然未找到: {endpoint}, 已注册端点: {list(SUPPORTED_ENDPOINTS.keys())}", flush=True)
                logger.error(f"🚨 端点恢复后仍然未找到: {endpoint}, 已注册端点: {list(SUPPORTED_ENDPOINTS.keys())}")
        except Exception as e:
            print(f"🚨 端点恢复失败: {e}", flush=True)
            import traceback
            print(f"🚨 端点恢复失败堆栈: {traceback.format_exc()}", flush=True)
            logger.error(f"🚨 端点恢复失败: {e}", exc_info=True)
            logger.error(f"🚨 端点恢复失败堆栈: {traceback.format_exc()}")
    
    if not handler:
        # 如果端点未找到，尝试动态注册（用于热更新后恢复）
        if endpoint == "/daily-fortune-calendar/query":
            try:
                from server.api.v1.daily_fortune_calendar import (
                    DailyFortuneCalendarRequest,
                    query_daily_fortune_calendar,
                )
                async def _handle_daily_fortune_calendar_query(payload: Dict[str, Any]):
                    """处理每日运势日历查询请求"""
                    # ⚠️ 重要：DailyFortuneCalendarRequest 的所有字段都是可选的
                    # 未登录用户只需要提供 date 参数
                    request_model = DailyFortuneCalendarRequest(**payload)
                    return await query_daily_fortune_calendar(request_model)
                SUPPORTED_ENDPOINTS["/daily-fortune-calendar/query"] = _handle_daily_fortune_calendar_query
                handler = _handle_daily_fortune_calendar_query
                logger.info("✅ 动态注册端点: /daily-fortune-calendar/query")
            except Exception as e:
                logger.error(f"动态注册端点失败: {e}", exc_info=True)
        
        # 动态注册 /bazi/rizhu-liujiazi 端点（用于热更新后恢复）
        if endpoint == "/bazi/rizhu-liujiazi":
            try:
                from server.api.v1.rizhu_liujiazi import (
                    RizhuLiujiaziRequest,
                    get_rizhu_liujiazi,
                )
                async def _handle_rizhu_liujiazi_dynamic(payload: Dict[str, Any]):
                    """处理日元-六十甲子查询请求（动态注册）"""
                    request_model = RizhuLiujiaziRequest(**payload)
                    return await get_rizhu_liujiazi(request_model)
                SUPPORTED_ENDPOINTS["/bazi/rizhu-liujiazi"] = _handle_rizhu_liujiazi_dynamic
                handler = _handle_rizhu_liujiazi_dynamic
                logger.info("✅ 动态注册端点: /bazi/rizhu-liujiazi")
            except Exception as e:
                logger.error(f"动态注册端点失败: {e}", exc_info=True)
        
        # 动态注册 /bazi/xishen-jishen 端点（用于热更新后恢复）
        if endpoint == "/bazi/xishen-jishen":
            try:
                from server.api.v1.xishen_jishen import XishenJishenRequest, get_xishen_jishen
                async def _handle_xishen_jishen_dynamic(payload: Dict[str, Any]):
                    """处理喜神忌神查询请求（动态注册）"""
                    request_model = XishenJishenRequest(**payload)
                    return await get_xishen_jishen(request_model)
                SUPPORTED_ENDPOINTS["/bazi/xishen-jishen"] = _handle_xishen_jishen_dynamic
                handler = _handle_xishen_jishen_dynamic
                logger.info("✅ 动态注册端点: /bazi/xishen-jishen")
            except Exception as e:
                logger.error(f"动态注册端点失败: {e}", exc_info=True)
        
        # 动态注册 /bazi/wuxing-proportion/test 端点（用于热更新后恢复）
        if endpoint == "/bazi/wuxing-proportion/test":
            try:
                from server.api.v1.wuxing_proportion import WuxingProportionRequest, wuxing_proportion_test
                async def _handle_wuxing_proportion_test_dynamic(payload: Dict[str, Any]):
                    """处理五行占比测试接口请求（动态注册）"""
                    request_model = WuxingProportionRequest(**payload)
                    return await wuxing_proportion_test(request_model)
                SUPPORTED_ENDPOINTS["/bazi/wuxing-proportion/test"] = _handle_wuxing_proportion_test_dynamic
                handler = _handle_wuxing_proportion_test_dynamic
                logger.info("✅ 动态注册端点: /bazi/wuxing-proportion/test")
            except Exception as e:
                logger.error(f"动态注册端点失败: {e}", exc_info=True)
        
        # 动态注册 /bazi/xishen-jishen/test 端点（用于热更新后恢复）
        if endpoint == "/bazi/xishen-jishen/test":
            try:
                from server.api.v1.xishen_jishen import XishenJishenRequest, xishen_jishen_test
                async def _handle_xishen_jishen_test_dynamic(payload: Dict[str, Any]):
                    """处理喜神忌神测试接口请求（动态注册）"""
                    request_model = XishenJishenRequest(**payload)
                    return await xishen_jishen_test(request_model)
                SUPPORTED_ENDPOINTS["/bazi/xishen-jishen/test"] = _handle_xishen_jishen_test_dynamic
                handler = _handle_xishen_jishen_test_dynamic
                logger.info("✅ 动态注册端点: /bazi/xishen-jishen/test")
            except Exception as e:
                logger.error(f"动态注册端点失败: {e}", exc_info=True)
        
        # 动态注册 /daily-fortune-calendar/test 端点（用于热更新后恢复）
        if endpoint == "/daily-fortune-calendar/test":
            try:
                from server.api.v1.daily_fortune_calendar import DailyFortuneCalendarRequest, daily_fortune_calendar_test
                async def _handle_daily_fortune_calendar_test_dynamic(payload: Dict[str, Any]):
                    """处理每日运势日历测试接口请求（动态注册）"""
                    request_model = DailyFortuneCalendarRequest(**payload)
                    return await daily_fortune_calendar_test(request_model)
                SUPPORTED_ENDPOINTS["/daily-fortune-calendar/test"] = _handle_daily_fortune_calendar_test_dynamic
                handler = _handle_daily_fortune_calendar_test_dynamic
                logger.info("✅ 动态注册端点: /daily-fortune-calendar/test")
            except Exception as e:
                logger.error(f"动态注册端点失败: {e}", exc_info=True)
        
        if not handler:
            # 调试信息：列出所有已注册的端点
            available_endpoints = list(SUPPORTED_ENDPOINTS.keys())
            logger.warning(f"未找到端点: {endpoint}, 已注册的端点: {available_endpoints}")
            error_msg = f"Unsupported endpoint: {endpoint}. Available endpoints: {', '.join(available_endpoints[:10])}"
            return _build_error_response(error_msg, http_status=404, grpc_status=12)

    

    try:
        result = await handler(payload)
        
        
        
        # 🔴 防御性检查：确保 result 不为 None
        if result is None:
            logger.error(f"Handler 返回了 None，endpoint: {endpoint}")
            
            data = {"detail": "服务返回空结果，请稍后重试"}
            status_code = 500
        else:
            # 如果 handler 已经处理了 JSONResponse，result 应该是字典
            # 但为了安全，仍然检查 JSONResponse 对象
            from fastapi.responses import JSONResponse
            if isinstance(result, JSONResponse):
                body = result.body
                if isinstance(body, bytes):
                    data = json.loads(body.decode('utf-8'))
                else:
                    data = body
                # 🔴 防御性检查：确保 data 不为 None
                if data is None:
                    logger.error("JSONResponse body 解析后为 None")
                    data = {"error": "响应解析失败", "detail": "JSONResponse body 为空"}
            else:
                # 处理 Pydantic 模型和普通字典
                try:
                    # 检查是否为 Pydantic BaseModel
                    if hasattr(result, 'model_dump'):
                        # Pydantic v2
                        # 🔴 修复：使用 exclude_none=False 确保包含所有字段（包括 None 值）
                        data = result.model_dump(exclude_none=False)
                        # 🔴 防御性检查：确保 model_dump 返回值不为 None
                        if data is None:
                            logger.error("Pydantic v2 model_dump 返回了 None")
                            data = {"error": "数据解析失败", "detail": "model_dump 返回空结果"}
                    elif hasattr(result, 'dict'):
                        # Pydantic v1
                        data = result.dict()
                        # 🔴 防御性检查：确保 dict() 返回值不为 None
                        if data is None:
                            logger.error("Pydantic v1 dict() 返回了 None")
                            data = {"error": "数据解析失败", "detail": "dict() 返回空结果"}
                    else:
                        # 普通对象，尝试 JSON 序列化
                        json_str = json.dumps(result, default=str, ensure_ascii=False)
                        data = json.loads(json_str)
                        # 🔴 防御性检查：确保 json.loads 返回值不为 None
                        if data is None:
                            logger.error("json.loads 返回了 None")
                            data = {"error": "数据解析失败", "detail": "JSON 解析返回空结果"}
                except (RecursionError, ValueError, TypeError) as json_err:
                    logger.error(f"JSON 序列化失败（可能是循环引用或数据过大）: {json_err}", exc_info=True)
                    # 降级方案：使用 jsonable_encoder
                    try:
                        data = jsonable_encoder(result)
                        # 🔴 防御性检查：确保 jsonable_encoder 返回值不为 None
                        if data is None:
                            logger.error("jsonable_encoder 返回了 None")
                            data = {"error": "数据序列化失败", "detail": "jsonable_encoder 返回空结果"}
                    except Exception as encoder_err:
                        logger.error(f"jsonable_encoder 也失败: {encoder_err}", exc_info=True)
                        data = {"error": "数据序列化失败", "detail": str(json_err)}
            
            # 🔴 防御性检查：确保 data 在 try 块中被设置
            if 'data' not in locals() or data is None:
                logger.error("data 变量未初始化或为 None")
                data = {"error": "数据处理失败", "detail": "数据变量未正确初始化"}
                status_code = 500
            else:
                status_code = 200
    except HTTPException as exc:
        status_code = exc.status_code
        data = {"detail": exc.detail}
    except Exception as exc:  # noqa: BLE001
        logger.exception("gRPC-Web handler 执行失败 (%s): %s", endpoint, exc)
        status_code = 500
        data = {"detail": f"Internal error: {exc}"}

    

    # 🔴 防御性检查：确保 data 不为 None
    if data is None:
        logger.error(f"gRPC-Web handler 返回了 None，endpoint: {endpoint}")
        
        data = {"detail": "服务返回空结果，请稍后重试"}
        status_code = 500
    
    # 🔴 防御性检查：确保 data 是字典类型
    if not isinstance(data, dict):
        logger.error(f"gRPC-Web handler 返回了非字典类型: {type(data)}, endpoint: {endpoint}")
        
        data = {"detail": f"服务返回了无效的数据类型: {type(data).__name__}"}
        status_code = 500
    
    
    
    # 🔴 最终防御性检查：确保 data 是字典且不为 None（双重保险）
    if not isinstance(data, dict) or data is None:
        logger.error(f"最终检查：data 不是有效字典，endpoint: {endpoint}, type: {type(data)}")
        data = {"detail": "服务返回了无效的数据"}
        status_code = 500
    
    success = 200 <= status_code < 300
    # 🔴 安全获取 detail：确保 data 是字典
    detail_value = data.get("detail", "") if isinstance(data, dict) else "未知错误"
    
    response_payload = _encode_frontend_response(
        success=success,
        data_json=json.dumps(data, ensure_ascii=False) if data is not None else "",
        error="" if success else str(detail_value),
        status_code=status_code,
    )

    grpc_status = 0 if success else _map_http_to_grpc_status(status_code)
    grpc_message = "" if success else str(detail_value)
    
    return _build_grpc_web_response(response_payload, grpc_status, grpc_message)


def _map_http_to_grpc_status(status_code: int) -> int:
    mapping = {
        400: 3,  # INVALID_ARGUMENT
        401: 16,  # UNAUTHENTICATED
        403: 7,  # PERMISSION_DENIED
        404: 12,  # UNIMPLEMENTED
        422: 3,
    }
    return mapping.get(status_code, 13)  # INTERNAL


def _extract_grpc_web_message(body: bytes) -> bytes:
    """解析 gRPC-Web 帧，返回第一帧的 payload"""
    if len(body) < 5:
        raise ValueError("gRPC-Web 帧长度不足")

    flag = body[0]
    if flag & 0x80:
        raise ValueError("首帧不应为 trailer")

    length = int.from_bytes(body[1:5], byteorder="big")
    payload = body[5 : 5 + length]
    if len(payload) != length:
        raise ValueError("gRPC-Web payload 长度不匹配")

    return payload


def _decode_frontend_request(message: bytes) -> Dict[str, str]:
    """手动解析 FrontendJsonRequest"""
    endpoint = ""
    payload_json = ""

    idx = 0
    length = len(message)

    while idx < length:
        key = message[idx]
        idx += 1
        field_number = key >> 3
        wire_type = key & 0x07

        if wire_type == 2:  # length-delimited
            str_len, idx = _read_varint(message, idx)
            value_bytes = message[idx : idx + str_len]
            idx += str_len
            value = value_bytes.decode("utf-8")

            if field_number == 1:
                endpoint = value
            elif field_number == 2:
                payload_json = value
            # field_number == 3 (auth_token) 已移除，不再解析
        else:
            raise ValueError(f"不支持的 wire_type: {wire_type}")

    return {"endpoint": endpoint, "payload_json": payload_json}


def _encode_frontend_response(
    *, success: bool, data_json: str, error: str, status_code: int
) -> bytes:
    """手动编码 FrontendJsonResponse"""
    buffer = bytearray()

    # bool success = 1;
    buffer.extend(_write_varint((1 << 3) | 0))
    buffer.extend(_write_varint(1 if success else 0))

    # string data_json = 2;
    if data_json:
        data_bytes = data_json.encode("utf-8")
        buffer.extend(_write_varint((2 << 3) | 2))
        buffer.extend(_write_varint(len(data_bytes)))
        buffer.extend(data_bytes)

    # string error = 3;
    if error:
        error_bytes = error.encode("utf-8")
        buffer.extend(_write_varint((3 << 3) | 2))
        buffer.extend(_write_varint(len(error_bytes)))
        buffer.extend(error_bytes)

    # int32 status_code = 4;
    buffer.extend(_write_varint((4 << 3) | 0))
    buffer.extend(_write_varint(status_code))

    return bytes(buffer)


def _build_grpc_web_response(message: bytes, grpc_status: int, grpc_message: str) -> Response:
    data_frame = _wrap_frame(0x00, message)
    
    # 修复：grpc-message 在 trailer 中需要使用 URL 编码来支持非 ASCII 字符
    # 根据 gRPC-Web 规范，grpc-message 应该使用 URL 编码
    import urllib.parse
    encoded_message = urllib.parse.quote(grpc_message, safe='')
    
    # trailer payload 使用 ASCII 编码（因为已经 URL 编码了）
    trailer_payload = f"grpc-status:{grpc_status}\r\ngrpc-message:{encoded_message}\r\n".encode(
        "ascii", errors="ignore"
    )
    trailer_frame = _wrap_frame(0x80, trailer_payload)
    body = data_frame + trailer_frame

    headers = {
        **_grpc_cors_headers(),
        "grpc-status": str(grpc_status),
        # HTTP header 中的 grpc-message 也需要 URL 编码
        "grpc-message": encoded_message,
        "Content-Type": "application/grpc-web+proto",
    }

    return Response(content=body, media_type="application/grpc-web+proto", headers=headers)


def _build_error_response(message: str, http_status: int, grpc_status: int) -> Response:
    payload = _encode_frontend_response(
        success=False,
        data_json=json.dumps({"detail": message}, ensure_ascii=False),
        error=message,
        status_code=http_status,
    )
    return _build_grpc_web_response(payload, grpc_status, message)


def _wrap_frame(flag: int, payload: bytes) -> bytes:
    header = bytes([flag]) + len(payload).to_bytes(4, byteorder="big")
    return header + payload


def _read_varint(data: bytes, idx: int) -> Tuple[int, int]:
    """读取 protobuf varint"""
    shift = 0
    result = 0

    while idx < len(data):
        byte = data[idx]
        idx += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, idx
        shift += 7

    raise ValueError("varint 解析失败")


def _write_varint(value: int) -> bytes:
    """写 protobuf varint"""
    buffer = bytearray()
    while True:
        to_write = value & 0x7F
        value >>= 7
        if value:
            buffer.append(to_write | 0x80)
        else:
            buffer.append(to_write)
            break
    return bytes(buffer)




# 模块加载时确保端点被注册（用于热更新后恢复）
def _ensure_endpoints_registered():
    """确保所有端点被注册（用于热更新后恢复）"""
    global SUPPORTED_ENDPOINTS
    
    # ⭐ 关键修复：如果端点列表为空，说明热更新后装饰器未执行，直接手动注册所有关键端点
    key_endpoints = ["/daily-fortune-calendar/query", "/bazi/interface", "/bazi/shengong-minggong", "/bazi/rizhu-liujiazi"]
    if len(SUPPORTED_ENDPOINTS) == 0:
        logger.error(f"🚨 端点列表为空！直接手动注册所有关键端点...")
        # 直接进入手动注册逻辑，跳过重新加载模块（因为重新加载后端点仍然是空的）
        missing_endpoints = key_endpoints
    else:
        # 检查关键端点是否已注册
        missing_endpoints = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
    logger.debug(f"检查关键端点注册状态: key_endpoints={key_endpoints}, missing_endpoints={missing_endpoints}, supported_endpoints_count={len(SUPPORTED_ENDPOINTS)}")
    
    if missing_endpoints:
        logger.error(f"🚨 检测到缺失端点: {missing_endpoints}，尝试手动注册...")
        try:
            # 手动注册每日运势日历端点
            if "/daily-fortune-calendar/query" in missing_endpoints:
                from server.api.v1.daily_fortune_calendar import (
                    DailyFortuneCalendarRequest,
                    query_daily_fortune_calendar,
                )
                
                async def _handle_daily_fortune_calendar_query(payload: Dict[str, Any]):
                    """处理每日运势日历查询请求"""
                    # ⚠️ 重要：DailyFortuneCalendarRequest 的所有字段都是可选的
                    # 未登录用户只需要提供 date 参数
                    request_model = DailyFortuneCalendarRequest(**payload)
                    return await query_daily_fortune_calendar(request_model)
                
                SUPPORTED_ENDPOINTS["/daily-fortune-calendar/query"] = _handle_daily_fortune_calendar_query
                logger.error(f"🚨 手动注册端点: /daily-fortune-calendar/query, 当前端点数量: {len(SUPPORTED_ENDPOINTS)}")
            
            # 手动注册 /bazi/interface 端点
            if "/bazi/interface" in missing_endpoints:
                try:
                    from server.api.v1.bazi import BaziInterfaceRequest, generate_bazi_interface
                    from fastapi import Request
                    from unittest.mock import MagicMock
                    async def _handle_bazi_interface_manual(payload: Dict[str, Any]):
                        """处理八字接口请求（手动注册）"""
                        request_model = BaziInterfaceRequest(**payload)
                        mock_request = MagicMock(spec=Request)
                        result = await generate_bazi_interface(request_model, mock_request)
                        if hasattr(result, 'model_dump'):
                            return result.model_dump()
                        elif hasattr(result, 'dict'):
                            return result.dict()
                        return result
                    SUPPORTED_ENDPOINTS["/bazi/interface"] = _handle_bazi_interface_manual
                    logger.error("🚨 手动注册端点: /bazi/interface")
                except Exception as e:
                    logger.error(f"❌ 手动注册 /bazi/interface 端点失败: {e}", exc_info=True)
            
            # 手动注册 /bazi/shengong-minggong 端点
            if "/bazi/shengong-minggong" in missing_endpoints:
                try:
                    from server.api.v1.bazi import ShengongMinggongRequest, get_shengong_minggong
                    from fastapi import Request
                    from unittest.mock import MagicMock
                    async def _handle_shengong_minggong_manual(payload: Dict[str, Any]):
                        """处理身宫命宫请求（手动注册）"""
                        request_model = ShengongMinggongRequest(**payload)
                        mock_request = MagicMock(spec=Request)
                        result = await get_shengong_minggong(request_model, mock_request)
                        if hasattr(result, 'model_dump'):
                            return result.model_dump()
                        elif hasattr(result, 'dict'):
                            return result.dict()
                        return result
                    SUPPORTED_ENDPOINTS["/bazi/shengong-minggong"] = _handle_shengong_minggong_manual
                    logger.error("🚨 手动注册端点: /bazi/shengong-minggong")
                except Exception as e:
                    logger.error(f"❌ 手动注册 /bazi/shengong-minggong 端点失败: {e}", exc_info=True)
            
            # 手动注册 /bazi/rizhu-liujiazi 端点
            if "/bazi/rizhu-liujiazi" in missing_endpoints:
                try:
                    from server.api.v1.rizhu_liujiazi import (
                        RizhuLiujiaziRequest,
                        get_rizhu_liujiazi,
                    )
                    async def _handle_rizhu_liujiazi_manual(payload: Dict[str, Any]):
                        """处理日元-六十甲子查询请求（手动注册）"""
                        request_model = RizhuLiujiaziRequest(**payload)
                        return await get_rizhu_liujiazi(request_model)
                    SUPPORTED_ENDPOINTS["/bazi/rizhu-liujiazi"] = _handle_rizhu_liujiazi_manual
                    logger.error("🚨 手动注册端点: /bazi/rizhu-liujiazi")
                except Exception as e:
                    logger.error(f"❌ 手动注册 /bazi/rizhu-liujiazi 端点失败: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"手动注册端点失败: {e}", exc_info=True)


# 注册安全监控端点（可选）
try:
    from server.api.v1.security_monitor import (
        get_security_stats,
        get_blocked_ips,
        unblock_ip,
        check_ip_status
    )
    
    @_register("/security/stats")
    async def _handle_security_stats(payload: Dict[str, Any]):
        """获取安全统计信息"""
        return await get_security_stats()
    
    @_register("/security/blocked-ips")
    async def _handle_security_blocked_ips(payload: Dict[str, Any]):
        """获取封禁 IP 列表"""
        return await get_blocked_ips()
    
    @_register("/security/unblock-ip")
    async def _handle_security_unblock_ip(payload: Dict[str, Any]):
        """解封 IP"""
        from server.api.v1.security_monitor import UnblockIPRequest
        request_model = UnblockIPRequest(**payload)
        return await unblock_ip(request_model)
    
    logger.info("✓ 安全监控端点已注册")
except ImportError as e:
    logger.warning(f"⚠ 安全监控端点未注册（可选功能）: {e}")

# 注册 Proto 文件服务端点（可选）
try:
    from server.api.v1.proto_service import (
        list_proto_files
    )
    
    @_register("/proto/list")
    async def _handle_proto_list(payload: Dict[str, Any]):
        """获取可用的 proto 文件列表"""
        return await list_proto_files()
    
    # 注意：/proto/{filename} 是路径参数端点，提供静态文件内容
    # 不适合通过 gRPC-Web 访问，建议直接使用 REST API: GET /api/v1/proto/{filename}
    # 已在 server/main.py 中注册为 REST 路由，无需在 gRPC 网关中注册
    
    logger.info("✓ Proto 文件服务端点已注册（/proto/list）")
except ImportError as e:
    logger.warning(f"⚠ Proto 文件服务端点未注册（可选功能）: {e}")

# 在模块加载时调用（用于热更新后恢复）
try:
    print(f"🔧 模块加载时检查端点注册状态...", flush=True)
    _ensure_endpoints_registered()
    # 验证关键端点是否已注册
    key_endpoints = ["/daily-fortune-calendar/query", "/bazi/interface", "/bazi/shengong-minggong", "/bazi/rizhu-liujiazi"]
    missing = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
    if missing:
        print(f"⚠️  模块加载后关键端点缺失: {missing}，当前端点数量: {len(SUPPORTED_ENDPOINTS)}", flush=True)
        logger.warning(f"⚠️  模块加载后关键端点缺失: {missing}，当前端点数量: {len(SUPPORTED_ENDPOINTS)}")
        logger.info(f"已注册的端点: {list(SUPPORTED_ENDPOINTS.keys())[:30]}")
    else:
        print(f"✅ 所有关键端点已注册（总端点数: {len(SUPPORTED_ENDPOINTS)}）", flush=True)
        logger.info(f"✅ 所有关键端点已注册（总端点数: {len(SUPPORTED_ENDPOINTS)}）")
except Exception as e:
    print(f"❌ 初始化端点注册检查失败: {e}", flush=True)
    import traceback
    print(f"❌ 堆栈: {traceback.format_exc()}", flush=True)
    logger.error(f"❌ 初始化端点注册检查失败: {e}", exc_info=True)
