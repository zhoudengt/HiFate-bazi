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

router = APIRouter()


class MonthlyFortuneRequest(BaseModel):
    """月运势请求模型"""
    solar_date: str = Field(..., description="阳历出生日期，格式：YYYY-MM-DD")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM")
    gender: str = Field(..., description="性别：male/female")
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
        result = MonthlyFortuneService.calculate_monthly_fortune(
            solar_date=request.solar_date,
            solar_time=request.solar_time,
            gender=request.gender,
            target_month=request.target_month,
            use_llm=request.use_llm,
            access_token=request.access_token,
            bot_id=request.bot_id
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '月运势计算失败'))
        
        return result
        
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"月运势计算异常: {str(e)}\n{traceback.format_exc()}"
        )

