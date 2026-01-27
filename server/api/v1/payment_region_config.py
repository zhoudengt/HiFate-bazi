#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付区域配置管理 API
提供区域配置的查询和更新接口
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services.payment_service.payment_region_config_manager import get_region_config_manager

router = APIRouter()


class RegionStatusRequest(BaseModel):
    """设置区域状态请求"""
    is_open: bool = Field(..., description="是否开放：true=开放，false=关闭")


@router.get("/payment/regions", summary="获取所有区域配置")
def get_all_regions():
    """
    获取所有区域配置列表
    """
    try:
        region_manager = get_region_config_manager()
        open_regions = region_manager.get_open_regions()
        closed_regions = region_manager.get_closed_regions()
        
        return {
            "success": True,
            "open_regions": open_regions,
            "closed_regions": closed_regions,
            "total": len(open_regions) + len(closed_regions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取区域配置失败: {str(e)}")


@router.get("/payment/regions/open", summary="获取开放的区域列表")
def get_open_regions():
    """
    获取所有开放的区域列表
    """
    try:
        region_manager = get_region_config_manager()
        open_regions = region_manager.get_open_regions()
        
        return {
            "success": True,
            "regions": open_regions,
            "count": len(open_regions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取开放区域失败: {str(e)}")


@router.get("/payment/regions/closed", summary="获取关闭的区域列表")
def get_closed_regions():
    """
    获取所有关闭的区域列表
    """
    try:
        region_manager = get_region_config_manager()
        closed_regions = region_manager.get_closed_regions()
        
        return {
            "success": True,
            "regions": closed_regions,
            "count": len(closed_regions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取关闭区域失败: {str(e)}")


@router.put("/payment/regions/{region_code}/open", summary="设置区域为开放")
def set_region_open(region_code: str):
    """
    设置区域为开放状态
    
    Args:
        region_code: 区域代码（如：HK, TW, CN等）
    """
    try:
        region_manager = get_region_config_manager()
        success = region_manager.set_region_status(region_code, True)
        
        if success:
            return {
                "success": True,
                "message": f"区域 {region_code} 已设置为开放"
            }
        else:
            raise HTTPException(status_code=400, detail=f"设置区域 {region_code} 状态失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置区域状态失败: {str(e)}")


@router.put("/payment/regions/{region_code}/close", summary="设置区域为关闭")
def set_region_close(region_code: str):
    """
    设置区域为关闭状态
    
    Args:
        region_code: 区域代码（如：HK, TW, CN等）
    """
    try:
        region_manager = get_region_config_manager()
        success = region_manager.set_region_status(region_code, False)
        
        if success:
            return {
                "success": True,
                "message": f"区域 {region_code} 已设置为关闭"
            }
        else:
            raise HTTPException(status_code=400, detail=f"设置区域 {region_code} 状态失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置区域状态失败: {str(e)}")


@router.get("/payment/regions/check", summary="检查区域是否开放")
def check_region_status(region_code: str):
    """
    检查区域是否开放
    
    Args:
        region_code: 区域代码（如：HK, TW, CN等）
    """
    try:
        region_manager = get_region_config_manager()
        is_open = region_manager.is_region_open(region_code)
        
        return {
            "success": True,
            "region_code": region_code,
            "is_open": is_open
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查区域状态失败: {str(e)}")
