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
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result, L2_TTL
)

logger = logging.getLogger(__name__)

router = APIRouter()


class WangShuaiRequest(BaziBaseRequest):
    """旺衰计算请求"""
    pass


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
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当calendar_type=lunar时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    """
    logger.info(f"📥 收到旺衰计算请求: {request.solar_date} {request.solar_time} {request.gender}")
    
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
        
        # >>> 缓存检查（旺衰固定，不随时间变化）<<<
        cache_key = generate_cache_key("wangshuai", final_solar_date, final_solar_time, request.gender)
        cached = get_cached_result(cache_key, "wangshuai")
        if cached:
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                if 'data' in cached:
                    cached['data']['conversion_info'] = conversion_info
                else:
                    cached['conversion_info'] = conversion_info
            return WangShuaiResponse(**cached)
        # >>> 缓存检查结束 <<<
        
        result = WangShuaiService.calculate_wangshuai(
            final_solar_date,
            final_solar_time,
            request.gender
        )
        
        # >>> 缓存写入 <<<
        if result.get('success'):
            set_cached_result(cache_key, result, L2_TTL)
        # >>> 缓存写入结束 <<<
        
        # 添加转换信息到结果
        if result.get('success') and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
            if 'data' in result:
                result['data']['conversion_info'] = conversion_info
            else:
                result['conversion_info'] = conversion_info
        
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

