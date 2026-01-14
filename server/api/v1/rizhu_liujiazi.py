#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日元-六十甲子 API - 根据生辰查询日柱解析
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

from server.services.rizhu_liujiazi_service import RizhuLiujiaziService
from server.services.bazi_service import BaziService
from server.utils.data_validator import validate_bazi_data
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result, L2_TTL
)

router = APIRouter()

# 线程池
import os
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


class RizhuLiujiaziRequest(BaziBaseRequest):
    """日元-六十甲子请求模型"""
    pass


class RizhuLiujiaziResponse(BaseModel):
    """日元-六十甲子响应模型"""
    success: bool
    data: Optional[dict] = None  # {id, rizhu, analysis}
    error: Optional[str] = None


@router.post("/bazi/rizhu-liujiazi", response_model=RizhuLiujiaziResponse, summary="查询日元-六十甲子解析")
async def get_rizhu_liujiazi(request: RizhuLiujiaziRequest):
    """
    根据用户生辰查询日柱对应的六十甲子解析
    
    流程：
    1. 调用八字排盘服务获取日柱（bazi_pillars.day.stem + bazi_pillars.day.branch）
    2. 根据日柱查询数据库获取解析内容
    3. 返回ID、日柱、解析内容
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    
    返回日柱解析结果（包含【基础信息】、【深度解读】、【断语展示】等）
    """
    try:
        # 在线程池中执行CPU密集型计算
        loop = asyncio.get_event_loop()
        
        # 0. 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # >>> 缓存检查（日柱固定，不随时间变化）<<<
        cache_key = generate_cache_key("rizhu", final_solar_date, final_solar_time, request.gender)
        cached = get_cached_result(cache_key, "rizhu-liujiazi")
        if cached:
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                cached['conversion_info'] = conversion_info
            return RizhuLiujiaziResponse(success=True, data=cached)
        # >>> 缓存检查结束 <<<
        
        # 1. 获取八字排盘结果
        bazi_result = await loop.run_in_executor(
            executor,
            BaziService.calculate_bazi_full,
            final_solar_date,
            final_solar_time,
            request.gender
        )
        
        if not bazi_result:
            return RizhuLiujiaziResponse(
                success=False,
                error="八字排盘失败"
            )
        
        # 2. 提取日柱
        bazi_data = bazi_result.get('bazi', {})
        bazi_data = validate_bazi_data(bazi_data)
        
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        day_pillar = bazi_pillars.get('day', {})
        
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        
        if not day_stem or not day_branch:
            return RizhuLiujiaziResponse(
                success=False,
                error="无法获取日柱信息"
            )
        
        rizhu = f"{day_stem}{day_branch}"
        
        # 3. 查询日柱解析
        analysis_data = await loop.run_in_executor(
            executor,
            RizhuLiujiaziService.get_rizhu_analysis,
            rizhu
        )
        
        if not analysis_data:
            # 添加详细的错误信息，帮助排查问题
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"未找到日柱 {rizhu} 的解析内容（日期: {request.solar_date}, 时间: {request.solar_time}, 性别: {request.gender}）")
            
            # 尝试获取数据库中的总记录数（用于诊断）
            try:
                total_count = await loop.run_in_executor(
                    executor,
                    RizhuLiujiaziService.get_total_count
                )
                logger.warning(f"当前数据库中总记录数: {total_count}")
            except:
                pass
            
            return RizhuLiujiaziResponse(
                success=False,
                error=f"未找到日柱 {rizhu} 的解析内容。请检查数据库中是否有该日柱的数据。"
            )
        
        # >>> 缓存写入 <<<
        if analysis_data and isinstance(analysis_data, dict):
            set_cached_result(cache_key, analysis_data, L2_TTL)
        # >>> 缓存写入结束 <<<
        
        # 添加转换信息到结果（如果有转换）
        if analysis_data and isinstance(analysis_data, dict) and conversion_info and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
            analysis_data['conversion_info'] = conversion_info
        
        return RizhuLiujiaziResponse(
            success=True,
            data=analysis_data
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"查询失败: {str(e)}\n{traceback.format_exc()}"
        )

