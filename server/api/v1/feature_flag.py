#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能开关 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, List
import logging

from server.utils.feature_flag import (
    get_feature_flag_manager,
    FeatureFlag,
    FlagType
)

router = APIRouter()
logger = logging.getLogger(__name__)


class FeatureFlagCreateRequest(BaseModel):
    """创建功能开关请求"""
    name: str
    description: str
    enabled: bool = False
    flag_type: str  # "boolean", "percentage", "whitelist", "blacklist"
    value: Optional[Any] = None


class FeatureFlagToggleRequest(BaseModel):
    """切换功能开关请求"""
    enabled: bool


class CheckFlagRequest(BaseModel):
    """检查功能开关请求"""
    flag_name: str
    user_id: Optional[str] = None


@router.post("/feature-flags")
async def create_feature_flag(request: FeatureFlagCreateRequest):
    """创建功能开关"""
    try:
        manager = get_feature_flag_manager()
        
        flag = FeatureFlag(
            name=request.name,
            description=request.description,
            enabled=request.enabled,
            flag_type=FlagType(request.flag_type),
            value=request.value
        )
        
        success = manager.create_flag(flag)
        if not success:
            raise HTTPException(status_code=400, detail="创建功能开关失败")
        
        return {
            "success": True,
            "flag": {
                "name": flag.name,
                "enabled": flag.enabled,
                "flag_type": flag.flag_type.value
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的参数: {e}")
    except Exception as e:
        logger.error(f"创建功能开关失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feature-flags/{flag_name}")
async def get_feature_flag(flag_name: str):
    """获取功能开关"""
    manager = get_feature_flag_manager()
    flag = manager.get_flag(flag_name)
    
    if not flag:
        raise HTTPException(status_code=404, detail="功能开关不存在")
    
    return {
        "success": True,
        "flag": {
            "name": flag.name,
            "description": flag.description,
            "enabled": flag.enabled,
            "flag_type": flag.flag_type.value,
            "value": flag.value
        }
    }


@router.post("/feature-flags/{flag_name}/toggle")
async def toggle_feature_flag(flag_name: str, request: FeatureFlagToggleRequest):
    """切换功能开关状态"""
    manager = get_feature_flag_manager()
    manager.toggle_flag(flag_name, request.enabled)
    
    return {
        "success": True,
        "message": f"功能开关已{'启用' if request.enabled else '禁用'}"
    }


@router.post("/feature-flags/check")
async def check_feature_flag(request: CheckFlagRequest):
    """检查功能开关是否启用"""
    manager = get_feature_flag_manager()
    enabled = manager.is_enabled(request.flag_name, request.user_id)
    
    return {
        "success": True,
        "flag_name": request.flag_name,
        "enabled": enabled
    }

