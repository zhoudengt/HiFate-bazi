#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字前端展示 API - 提供前端友好的数据格式
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.bazi_display_service import BaziDisplayService

router = APIRouter()

# 线程池
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


class BaziDisplayRequest(BaseModel):
    """八字展示请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM")
    gender: str = Field(..., description="性别：male(男) 或 female(女)")
    
    @validator('solar_date')
    def validate_date(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('solar_time')
    def validate_time(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v


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
    current_time: Optional[str] = Field(None, description="当前时间（可选），格式：YYYY-MM-DD HH:MM")
    dayun_index: Optional[int] = Field(None, description="大运索引（可选，已废弃，优先使用dayun_year_start和dayun_year_end）")
    dayun_year_start: Optional[int] = Field(None, description="大运起始年份（可选），指定要显示的大运的起始年份")
    dayun_year_end: Optional[int] = Field(None, description="大运结束年份（可选），指定要显示的大运的结束年份")
    target_year: Optional[int] = Field(None, description="目标年份（可选），用于计算该年份的流月")


@router.post("/bazi/pan/display", summary="排盘展示（前端优化）")
async def get_pan_display(request: BaziDisplayRequest):
    """
    获取排盘数据（前端优化格式）
    
    返回数组格式的四柱数据，便于前端 v-for 渲染
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    
    返回前端友好的排盘数据，包括：
    - 基本信息
    - 四柱数组（便于前端循环渲染）
    - 五行统计（包含百分比）
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_pan_display,
            request.solar_date,
            request.solar_time,
            request.gender
        )
        
        if result.get('success'):
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
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **current_time**: 当前时间（可选）(YYYY-MM-DD HH:MM)
    
    返回前端友好的大运数据，包括：
    - 当前大运（明确标识）
    - 大运列表（数组格式，便于前端渲染）
    - 起运和交运信息
    - 年龄范围（对象格式，便于前端计算）
    """
    try:
        current_time = None
        if request.current_time:
            current_time = datetime.strptime(request.current_time, "%Y-%m-%d %H:%M")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_dayun_display,
            request.solar_date,
            request.solar_time,
            request.gender,
            current_time
        )
        
        if result.get('success'):
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
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **year_range**: 年份范围（可选）{"start": 2020, "end": 2030}
    
    返回前端友好的流年数据，包括：
    - 当前流年（明确标识）
    - 流年列表（数组格式，便于前端渲染）
    - 年龄字段（整数和显示格式）
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_liunian_display,
            request.solar_date,
            request.solar_time,
            request.gender,
            request.year_range
        )
        
        if result.get('success'):
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
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **target_year**: 目标年份（可选），用于计算该年份的流月
    
    返回前端友好的流月数据，包括：
    - 当前流月（明确标识）
    - 流月列表（数组格式，便于前端渲染）
    - 节气信息
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_liuyue_display,
            request.solar_date,
            request.solar_time,
            request.gender,
            request.target_year
        )
        
        if result.get('success'):
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
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **current_time**: 当前时间（可选）(YYYY-MM-DD HH:MM)
    - **dayun_index**: 大运索引（可选），指定要显示的大运，只返回该大运范围内的流年（性能优化）
    - **target_year**: 目标年份（可选），用于计算该年份的流月
    
    返回前端友好的数据，包括：
    - 大运数据（当前大运、大运列表、起运交运信息）
    - 流年数据（当前流年、流年列表）
    - 流月数据（当前流月、流月列表）
    """
    try:
        current_time = None
        if request.current_time:
            current_time = datetime.strptime(request.current_time, "%Y-%m-%d %H:%M")
        
        loop = asyncio.get_event_loop()
        # ✅ 修复：传递年份范围参数，而不是索引
        result = await loop.run_in_executor(
            executor,
            lambda: BaziDisplayService.get_fortune_display(
                request.solar_date,
                request.solar_time,
                request.gender,
                current_time,
                dayun_index=request.dayun_index,  # 兼容旧接口
                dayun_year_start=request.dayun_year_start,
                dayun_year_end=request.dayun_year_end,
                target_year=request.target_year
            )
        )
        
        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}\n{traceback.format_exc()}")

