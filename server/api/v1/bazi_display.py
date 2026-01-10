#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字前端展示 API - 提供前端友好的数据格式
"""

import sys
import os
import logging
import json
from fastapi import APIRouter, HTTPException
from fastapi import Request
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import asyncio

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.bazi_display_service import BaziDisplayService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor

router = APIRouter()

# 线程池
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


class BaziDisplayRequest(BaziBaseRequest):
    """八字展示请求模型"""
    pass


class DayunDisplayRequest(BaziDisplayRequest):
    """大运展示请求模型"""
    current_time: Optional[str] = Field(None, description="当前时间（可选），格式：YYYY-MM-DD HH:MM")


class LiunianDisplayRequest(BaziDisplayRequest):
    """流年展示请求模型"""
    year_range: Optional[Dict[str, int]] = Field(None, description="年份范围（可选），如：{\"start\": 2020, \"end\": 2030}")


class LiuyueDisplayRequest(BaziDisplayRequest):
    """流月展示请求模型"""
    target_year: Optional[int] = Field(None, description="目标年份（可选），用于计算该年份的流月")


class FortuneDisplayRequest(BaziDisplayRequest):
    """大运流年流月统一请求模型"""
    current_time: Optional[str] = Field(None, description="当前时间（可选），格式：YYYY-MM-DD HH:MM 或 '今'")
    dayun_index: Optional[int] = Field(None, description="大运索引（可选，已废弃，优先使用dayun_year_start和dayun_year_end）")
    dayun_year_start: Optional[int] = Field(None, description="大运起始年份（可选），指定要显示的大运的起始年份")
    dayun_year_end: Optional[int] = Field(None, description="大运结束年份（可选），指定要显示的大运的结束年份")
    target_year: Optional[int] = Field(None, description="目标年份（可选），用于计算该年份的流月")
    quick_mode: Optional[bool] = Field(True, description="快速模式，只计算当前大运，其他大运异步预热（默认True）")
    async_warmup: Optional[bool] = Field(True, description="是否触发异步预热（默认True）")
    
    # ✅ 不在模型级别验证，改为在路由函数内部直接处理（更灵活）
    # 注释：使用 try-except 在路由函数中处理 "今" 参数，避免 validator 拦截


@router.post("/bazi/pan/display", summary="排盘展示（前端优化）")
async def get_pan_display(request: BaziDisplayRequest):
    """
    获取排盘数据（前端优化格式）
    
    返回数组格式的四柱数据，便于前端 v-for 渲染
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当calendar_type=lunar时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    
    返回前端友好的排盘数据，包括：
    - 基本信息
    - 四柱数组（便于前端循环渲染）
    - 五行统计（包含百分比）
    - conversion_info: 转换信息（如果进行了农历转换或时区转换）
    """
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_pan_display,
            final_solar_date,
            final_solar_time,
            request.gender
        )
        
        if result.get('success'):
            # 添加转换信息到结果
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                result['conversion_info'] = conversion_info
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}\n{traceback.format_exc()}")


@router.post("/bazi/dayun/display", summary="大运展示（前端优化）")
async def get_dayun_display(request: DayunDisplayRequest):
    """
    获取大运数据（前端优化格式）
    
    返回数组格式的大运数据，包含明确的当前状态标识
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当calendar_type=lunar时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    - **current_time**: 当前时间（可选）(YYYY-MM-DD HH:MM)
    
    返回前端友好的大运数据，包括：
    - 当前大运（明确标识）
    - 大运列表（数组格式，便于前端渲染）
    - 起运和交运信息
    - 年龄范围（对象格式，便于前端计算）
    - conversion_info: 转换信息（如果进行了农历转换或时区转换）
    """
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        current_time = None
        if request.current_time:
            current_time = datetime.strptime(request.current_time, "%Y-%m-%d %H:%M")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_dayun_display,
            final_solar_date,
            final_solar_time,
            request.gender,
            current_time
        )
        
        if result.get('success'):
            # 添加转换信息到结果
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                result['conversion_info'] = conversion_info
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}\n{traceback.format_exc()}")


@router.post("/bazi/liunian/display", summary="流年展示（前端优化）")
async def get_liunian_display(request: LiunianDisplayRequest):
    """
    获取流年数据（前端优化格式）
    
    返回数组格式的流年数据，包含年龄字段
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当calendar_type=lunar时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    - **year_range**: 年份范围（可选）{"start": 2020, "end": 2030}
    
    返回前端友好的流年数据，包括：
    - 当前流年（明确标识）
    - 流年列表（数组格式，便于前端渲染）
    - 年龄字段（整数和显示格式）
    - conversion_info: 转换信息（如果进行了农历转换或时区转换）
    """
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_liunian_display,
            final_solar_date,
            final_solar_time,
            request.gender,
            request.year_range
        )
        
        if result.get('success'):
            # 添加转换信息到结果
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                result['conversion_info'] = conversion_info
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}\n{traceback.format_exc()}")


@router.post("/bazi/liuyue/display", summary="流月展示（前端优化）")
async def get_liuyue_display(request: LiuyueDisplayRequest):
    """
    获取流月数据（前端优化格式）
    
    返回数组格式的流月数据
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当calendar_type=lunar时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    - **target_year**: 目标年份（可选），用于计算该年份的流月
    
    返回前端友好的流月数据，包括：
    - 当前流月（明确标识）
    - 流月列表（数组格式，便于前端渲染）
    - 节气信息
    - conversion_info: 转换信息（如果进行了农历转换或时区转换）
    """
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_liuyue_display,
            final_solar_date,
            final_solar_time,
            request.gender,
            request.target_year
        )
        
        if result.get('success'):
            # 添加转换信息到结果
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                result['conversion_info'] = conversion_info
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}\n{traceback.format_exc()}")


@router.post("/bazi/fortune/display", summary="大运流年流月统一接口（性能优化）")
async def get_fortune_display(request: FortuneDisplayRequest):
    """
    获取大运流年流月数据（统一接口，一次返回所有数据）
    
    **性能优化**：只计算一次，避免重复调用
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当calendar_type=lunar时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    - **current_time**: 当前时间（可选）(YYYY-MM-DD HH:MM) 或 '今'
    - **dayun_index**: 大运索引（可选），指定要显示的大运，只返回该大运范围内的流年（性能优化）
    - **dayun_year_start**: 大运起始年份（可选）
    - **dayun_year_end**: 大运结束年份（可选）
    - **target_year**: 目标年份（可选），用于计算该年份的流月
    
    返回前端友好的数据，包括：
    - 大运数据（当前大运、大运列表、起运交运信息）
    - 流年数据（当前流年、流年列表）
    - 流月数据（当前流月、流月列表）
    - conversion_info: 转换信息（如果进行了农历转换或时区转换）
    """
    try:
        
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # ✅ 解析 current_time（支持"今"参数，使用 try-except 处理）
        current_time = None
        if request.current_time:
            current_time_str = str(request.current_time).strip()
            
            # 首先检查是否为 "今" 字符串
            if current_time_str == "今":
                current_time = datetime.now()
                logger.info(f"[今参数] 检测到 '今' 参数，使用当前时间: {current_time}")
            else:
                # 尝试解析时间字符串
                try:
                    current_time = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M")
                    logger.info(f"[今参数] 解析时间字符串: {current_time_str} -> {current_time}")
                except ValueError as e:
                    # 如果解析失败，检查是否是 "今"（防止 validator 已经转换的情况）
                    if current_time_str == "今":
                        current_time = datetime.now()
                        logger.info(f"[今参数] 在异常处理中检测到 '今'，使用当前时间: {current_time}")
                    else:
                        logger.error(f"[今参数] 时间解析失败: {current_time_str}, 错误: {e}")
                        raise ValueError(f"current_time 参数格式错误，应为 '今' 或 'YYYY-MM-DD HH:MM' 格式，但收到: {request.current_time}")
        
        # ✅ 使用统一数据服务（内部适配，接口层完全不动）
        from server.services.bazi_data_service import BaziDataService
        
        # 使用 BaziDisplayService 直接调用（传递快速模式参数）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_fortune_display,
            final_solar_date,
            final_solar_time,
            request.gender,
            current_time,
            request.dayun_index,
            request.dayun_year_start,
            request.dayun_year_end,
            request.target_year,
            request.quick_mode if request.quick_mode is not None else True,  # quick_mode
            request.async_warmup if request.async_warmup is not None else True  # async_warmup
        )
        
        if result.get('success'):
            # 添加转换信息到结果
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                result['conversion_info'] = conversion_info
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}\n{traceback.format_exc()}")

