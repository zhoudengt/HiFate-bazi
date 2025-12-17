#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日运势日历API接口
基于万年历接口，提供完整的每日运势信息
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.daily_fortune_calendar_service import DailyFortuneCalendarService

router = APIRouter()


class DailyFortuneCalendarRequest(BaseModel):
    """每日运势日历请求模型"""
    date: Optional[str] = Field(None, description="日期（可选，默认为今天），格式：YYYY-MM-DD", example="2025-01-15")
    solar_date: Optional[str] = Field(None, description="用户生辰阳历日期（可选，用于十神提示），格式：YYYY-MM-DD", example="1990-01-15")
    solar_time: Optional[str] = Field(None, description="用户生辰时间（可选），格式：HH:MM", example="12:00")
    gender: Optional[str] = Field(None, description="用户性别（可选），male/female", example="male")
    
    @validator('date')
    def validate_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('solar_date')
    def validate_solar_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('用户生辰日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('solar_time')
    def validate_solar_time(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('用户生辰时间格式错误，应为 HH:MM')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v is None:
            return v
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v


class DailyFortuneCalendarResponse(BaseModel):
    """每日运势日历响应模型"""
    success: bool
    # 基础万年历信息
    solar_date: Optional[str] = None  # 当前阳历日期
    lunar_date: Optional[str] = None  # 当前阴历日期
    weekday: Optional[str] = None  # 星期几（中文）
    weekday_en: Optional[str] = None  # 星期几（英文）
    # 流年流月流日
    liunian: Optional[str] = None  # 流年：甲辰年
    liuyue: Optional[str] = None  # 流月：戊子月
    liuri: Optional[str] = None  # 流日：乙卯日
    # 万年历信息
    yi: Optional[List[str]] = None  # 宜
    ji: Optional[List[str]] = None  # 忌
    luck_level: Optional[str] = None  # 吉凶等级
    deities: Optional[Dict[str, Any]] = None  # 神煞方位（喜神、财神、福神）
    chong_he_sha: Optional[Dict[str, Any]] = None  # 冲合煞（冲、合、煞）
    jianchu: Optional[str] = None  # 建除十二神
    # 运势内容
    jiazi_fortune: Optional[str] = None  # 整体运势（六十甲子）
    shishen_hint: Optional[str] = None  # 十神提示（需要用户生辰）
    zodiac_relations: Optional[str] = None  # 生肖简运
    jianchu_summary: Optional[str] = None  # 能量小结
    error: Optional[str] = None


@router.post("/daily-fortune-calendar/query", response_model=DailyFortuneCalendarResponse, summary="查询每日运势日历")
async def query_daily_fortune_calendar(request: DailyFortuneCalendarRequest):
    """
    查询每日运势日历信息
    
    基于万年历接口，提供完整的每日运势信息，包括：
    - 基础万年历信息（阳历、阴历、星期、宜忌、吉凶等级、神煞方位、冲合煞、建除）
    - 流年、流月、流日（格式：甲辰年、戊子月、乙卯日）
    - 整体运势（根据甲子日匹配六十甲子运势）
    - 十神提示（根据日干与用户生辰日干计算，需要用户生辰信息）
    - 生肖简运（根据日支匹配生肖刑冲破害）
    - 能量小结（根据建除十二神匹配）
    
    **参数说明**：
    - **date**: 查询日期（可选，默认为今天），格式：YYYY-MM-DD
    - **solar_date**: 用户生辰阳历日期（可选，用于十神提示），格式：YYYY-MM-DD
    - **solar_time**: 用户生辰时间（可选），格式：HH:MM
    - **gender**: 用户性别（可选），male/female
    
    **注意**：
    - 如果未提供用户生辰信息，十神提示将为空
    - 所有运势数据从数据库读取，不直接读取Excel文件
    
    返回完整的每日运势信息
    """
    try:
        result = DailyFortuneCalendarService.get_daily_fortune_calendar(
            date_str=request.date,
            user_solar_date=request.solar_date,
            user_solar_time=request.solar_time,
            user_gender=request.gender
        )
        
        if result.get('success'):
            return DailyFortuneCalendarResponse(
                success=True,
                solar_date=result.get('solar_date'),
                lunar_date=result.get('lunar_date'),
                weekday=result.get('weekday'),
                weekday_en=result.get('weekday_en'),
                liunian=result.get('liunian'),
                liuyue=result.get('liuyue'),
                liuri=result.get('liuri'),
                yi=result.get('yi', []),
                ji=result.get('ji', []),
                luck_level=result.get('luck_level'),
                deities=result.get('deities', {}),
                chong_he_sha=result.get('chong_he_sha', {}),
                jianchu=result.get('jianchu'),
                jiazi_fortune=result.get('jiazi_fortune'),
                shishen_hint=result.get('shishen_hint'),
                zodiac_relations=result.get('zodiac_relations'),
                jianchu_summary=result.get('jianchu_summary')
            )
        else:
            return DailyFortuneCalendarResponse(
                success=False,
                error=result.get('error', '获取每日运势失败')
            )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"查询每日运势异常: {str(e)}\n{traceback.format_exc()}"
        )

