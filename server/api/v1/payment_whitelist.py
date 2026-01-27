#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付白名单管理 API
提供白名单的增删改查接口
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

from services.payment_service.payment_whitelist_manager import get_whitelist_manager

router = APIRouter()


class AddWhitelistRequest(BaseModel):
    """添加白名单请求"""
    whitelist_type: str = Field(..., description="白名单类型：user_id/email/phone/identifier")
    user_id: Optional[str] = Field(None, description="用户ID")
    email: Optional[str] = Field(None, description="用户邮箱")
    phone: Optional[str] = Field(None, description="用户手机号")
    identifier: Optional[str] = Field(None, description="其他标识符")
    blocked_region: Optional[str] = Field(None, description="被限制的区域（如：CN）")
    notes: Optional[str] = Field(None, description="备注说明")
    created_by: Optional[str] = Field(None, description="创建人")


class RemoveWhitelistRequest(BaseModel):
    """移除白名单请求"""
    whitelist_type: str = Field(..., description="白名单类型")
    user_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    identifier: Optional[str] = None


@router.post("/payment/whitelist/add", summary="添加白名单")
def add_to_whitelist(request: AddWhitelistRequest):
    """
    添加用户到白名单
    
    用于不开放区域的用户（如大陆用户）使用支付功能
    """
    try:
        whitelist_manager = get_whitelist_manager()
        success = whitelist_manager.add_to_whitelist(
            whitelist_type=request.whitelist_type,
            user_id=request.user_id,
            email=request.email,
            phone=request.phone,
            identifier=request.identifier,
            blocked_region=request.blocked_region,
            notes=request.notes,
            created_by=request.created_by
        )
        
        if success:
            return {
                "success": True,
                "message": "用户已添加到白名单"
            }
        else:
            raise HTTPException(status_code=400, detail="添加白名单失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加白名单失败: {str(e)}")


@router.delete("/payment/whitelist/remove", summary="移除白名单")
def remove_from_whitelist(request: RemoveWhitelistRequest):
    """
    从白名单移除用户
    """
    try:
        whitelist_manager = get_whitelist_manager()
        success = whitelist_manager.remove_from_whitelist(
            whitelist_type=request.whitelist_type,
            user_id=request.user_id,
            email=request.email,
            phone=request.phone,
            identifier=request.identifier
        )
        
        if success:
            return {
                "success": True,
                "message": "用户已从白名单移除"
            }
        else:
            raise HTTPException(status_code=400, detail="移除白名单失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移除白名单失败: {str(e)}")


@router.get("/payment/whitelist/list", summary="查询白名单列表")
def get_whitelist_list(
    status: Optional[str] = None,
    blocked_region: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    查询白名单列表
    
    Args:
        status: 状态过滤（active/inactive），如果为None则查询所有
        blocked_region: 区域过滤
        limit: 限制数量
        offset: 偏移量
    """
    try:
        whitelist_manager = get_whitelist_manager()
        whitelist = whitelist_manager.get_whitelist(
            status=status,
            blocked_region=blocked_region,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "whitelist": whitelist,
            "count": len(whitelist)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询白名单列表失败: {str(e)}")


@router.put("/payment/whitelist/{whitelist_id}/enable", summary="启用白名单")
def enable_whitelist(whitelist_id: int):
    """
    启用白名单
    """
    try:
        whitelist_manager = get_whitelist_manager()
        success = whitelist_manager.enable_whitelist(whitelist_id)
        
        if success:
            return {
                "success": True,
                "message": f"白名单 {whitelist_id} 已启用"
            }
        else:
            raise HTTPException(status_code=400, detail=f"启用白名单 {whitelist_id} 失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启用白名单失败: {str(e)}")


@router.put("/payment/whitelist/{whitelist_id}/disable", summary="禁用白名单")
def disable_whitelist(whitelist_id: int):
    """
    禁用白名单
    """
    try:
        whitelist_manager = get_whitelist_manager()
        success = whitelist_manager.disable_whitelist(whitelist_id)
        
        if success:
            return {
                "success": True,
                "message": f"白名单 {whitelist_id} 已禁用"
            }
        else:
            raise HTTPException(status_code=400, detail=f"禁用白名单 {whitelist_id} 失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"禁用白名单失败: {str(e)}")


@router.get("/payment/whitelist/check", summary="检查用户是否在白名单中")
def check_whitelist(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    identifier: Optional[str] = None
):
    """
    检查用户是否在白名单中
    
    Args:
        user_id: 用户ID
        email: 用户邮箱
        phone: 用户手机号
        identifier: 其他标识符
    """
    try:
        whitelist_manager = get_whitelist_manager()
        is_whitelisted = whitelist_manager.is_whitelisted(
            user_id=user_id,
            email=email,
            phone=phone,
            identifier=identifier
        )
        
        return {
            "success": True,
            "is_whitelisted": is_whitelisted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查白名单失败: {str(e)}")
