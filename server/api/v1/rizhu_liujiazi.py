#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日元-六十甲子 API - 根据生辰查询日柱解析
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.rizhu_liujiazi_service import RizhuLiujiaziService
from server.services.bazi_service import BaziService
from server.utils.data_validator import validate_bazi_data

router = APIRouter()

# 线程池
import os
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


class RizhuLiujiaziRequest(BaseModel):
    """日元-六十甲子请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    
    @validator('solar_date')
    def validate_solar_date(cls, v):
        """验证日期格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('solar_time')
    def validate_solar_time(cls, v):
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


class RizhuLiujiaziResponse(BaseModel):
    """日元-六十甲子响应模型"""
    success: bool
    data: Optional[dict] = None  # {id, rizhu, analysis}
    error: Optional[str] = None


@router.post("/bazi/rizhu-liujiazi", response_model=RizhuLiujiaziResponse, summary="查询日元-六十甲子解析")
async def get_rizhu_liujiazi(request: RizhuLiujiaziRequest):
    """
    根据用户生辰查询日柱对应的六十甲子解析
    
    流程：
    1. 调用八字排盘服务获取日柱（bazi_pillars.day.stem + bazi_pillars.day.branch）
    2. 根据日柱查询数据库获取解析内容
    3. 返回ID、日柱、解析内容
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    
    返回日柱解析结果（包含【基础信息】、【深度解读】、【断语展示】等）
    """
    try:
        # 在线程池中执行CPU密集型计算
        loop = asyncio.get_event_loop()
        
        # 1. 获取八字排盘结果
        bazi_result = await loop.run_in_executor(
            executor,
            BaziService.calculate_bazi_full,
            request.solar_date,
            request.solar_time,
            request.gender
        )
        
        if not bazi_result:
            return RizhuLiujiaziResponse(
                success=False,
                error="八字排盘失败"
            )
        
        # 2. 提取日柱
        bazi_data = bazi_result.get('bazi', {})
        bazi_data = validate_bazi_data(bazi_data)
        
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        day_pillar = bazi_pillars.get('day', {})
        
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        
        if not day_stem or not day_branch:
            return RizhuLiujiaziResponse(
                success=False,
                error="无法获取日柱信息"
            )
        
        rizhu = f"{day_stem}{day_branch}"
        
        # 3. 查询日柱解析
        analysis_data = await loop.run_in_executor(
            executor,
            RizhuLiujiaziService.get_rizhu_analysis,
            rizhu
        )
        
        if not analysis_data:
            return RizhuLiujiaziResponse(
                success=False,
                error=f"未找到日柱 {rizhu} 的解析内容"
            )
        
        return RizhuLiujiaziResponse(
            success=True,
            data=analysis_data
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"查询失败: {str(e)}\n{traceback.format_exc()}"
        )

