#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字AI分析API接口
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.bazi_ai_service import BaziAIService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.api_error_handler import api_error_handler
from server.utils.async_executor import get_executor

router = APIRouter()


class BaziAIRequest(BaziBaseRequest):
    """八字AI分析请求模型"""
    user_question: Optional[str] = Field(None, description="用户的问题或分析需求", example="请分析我的财运和事业")
    access_token: Optional[str] = Field(None, description="Coze Access Token，如果不提供则使用环境变量 COZE_ACCESS_TOKEN", example="pat_...")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID，如果不提供则使用环境变量 COZE_BOT_ID", example="1234567890")
    api_base: Optional[str] = Field(None, description="Coze API 基础URL，默认 https://api.coze.cn/v1", example="https://api.coze.cn/v1")
    include_rizhu_analysis: Optional[bool] = Field(True, description="是否包含日柱性别分析结果", example=True)


class BaziAIResponse(BaseModel):
    """八字AI分析响应模型"""
    success: bool
    bazi_data: Optional[dict] = None
    ai_analysis: Optional[dict] = None
    rizhu_analysis: Optional[str] = None
    polished_rules: Optional[str] = Field(None, description="大模型润色后的规则内容")
    polished_rules_info: Optional[dict] = Field(None, description="润色前后的对比信息，包含原始内容、润色后内容和修改列表")
    error: Optional[str] = None


@router.post("/bazi/ai-analyze", response_model=BaziAIResponse, summary="Coze AI分析八字")
@api_error_handler
async def analyze_bazi_with_ai(request: BaziAIRequest):
    """
    调用八字接口获取数据，然后使用Coze AI进行分析
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **user_question**: 用户的问题或分析需求（可选）
    - **access_token**: Coze Access Token（可选，不提供则使用环境变量 COZE_ACCESS_TOKEN）
    - **bot_id**: Coze Bot ID（可选，不提供则使用环境变量 COZE_BOT_ID）
    - **api_base**: Coze API 基础URL（可选，默认 https://api.coze.cn/v1）
    - **include_rizhu_analysis**: 是否包含日柱性别分析结果（可选，默认 True）
    
    返回八字数据和Coze AI分析结果
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        get_executor(),
        BaziAIService.analyze_bazi_with_ai,
        request.solar_date,
        request.solar_time,
        request.gender,
        request.user_question,
        request.access_token,
        request.bot_id,
        request.api_base,
        request.include_rizhu_analysis
    )
    return BaziAIResponse(
        success=result.get('success', False),
        bazi_data=result.get('bazi_data'),
        ai_analysis=result.get('ai_analysis'),
        rizhu_analysis=result.get('rizhu_analysis'),
        polished_rules=result.get('polished_rules'),
        polished_rules_info=result.get('polished_rules_info'),
        error=result.get('error')
    )

