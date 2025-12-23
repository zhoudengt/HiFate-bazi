#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今日运势分析 API - 类似 FateTell 的"日运日签"功能
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

from server.services.daily_fortune_service import DailyFortuneService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor

router = APIRouter()

# 线程池
import os
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


class DailyFortuneRequest(BaziBaseRequest):
    """今日运势分析请求模型"""
    target_date: Optional[str] = Field(None, description="目标日期（可选，默认为今天），格式：YYYY-MM-DD", example="2025-01-17")
    use_llm: Optional[bool] = Field(False, description="是否使用 LLM 生成（可选，默认使用规则匹配）", example=False)
    access_token: Optional[str] = Field(None, description="Coze Access Token（可选，use_llm=True 时需要）")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，use_llm=True 时需要）")
    
    @validator('target_date')
    def validate_target_date(cls, v):
        if v is None:
            return v
        from datetime import datetime
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('目标日期格式错误，应为 YYYY-MM-DD')
        return v


class DailyFortuneResponse(BaseModel):
    """今日运势分析响应模型"""
    success: bool
    target_date: Optional[str] = None
    fortune: Optional[dict] = None
    liuri_info: Optional[dict] = None
    bazi_data: Optional[dict] = None
    matched_rules_count: Optional[int] = None
    error: Optional[str] = None


@router.post("/bazi/daily-fortune", response_model=DailyFortuneResponse, summary="今日运势分析（类似 FateTell 的日运日签）")
async def get_daily_fortune(request: DailyFortuneRequest):
    """
    获取今日运势分析（类似 FateTell 的"日运日签"功能）
    
    结合用户的八字信息和当前日期（或指定日期），分析该日的运势。
    
    特点：
    - 结合流年、流月、流日信息
    - 分析事业、财运、感情、健康等各个方面
    - 支持规则匹配和 LLM 生成两种模式
    - 快速响应（规则匹配模式 <1秒）
    
    适用场景：
    - 每日运势查询
    - 特定日期运势分析
    - 决策参考
    
    - **solar_date**: 用户出生日期（阳历）(YYYY-MM-DD)
    - **solar_time**: 用户出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **target_date**: 目标日期（可选，默认为今天）(YYYY-MM-DD)
    - **use_llm**: 是否使用 LLM 生成（可选，默认使用规则匹配）
    - **access_token**: Coze Access Token（可选，use_llm=True 时需要）
    - **bot_id**: Coze Bot ID（可选，use_llm=True 时需要）
    
    返回今日运势分析结果
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
            DailyFortuneService.calculate_daily_fortune,
            final_solar_date,
            final_solar_time,
            request.gender,
            request.target_date,
            request.use_llm,
            request.access_token,
            request.bot_id
        )
        
        # 添加转换信息到结果
        if result and isinstance(result, dict) and result.get('success') and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
            if 'fortune' in result:
                result['fortune']['conversion_info'] = conversion_info
            else:
                result['conversion_info'] = conversion_info
        
        if result.get('success'):
            return DailyFortuneResponse(
                success=True,
                target_date=result.get('target_date'),
                fortune=result.get('fortune'),
                liuri_info=result.get('liuri_info'),
                bazi_data=result.get('bazi_data'),
                matched_rules_count=result.get('matched_rules_count')
            )
        else:
            return DailyFortuneResponse(
                success=False,
                error=result.get('error', '计算失败')
            )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}\n{traceback.format_exc()}")

