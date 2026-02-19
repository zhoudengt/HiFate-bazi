# -*- coding: utf-8 -*-
"""
八字核心 gRPC-Web 端点处理器
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from server.api.grpc_gateway.endpoints import _register
from server.api.v1.bazi_display import (
    BaziDisplayRequest,
    FortuneDisplayRequest,
    get_pan_display,
    _assemble_fortune_display_response,
    _assemble_shengong_minggong_response,
)
from server.api.v1.wangshuai import WangShuaiRequest, calculate_wangshuai
from server.api.v1.formula_analysis import FormulaAnalysisRequest, analyze_formula_rules
from server.api.v1.bazi import (
    BaziInterfaceRequest,
    ShengongMinggongRequest,
)
from server.utils.bazi_input_processor import BaziInputProcessor
from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from server.orchestrators.modules_config import get_modules_config
from server.services.bazi_interface_service import BaziInterfaceService
from server.api.v1.wuxing_proportion import (
    WuxingProportionRequest,
    wuxing_proportion_test,
    wuxing_proportion_stream_generator,
)
from server.api.v1.xishen_jishen import (
    XishenJishenRequest,
    xishen_jishen_test,
    xishen_jishen_stream_generator,
)
from server.api.grpc_gateway.utils import _collect_sse_stream

logger = logging.getLogger(__name__)

try:
    from server.api.v1.rizhu_liujiazi import RizhuLiujiaziRequest, get_rizhu_liujiazi
    RIZHU_LIUJIAZI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ 无法导入 rizhu_liujiazi 模块: {e}")
    RIZHU_LIUJIAZI_AVAILABLE = False
    RizhuLiujiaziRequest = None
    get_rizhu_liujiazi = None


@_register("/bazi/pan/display")
async def _handle_pan(payload: Dict[str, Any]):
    request_model = BaziDisplayRequest(**payload)
    return await get_pan_display(request_model)


@_register("/bazi/fortune/display")
async def _handle_fortune(payload: Dict[str, Any]):
    """处理大运流年流月展示请求"""
    from server.utils.api_cache_helper import (
        generate_cache_key, get_cached_result, set_cached_result,
        L2_TTL, get_current_date_str
    )
    use_jin_mode = False
    if payload.get('current_time') == "今":
        use_jin_mode = True
        payload['current_time'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    request_model = FortuneDisplayRequest(**payload)
    final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
        request_model.solar_date, request_model.solar_time,
        request_model.calendar_type or "solar",
        request_model.location, request_model.latitude, request_model.longitude
    )
    current_time = None
    if request_model.current_time:
        if use_jin_mode:
            current_time = datetime.now()
        else:
            try:
                current_time = datetime.strptime(request_model.current_time, "%Y-%m-%d %H:%M")
            except ValueError:
                raise ValueError(f"current_time 参数格式错误: {request_model.current_time}")
    if current_time is None:
        current_time = datetime.now()
    current_date = get_current_date_str()
    cache_key = generate_cache_key(
        "fortune", final_solar_date, final_solar_time, request_model.gender, current_date,
        dayun_index=request_model.dayun_index,
        dayun_year_start=request_model.dayun_year_start,
        dayun_year_end=request_model.dayun_year_end,
        target_year=request_model.target_year
    )
    cached = get_cached_result(cache_key, "grpc/fortune/display")
    if cached:
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            cached['conversion_info'] = conversion_info
        return cached
    modules = get_modules_config('fortune_display')
    orchestrator_data = await BaziDataOrchestrator.fetch_data(
        final_solar_date, final_solar_time, request_model.gender,
        modules=modules, current_time=current_time, preprocessed=True,
        calendar_type=request_model.calendar_type or "solar",
        location=request_model.location, latitude=request_model.latitude,
        longitude=request_model.longitude, dayun_index=request_model.dayun_index,
        dayun_year_start=request_model.dayun_year_start,
        dayun_year_end=request_model.dayun_year_end,
        target_year=request_model.target_year
    )
    result = _assemble_fortune_display_response(
        orchestrator_data, final_solar_date, current_time,
        request_model.dayun_index, request_model.dayun_year_start,
        request_model.dayun_year_end, request_model.target_year
    )
    if result.get('success'):
        set_cached_result(cache_key, result, L2_TTL)
    if result.get('success') and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
        result['conversion_info'] = conversion_info
    # 异步预热：后台用 quick_mode=False 计算完整数据并刷新缓存
    if result.get('success'):
        asyncio.ensure_future(_warmup_fortune_full(
            final_solar_date, final_solar_time, request_model.gender,
            current_time, cache_key
        ))
    return result


async def _warmup_fortune_full(solar_date, solar_time, gender, current_time, fortune_cache_key):
    """后台预热：用 quick_mode=False 重新计算完整大运流年并刷新缓存"""
    try:
        from server.services.bazi_detail_service import BaziDetailService
        from server.utils.cache_multi_level import get_multi_cache

        await asyncio.sleep(0.5)

        cache = get_multi_cache()
        current_time_iso = current_time.strftime('%Y-%m-%d')
        detail_cache_key = f"bazi_detail:{solar_date}:{solar_time}:{gender}:{current_time_iso}:all:all:full"

        cache.delete(detail_cache_key)

        loop = asyncio.get_event_loop()
        full_detail = await loop.run_in_executor(
            None,
            BaziDetailService.calculate_detail_full,
            solar_date, solar_time, gender, current_time,
            None, None, False, False
        )
        if not full_detail:
            return

        cache.delete(fortune_cache_key)
        logger.info(f"✅ [异步预热] detail 完整数据已就绪，fortune 缓存已清除待重建: {fortune_cache_key[:50]}...")
    except Exception as e:
        logger.warning(f"⚠️ [异步预热] fortune 预热失败（不影响业务）: {e}")


@_register("/bazi/wangshuai")
async def _handle_wangshuai(payload: Dict[str, Any]):
    request_model = WangShuaiRequest(**payload)
    return await calculate_wangshuai(request_model)


@_register("/bazi/formula-analysis")
async def _handle_formula_analysis(payload: Dict[str, Any]):
    request_model = FormulaAnalysisRequest(**payload)
    return await analyze_formula_rules(request_model)


@_register("/bazi/interface")
async def _handle_bazi_interface(payload: Dict[str, Any]):
    """处理八字界面信息请求"""
    from server.utils.async_executor import get_executor
    request_model = BaziInterfaceRequest(**payload)
    final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
        request_model.solar_date, request_model.solar_time,
        request_model.calendar_type or "solar",
        request_model.location, request_model.latitude, request_model.longitude
    )
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        get_executor(),
        BaziInterfaceService.generate_interface_full,
        final_solar_date, final_solar_time, request_model.gender,
        request_model.name or "", request_model.location or "未知地",
        request_model.latitude or 39.00, request_model.longitude or 120.00
    )
    if conversion_info.get('converted') or conversion_info.get('timezone_info'):
        result['conversion_info'] = conversion_info
    return {"success": True, "data": result}


@_register("/bazi/shengong-minggong")
async def _handle_shengong_minggong(payload: Dict[str, Any]):
    """处理身宫命宫详细信息请求"""
    from server.utils.api_cache_helper import (
        generate_cache_key, get_cached_result, set_cached_result,
        L2_TTL, get_current_date_str
    )
    request_model = ShengongMinggongRequest(**payload)
    final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
        request_model.solar_date, request_model.solar_time,
        request_model.calendar_type or "solar",
        request_model.location, request_model.latitude, request_model.longitude
    )
    current_time = None
    if request_model.current_time:
        try:
            current_time = datetime.strptime(request_model.current_time, "%Y-%m-%d %H:%M")
        except ValueError:
            pass
    if current_time is None:
        current_time = datetime.now()
    current_date = get_current_date_str()
    cache_key = generate_cache_key(
        "shengong", final_solar_date, final_solar_time, request_model.gender, current_date,
        dayun_year_start=request_model.dayun_year_start,
        dayun_year_end=request_model.dayun_year_end,
        target_year=request_model.target_year
    )
    cached = get_cached_result(cache_key, "grpc/shengong-minggong")
    if cached:
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            cached['conversion_info'] = conversion_info
        return cached
    modules = get_modules_config('shengong_minggong')
    orchestrator_data = await BaziDataOrchestrator.fetch_data(
        final_solar_date, final_solar_time, request_model.gender,
        modules=modules, current_time=current_time, preprocessed=True,
        calendar_type=request_model.calendar_type or "solar",
        location=request_model.location, latitude=request_model.latitude,
        longitude=request_model.longitude,
        dayun_year_start=request_model.dayun_year_start,
        dayun_year_end=request_model.dayun_year_end,
        target_year=request_model.target_year
    )
    result = _assemble_shengong_minggong_response(
        orchestrator_data, final_solar_date, final_solar_time,
        request_model.gender, current_time,
        request_model.dayun_year_start, request_model.dayun_year_end,
        request_model.target_year
    )
    if result.get('success'):
        set_cached_result(cache_key, result, L2_TTL)
    if result.get('success') and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
        result['conversion_info'] = conversion_info
    return result


if RIZHU_LIUJIAZI_AVAILABLE:
    @_register("/bazi/rizhu-liujiazi")
    async def _handle_rizhu_liujiazi(payload: Dict[str, Any]):
        request_model = RizhuLiujiaziRequest(**payload)
        return await get_rizhu_liujiazi(request_model)
else:
    logger.warning("⚠️ /bazi/rizhu-liujiazi 端点未注册（模块不可用）")


@_register("/bazi/data")
async def _handle_bazi_data(payload: Dict[str, Any]):
    from server.api.v1.bazi_data import BaziDataRequest, get_bazi_data
    request_model = BaziDataRequest(**payload)
    return await get_bazi_data(request_model)


@_register("/bazi/wuxing-proportion/test")
async def _handle_wuxing_proportion_test(payload: Dict[str, Any]):
    request_model = WuxingProportionRequest(**payload)
    return await wuxing_proportion_test(request_model)


@_register("/bazi/wuxing-proportion/stream")
async def _handle_wuxing_proportion_stream(payload: Dict[str, Any]):
    request_model = WuxingProportionRequest(**payload)
    generator = wuxing_proportion_stream_generator(request_model)
    return await _collect_sse_stream(generator)


@_register("/bazi/xishen-jishen/test")
async def _handle_xishen_jishen_test(payload: Dict[str, Any]):
    request_model = XishenJishenRequest(**payload)
    return await xishen_jishen_test(request_model)


@_register("/bazi/xishen-jishen/stream")
async def _handle_xishen_jishen_stream(payload: Dict[str, Any]):
    request_model = XishenJishenRequest(**payload)
    generator = xishen_jishen_stream_generator(request_model)
    return await _collect_sse_stream(generator)
