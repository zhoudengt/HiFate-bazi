#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流年大运增强分析API
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from server.services.liunian_enhanced_service import LiunianEnhancedService

logger = logging.getLogger(__name__)

router = APIRouter()


class LiunianEnhancedRequest(BaseModel):
    """流年大运增强分析请求模型"""
    solar_date: str = Field(..., description="出生日期，格式 YYYY-MM-DD")
    solar_time: str = Field(..., description="出生时间，格式 HH:MM")
    gender: str = Field(..., description="性别，male/female")
    target_year: Optional[int] = Field(None, description="目标年份（可选），用于分析特定年份")
    years_ahead: int = Field(10, description="预测未来多少年，默认10年")


class LiunianEnhancedResponse(BaseModel):
    """流年大运增强分析响应模型"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/bazi/liunian-enhanced", response_model=LiunianEnhancedResponse, summary="流年大运增强分析")
async def analyze_liunian_enhanced(request: LiunianEnhancedRequest):
    """
    流年大运增强分析
    
    功能包括：
    - 流年吉凶量化评分（0-100分）
    - 大运转折点识别
    - 流年与命局互动分析
    - 关键时间节点预测
    """
    logger.info(f"📥 收到流年大运增强分析请求: {request.solar_date} {request.solar_time} {request.gender}")
    
    try:
        result = LiunianEnhancedService.analyze_liunian_enhanced(
            solar_date=request.solar_date,
            solar_time=request.solar_time,
            gender=request.gender,
            target_year=request.target_year,
            years_ahead=request.years_ahead
        )
        
        if not result.get('success'):
            logger.error(f"❌ 流年大运增强分析失败: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        logger.info(f"✅ 流年大运增强分析成功")
        return LiunianEnhancedResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 流年大运增强分析API异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析异常: {str(e)}")

