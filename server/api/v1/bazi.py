#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字计算API接口
"""

import sys
import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.services.bazi_interface_service import BaziInterfaceService
from server.services.bazi_detail_service import BaziDetailService
from server.utils import bazi_cache

router = APIRouter()

# 根据CPU核心数动态调整线程池大小（优化高并发性能）
import os
cpu_count = os.cpu_count() or 4
# 线程池大小 = CPU核心数 * 2，但不超过100
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)

# 尝试导入限流装饰器（如果可用）
try:
    from slowapi import Limiter
    limiter = None  # 将在路由中从 app.state 获取
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False


class BaziRequest(BaseModel):
    """八字计算请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    
    @validator('solar_date')
    def validate_date(cls, v):
        """验证日期格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('solar_time')
    def validate_time(cls, v):
        """验证时间格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        """验证性别"""
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v


class BaziResponse(BaseModel):
    """八字计算响应模型"""
    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None


@router.post("/bazi/calculate", response_model=BaziResponse, summary="计算生辰八字")
async def calculate_bazi(request: BaziRequest, http_request: Request):
    """
    计算生辰八字（带缓存优化）
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    
    返回完整的八字信息和匹配的规则
    """
    try:
        # 检查缓存
        cached_result = bazi_cache.get(
            request.solar_date,
            request.solar_time,
            request.gender
        )
        
        if cached_result is not None:
            # 验证缓存数据的格式
            if not isinstance(cached_result, dict):
                # 缓存数据格式错误，清除缓存
                bazi_cache.clear()
                cached_result = None
            else:
                # 返回缓存结果
                return BaziResponse(
                    success=True,
                    data=cached_result
                )
        
        # 在线程池中执行CPU密集型计算
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziService.calculate_bazi_full,
            request.solar_date,
            request.solar_time,
            request.gender
        )
        
        # 验证结果格式
        if not isinstance(result, dict):
            raise ValueError(f"计算结果格式错误: 期望字典类型，实际是 {type(result)}")
        
        # 缓存结果
        bazi_cache.set(
            request.solar_date,
            request.solar_time,
            request.gender,
            result
        )
        
        return BaziResponse(
            success=True,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        error_trace = traceback.format_exc()
        logger.error(f"计算失败: {str(e)}\n{error_trace}")
        error_detail = f"计算失败: {str(e)}\n{error_trace}"
        raise HTTPException(status_code=500, detail=error_detail)


class BaziInterfaceRequest(BaseModel):
    """八字界面信息请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    name: Optional[str] = Field(None, description="姓名", example="张三")
    location: Optional[str] = Field(None, description="出生地点", example="北京")
    latitude: Optional[float] = Field(None, description="纬度", example=39.90)
    longitude: Optional[float] = Field(None, description="经度", example=116.40)
    
    @validator('solar_date')
    def validate_date(cls, v):
        """验证日期格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('solar_time')
    def validate_time(cls, v):
        """验证时间格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        """验证性别"""
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v


@router.post("/bazi/interface", response_model=BaziResponse, summary="生成八字界面信息")
async def generate_bazi_interface(request: BaziInterfaceRequest, http_request: Request):
    """
    生成八字界面信息（包含命宫、身宫、胎元、胎息、命卦等）
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **name**: 姓名（可选）
    - **location**: 出生地点（可选）
    - **latitude**: 纬度（可选）
    - **longitude**: 经度（可选）
    
    返回完整的八字界面信息（JSON格式）
    """
    try:
        # 检查缓存（包含位置信息）
        cached_result = bazi_cache.get(
            request.solar_date,
            request.solar_time,
            request.gender,
            name=request.name or "",
            location=request.location or "未知地",
            latitude=request.latitude or 39.00,
            longitude=request.longitude or 120.00
        )
        
        if cached_result is not None:
            return BaziResponse(
                success=True,
                data=cached_result
            )
        
        # 在线程池中执行CPU密集型计算
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziInterfaceService.generate_interface_full,
            request.solar_date,
            request.solar_time,
            request.gender,
            request.name or "",
            request.location or "未知地",
            request.latitude or 39.00,
            request.longitude or 120.00
        )
        
        # 缓存结果
        bazi_cache.set(
            request.solar_date,
            request.solar_time,
            request.gender,
            result,
            name=request.name or "",
            location=request.location or "未知地",
            latitude=request.latitude or 39.00,
            longitude=request.longitude or 120.00
        )
        
        return BaziResponse(
            success=True,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        error_trace = traceback.format_exc()
        logger.error(f"生成失败: {str(e)}\n{error_trace}")
        error_detail = f"生成失败: {str(e)}\n{error_trace}"
        raise HTTPException(status_code=500, detail=error_detail)


class BaziDetailRequest(BaseModel):
    """八字详细计算请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    current_time: Optional[str] = Field(None, description="当前时间，格式：YYYY-MM-DD HH:MM，用于计算大运流年，默认为当前系统时间", example="2024-01-01 12:00")
    
    @validator('solar_date')
    def validate_date(cls, v):
        """验证日期格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('solar_time')
    def validate_time(cls, v):
        """验证时间格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        """验证性别"""
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v
    
    @validator('current_time')
    def validate_current_time(cls, v):
        """验证当前时间格式"""
        if v is None:
            return v
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d %H:%M')
        except ValueError:
            raise ValueError('当前时间格式错误，应为 YYYY-MM-DD HH:MM')
        return v


@router.post("/bazi/detail", response_model=BaziResponse, summary="计算详细八字信息（包含大运流年）")
async def calculate_bazi_detail(request: BaziDetailRequest, http_request: Request):
    """
    计算详细八字信息（包含大运流年、流月、流日、流时等）
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **current_time**: 当前时间 (YYYY-MM-DD HH:MM)，用于计算大运流年，可选
    
    返回完整的详细八字信息（包含大运流年序列）
    """
    try:
        from datetime import datetime
        
        # 解析当前时间
        current_time = None
        if request.current_time:
            current_time = datetime.strptime(request.current_time, "%Y-%m-%d %H:%M")
        
        # 检查缓存（包含当前时间）
        current_time_str = request.current_time or datetime.now().strftime("%Y-%m-%d %H:%M")
        cached_result = bazi_cache.get(
            request.solar_date,
            request.solar_time,
            request.gender,
            current_time=current_time_str
        )
        
        if cached_result is not None:
            return BaziResponse(
                success=True,
                data=cached_result
            )
        
        # 在线程池中执行CPU密集型计算
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDetailService.calculate_detail_full,
            request.solar_date,
            request.solar_time,
            request.gender,
            current_time
        )
        
        # 缓存结果
        bazi_cache.set(
            request.solar_date,
            request.solar_time,
            request.gender,
            result,
            current_time=current_time_str
        )
        
        return BaziResponse(
            success=True,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")

