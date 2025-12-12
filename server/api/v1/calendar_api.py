#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万年历API接口 - 调用第三方万年历API
支持查询指定日期的万年历信息
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.calendar_api_service import CalendarAPIService

router = APIRouter()


class CalendarRequest(BaseModel):
    """万年历请求模型"""
    date: Optional[str] = Field(None, description="日期（可选，默认为今天），格式：YYYY-MM-DD", example="2024-11-14")
    provider: Optional[str] = Field(None, description="API提供商（可选），jisuapi/tianapi/6api，默认自动选择", example="jisuapi")
    
    @validator('date')
    def validate_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v


class CalendarResponse(BaseModel):
    """万年历响应模型"""
    success: bool
    provider: Optional[str] = None
    date: Optional[str] = None
    solar_date: Optional[str] = None
    weekday: Optional[str] = None
    weekday_en: Optional[str] = None
    lunar_date: Optional[str] = None
    ganzhi: Optional[dict] = None
    yi: Optional[list] = None
    ji: Optional[list] = None
    luck_level: Optional[str] = None
    deities: Optional[dict] = None
    chong_he_sha: Optional[dict] = None
    error: Optional[str] = None


@router.post("/calendar/query", response_model=CalendarResponse, summary="查询万年历")
async def query_calendar(request: CalendarRequest):
    """
    查询万年历信息
    
    调用第三方万年历API或本地计算获取指定日期的万年历信息，包括：
    - 公历日期
    - 星期几（中文和英文）
    - 农历日期
    - 干支（年、月、日）
    - 宜忌（宜做什么、忌做什么）
    - 吉凶（大凶/大吉等）
    - 神煞方位（福神、财神、喜神）
    - 冲合煞（冲、合、煞）
    
    **支持的API提供商：**
    - 极速数据 (jisuapi) - 需要配置 JISUAPI_KEY
    - 天聚数行 (tianapi) - 需要配置 TIANAPI_KEY
    - 六派数据 (6api) - 需要配置 API6API_KEY
    
    **环境变量配置：**
    ```bash
    # 选择其中一个配置即可
    export JISUAPI_KEY="your_api_key"
    # 或
    export TIANAPI_KEY="your_api_key"
    # 或
    export API6API_KEY="your_api_key"
    ```
    
    **注意**：如果未配置API密钥，将使用本地计算模式（仅提供农历和干支信息）
    
    - **date**: 日期（可选），默认为今天，格式：YYYY-MM-DD
    - **provider**: API提供商（可选），默认自动选择已配置的提供商
    
    返回万年历信息
    """
    try:
        service = CalendarAPIService(provider=request.provider)
        result = service.get_calendar(date=request.date)
        
        if result.get('success'):
            return CalendarResponse(
                success=True,
                provider=result.get('provider'),
                date=result.get('date'),
                solar_date=result.get('solar_date'),
                weekday=result.get('weekday'),
                weekday_en=result.get('weekday_en'),
                lunar_date=result.get('lunar_date'),
                ganzhi=result.get('ganzhi'),
                yi=result.get('yi', []),
                ji=result.get('ji', []),
                luck_level=result.get('luck_level'),
                deities=result.get('deities'),
                chong_he_sha=result.get('chong_he_sha')
            )
        else:
            return CalendarResponse(
                success=False,
                error=result.get('error', '获取万年历失败')
            )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"查询万年历异常: {str(e)}\n{traceback.format_exc()}"
        )


@router.get("/calendar/providers", summary="获取可用的API提供商")
async def get_calendar_providers():
    """
    获取可用的万年历API提供商列表
    
    返回已配置API密钥的提供商列表
    """
    providers = []
    for provider_name, config in CalendarAPIService.API_PROVIDERS.items():
        api_key = os.getenv(config['api_key_env'])
        providers.append({
            'name': provider_name,
            'display_name': config['name'],
            'configured': api_key is not None,
            'api_key_env': config['api_key_env']
        })
    
    return {
        'success': True,
        'providers': providers
    }
