#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运势API接口 - 调用第三方运势API
支持今日运势和本月运势
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

from server.services.fortune_api_service import FortuneAPIService
from server.utils.api_error_handler import api_error_handler

router = APIRouter()


class FortuneRequest(BaseModel):
    """运势请求模型"""
    constellation: Optional[str] = Field(None, description="星座名称（中文），如：白羊座、金牛座等。如果不提供，将根据日期自动计算", example="白羊座")
    date: Optional[str] = Field(None, description="日期（可选，默认为今天），格式：YYYY-MM-DD", example="2025-01-17")
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
    
    @validator('constellation')
    def validate_constellation(cls, v):
        if v is None:
            return v
        valid_constellations = [
            '白羊座', '金牛座', '双子座', '巨蟹座', '狮子座', '处女座',
            '天秤座', '天蝎座', '射手座', '摩羯座', '水瓶座', '双鱼座'
        ]
        if v not in valid_constellations:
            raise ValueError(f'星座名称无效，应为以下之一：{", ".join(valid_constellations)}')
        return v


class MonthlyFortuneRequest(BaseModel):
    """本月运势请求模型"""
    constellation: Optional[str] = Field(None, description="星座名称（中文），如：白羊座、金牛座等。如果不提供，将根据日期自动计算", example="白羊座")
    year: Optional[int] = Field(None, description="年份（可选，默认为今年）", example=2025)
    month: Optional[int] = Field(None, description="月份（可选，默认为本月），1-12", example=1)
    provider: Optional[str] = Field(None, description="API提供商（可选），jisuapi/tianapi/6api，默认自动选择", example="jisuapi")
    
    @validator('month')
    def validate_month(cls, v):
        if v is None:
            return v
        if not (1 <= v <= 12):
            raise ValueError('月份必须在 1-12 之间')
        return v
    
    @validator('constellation')
    def validate_constellation(cls, v):
        if v is None:
            return v
        valid_constellations = [
            '白羊座', '金牛座', '双子座', '巨蟹座', '狮子座', '处女座',
            '天秤座', '天蝎座', '射手座', '摩羯座', '水瓶座', '双鱼座'
        ]
        if v not in valid_constellations:
            raise ValueError(f'星座名称无效，应为以下之一：{", ".join(valid_constellations)}')
        return v


class FortuneResponse(BaseModel):
    """运势响应模型"""
    success: bool
    provider: Optional[str] = None
    constellation: Optional[str] = None
    date: Optional[str] = None
    fortune: Optional[dict] = None
    error: Optional[str] = None


class MonthlyFortuneResponse(BaseModel):
    """本月运势响应模型"""
    success: bool
    provider: Optional[str] = None
    constellation: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    fortune: Optional[dict] = None
    error: Optional[str] = None


@router.post("/fortune/daily", response_model=FortuneResponse, summary="获取今日运势")
@api_error_handler
async def get_daily_fortune(request: FortuneRequest):
    """
    获取今日运势
    
    调用第三方运势API获取今日运势信息，包括：
    - 整体运势
    - 事业运势
    - 爱情运势
    - 财运
    - 健康运势
    - 幸运色、幸运数字等
    
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
    
    - **constellation**: 星座名称（可选），如果不提供则根据日期自动计算
    - **date**: 日期（可选），默认为今天，格式：YYYY-MM-DD
    - **provider**: API提供商（可选），默认自动选择已配置的提供商
    
    返回今日运势分析结果
    """
    service = FortuneAPIService(provider=request.provider)
    result = service.get_daily_fortune(
        constellation=request.constellation,
        date=request.date
    )
    if result.get('success'):
        return FortuneResponse(
            success=True,
            provider=result.get('provider'),
            constellation=result.get('constellation'),
            date=result.get('date'),
            fortune=result.get('fortune')
        )
    return FortuneResponse(
        success=False,
        error=result.get('error', '获取运势失败')
    )


@router.post("/fortune/monthly", response_model=MonthlyFortuneResponse, summary="获取本月运势")
@api_error_handler
async def get_monthly_fortune(request: MonthlyFortuneRequest):
    """
    获取本月运势
    
    调用第三方运势API获取本月运势信息，包括：
    - 整体运势
    - 事业运势
    - 爱情运势
    - 财运
    - 健康运势
    
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
    
    - **constellation**: 星座名称（可选），如果不提供则根据日期自动计算
    - **year**: 年份（可选），默认为今年
    - **month**: 月份（可选），默认为本月，1-12
    - **provider**: API提供商（可选），默认自动选择已配置的提供商
    
    返回本月运势分析结果
    """
    service = FortuneAPIService(provider=request.provider)
    result = service.get_monthly_fortune(
        constellation=request.constellation,
        year=request.year,
        month=request.month
    )
    if result.get('success'):
        return MonthlyFortuneResponse(
            success=True,
            provider=result.get('provider'),
            constellation=result.get('constellation'),
            year=result.get('year'),
            month=result.get('month'),
            fortune=result.get('fortune')
        )
    return MonthlyFortuneResponse(
        success=False,
        error=result.get('error', '获取运势失败')
    )


@router.get("/fortune/providers", summary="获取可用的API提供商")
async def get_providers():
    """
    获取可用的API提供商列表
    
    返回已配置API密钥的提供商列表
    """
    providers = []
    for provider_name, config in FortuneAPIService.API_PROVIDERS.items():
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

