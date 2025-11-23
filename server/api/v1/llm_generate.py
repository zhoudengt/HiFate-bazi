#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 生成模式 API - 类似 FateTell 的实时生成
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

from server.services.llm_generate_service import LLMGenerateService

router = APIRouter()

# 线程池
import os
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


class LLMGenerateRequest(BaseModel):
    """LLM 生成请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    user_question: Optional[str] = Field(None, description="用户问题或分析需求（可选）", example="我想了解我的事业运势")
    access_token: Optional[str] = Field(None, description="Coze Access Token（可选）")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选）")
    api_base: Optional[str] = Field(None, description="Coze API 基础URL（可选）")
    
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


class LLMGenerateResponse(BaseModel):
    """LLM 生成响应模型"""
    success: bool
    report: Optional[str] = None
    bazi_data: Optional[dict] = None
    prompt_length: Optional[int] = None
    report_length: Optional[int] = None
    error: Optional[str] = None
    error_detail: Optional[str] = None  # 原始错误信息（供调试）
    suggestion: Optional[str] = None  # 建议的替代方案


@router.post("/bazi/llm-generate", response_model=LLMGenerateResponse, summary="LLM 生成完整报告（类似 FateTell）")
async def generate_llm_report(request: LLMGenerateRequest):
    """
    使用 LLM 直接生成完整的命理报告（类似 FateTell 的实时生成模式）
    
    与规则匹配模式的区别：
    - 规则匹配模式：从规则库中匹配规则，然后精选和拼装
    - LLM 生成模式：使用 LLM 直接生成完整报告，每次生成都不同
    
    适用场景：
    - 需要完全个性化的报告
    - 需要连贯的整篇文章（而非规则片段拼接）
    - 需要结合用户具体问题生成针对性内容
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **user_question**: 用户问题或分析需求（可选）
    - **access_token**: Coze Access Token（可选，不提供则使用环境变量）
    - **bot_id**: Coze Bot ID（可选，不提供则使用环境变量）
    - **api_base**: Coze API 基础URL（可选）
    
    返回 LLM 生成的完整报告
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            LLMGenerateService.generate_report,
            request.solar_date,
            request.solar_time,
            request.gender,
            request.user_question,
            request.access_token,
            request.bot_id,
            request.api_base
        )
        
        if result.get('success'):
            return LLMGenerateResponse(
                success=True,
                report=result.get('report'),
                bazi_data=result.get('bazi_data'),
                prompt_length=result.get('prompt_length'),
                report_length=result.get('report_length')
            )
        else:
            # 返回友好的错误信息，而不是直接抛出异常
            return LLMGenerateResponse(
                success=False,
                error=result.get('error', '生成失败'),
                error_detail=result.get('error_detail'),
                suggestion=result.get('suggestion'),
                bazi_data=result.get('bazi_data')
            )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"生成异常: {str(e)}\n{traceback.format_exc()}")

