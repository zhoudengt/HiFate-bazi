#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月运势API - 基于八字的本月运势分析
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.monthly_fortune_service import MonthlyFortuneService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result, L2_TTL, get_current_month_str
)

router = APIRouter()


class MonthlyFortuneRequest(BaziBaseRequest):
    """月运势请求模型"""
    target_month: Optional[str] = Field(None, description="目标月份，格式：YYYY-MM，默认为本月")
    use_llm: bool = Field(False, description="是否使用LLM生成")
    access_token: Optional[str] = Field(None, description="Coze Access Token（use_llm=True时需要）")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（use_llm=True时需要）")


@router.post("/bazi/monthly-fortune")
async def calculate_monthly_fortune(request: MonthlyFortuneRequest):
    """
    计算月运势（基于八字）
    
    Args:
        request: 月运势请求数据
        
    Returns:
        dict: 包含月运势分析结果
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
        
        # >>> 缓存检查（月运按目标月份缓存，不使用 LLM 时缓存）<<<
        target_month = request.target_month or get_current_month_str()
        cache_key = None
        if not request.use_llm:
            cache_key = generate_cache_key("monthlyfortune", final_solar_date, final_solar_time, request.gender, target_month)
            cached = get_cached_result(cache_key, "monthly-fortune")
            if cached:
                if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                    if 'fortune' in cached:
                        cached['fortune']['conversion_info'] = conversion_info
                    else:
                        cached['conversion_info'] = conversion_info
                return cached
        # >>> 缓存检查结束 <<<
        
        result = MonthlyFortuneService.calculate_monthly_fortune(
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=request.gender,
            target_month=request.target_month,
            use_llm=request.use_llm,
            access_token=request.access_token,
            bot_id=request.bot_id
        )
        
        # >>> 缓存写入（仅非 LLM 模式）<<<
        if result.get('success') and not request.use_llm and cache_key:
            set_cached_result(cache_key, result, L2_TTL)
        # >>> 缓存写入结束 <<<
        
        # 添加转换信息到结果
        if result and isinstance(result, dict) and result.get('success') and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
            if 'fortune' in result:
                result['fortune']['conversion_info'] = conversion_info
            else:
                result['conversion_info'] = conversion_info
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '月运势计算失败'))
        
        return result
        
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"月运势计算异常: {str(e)}\n{traceback.format_exc()}"
        )

