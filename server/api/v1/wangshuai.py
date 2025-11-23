#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旺衰分析API路由
"""

import logging
import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.wangshuai_service import WangShuaiService

logger = logging.getLogger(__name__)

router = APIRouter()


class WangShuaiRequest(BaseModel):
    """旺衰计算请求"""
    solar_date: str = Field(..., description="出生日期 (YYYY-MM-DD)", example="1987-01-07")
    solar_time: str = Field(..., description="出生时间 (HH:MM)", example="09:55")
    gender: str = Field(..., description="性别 (male/female)", example="male")


class WangShuaiResponse(BaseModel):
    """旺衰计算响应"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/bazi/wangshuai", response_model=WangShuaiResponse, summary="计算命局旺衰")
async def calculate_wangshuai(request: WangShuaiRequest):
    """
    计算命局旺衰
    
    根据八字信息计算：
    - 得令分（月支权重）：45分或0分
    - 得地分（年日时支）：根据藏干匹配计分
    - 得势分（天干生扶）：10分或0分 ✅ 修正为10分
    
    最终判定：极旺、身旺、身弱、极弱、平衡
    并计算喜神和忌神的五行
    """
    logger.info(f"📥 收到旺衰计算请求: {request.solar_date} {request.solar_time} {request.gender}")
    
    try:
        result = WangShuaiService.calculate_wangshuai(
            request.solar_date,
            request.solar_time,
            request.gender
        )
        
        if not result['success']:
            logger.error(f"❌ 旺衰计算失败: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))
        
        logger.info(f"✅ 旺衰计算成功，返回结果")
        return WangShuaiResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 旺衰API异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}")

