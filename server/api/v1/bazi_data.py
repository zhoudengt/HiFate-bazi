#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据获取接口 - 通过配置参数按需获取数据
支持并行计算、多级缓存和性能优化
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter
from pydantic import BaseModel, Field, validator

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.services.bazi_data_validator import BaziDataValidator
from server.services.bazi_data_cache import BaziDataCache
import asyncio

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


class DayunConfig(BaseModel):
    """大运查询配置"""
    mode: Optional[str] = Field(None, description="查询模式: 'count'(数量), 'current'(当前), 'current_with_neighbors'(当前及前后), 'indices'(索引列表)")
    count: Optional[int] = Field(None, description="数量模式：返回前N个大运")
    indices: Optional[List[int]] = Field(None, description="索引模式：返回指定索引的大运（如[1,2,3]表示第2-4步大运）")
    
    @validator('mode')
    def validate_mode(cls, v):
        if v and v not in ['count', 'current', 'current_with_neighbors', 'indices']:
            raise ValueError("mode 必须是 'count', 'current', 'current_with_neighbors' 或 'indices'")
        return v


class BaziDataRequest(BaziBaseRequest):
    """统一数据获取请求"""
    # 数据模块配置（按需获取）
    modules: Dict[str, Any] = Field(
        default_factory=dict,
        description="数据模块配置，例如: {'dayun': {'mode': 'current_with_neighbors'}, 'rules': {'types': ['shishen']}}"
    )
    
    # 性能配置
    use_cache: bool = Field(True, description="是否使用缓存")
    parallel: bool = Field(True, description="是否并行获取数据")
    timeout: Optional[int] = Field(30, description="超时时间（秒）")
    
    # 数据一致性验证
    verify_consistency: bool = Field(True, description="是否验证数据一致性（与前端页面数据对比）")


class BaziDataResponse(BaseModel):
    """统一数据获取响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="数据内容")
    message: Optional[str] = Field(None, description="消息")
    error: Optional[str] = Field(None, description="错误信息")
    validation_errors: Optional[List[str]] = Field(None, description="数据一致性验证错误列表")


@router.post("/bazi/data", response_model=BaziDataResponse, summary="统一数据获取接口")
async def get_bazi_data(request: BaziDataRequest):
    """
    统一数据获取接口 - 通过配置参数按需获取数据
    
    支持所有数据模块：
    - 基础模块: bazi, wangshuai, xishen_jishen, wuxing
    - 大运流年模块: dayun, liunian, liuyue, special_liunian, fortune_display
    - 规则匹配模块: rules（支持所有规则类型）
    - 分析模块: health, personality, rizhu, wuxing_proportion, liunian_enhanced
    - 辅助模块: deities, branch_relations, career_star, wealth_star, children_star, shengong_minggong
    - 运势模块: daily_fortune, monthly_fortune, daily_fortune_calendar
    - 其他模块: yigua, bazi_interface, bazi_ai
    
    Args:
        request: 统一数据获取请求参数
        
    Returns:
        BaziDataResponse: 包含所有请求模块的数据
    """
    try:
        # 1. 检查缓存
        cached_data = None
        if request.use_cache:
            cached_data = BaziDataCache.get(
                request.solar_date,
                request.solar_time,
                request.gender,
                request.modules
            )
            if cached_data:
                logger.info("缓存命中，直接返回缓存数据")
                return BaziDataResponse(
                    success=True,
                    data=cached_data,
                    message="数据获取成功（来自缓存）"
                )
        
        # 2. 获取数据（支持7个标准参数）
        data = await BaziDataOrchestrator.fetch_data(
            request.solar_date,
            request.solar_time,
            request.gender,
            request.modules,
            use_cache=request.use_cache,
            parallel=request.parallel,
            calendar_type=request.calendar_type,
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        # 3. 数据一致性验证
        validation_errors = []
        if request.verify_consistency:
            is_consistent, errors = BaziDataValidator.validate_consistency(data)
            if not is_consistent:
                validation_errors = errors
                logger.warning(f"数据一致性验证失败: {errors}")
        
        # 4. 设置缓存
        if request.use_cache and cached_data is None:
            BaziDataCache.set(
                request.solar_date,
                request.solar_time,
                request.gender,
                request.modules,
                data
            )
        
        # 5. 返回结果
        return BaziDataResponse(
            success=True,
            data=data,
            message="数据获取成功",
            validation_errors=validation_errors if validation_errors else None
        )
    
    except Exception as e:
        logger.error(f"获取数据失败: {e}", exc_info=True)
        return BaziDataResponse(
            success=False,
            error=str(e),
            message="数据获取失败"
        )

