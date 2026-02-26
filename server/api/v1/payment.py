#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付API接口（魔方西元）

# [DEPRECATED] 已被 unified_payment.py (v2) 替代。
# 路由注册和 gRPC 端点注册已移除，此文件不再有运行时引用。
# 下个版本可直接删除。
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict

# main.py 已经设置了 project_root，这里不需要重复设置
# 但为了兼容性，确保项目根目录在路径中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services.payment_service.stripe_client import StripeClient

router = APIRouter()

# 初始化Stripe客户端
stripe_client = StripeClient()


class CreatePaymentSessionRequest(BaseModel):
    """创建支付会话请求"""
    amount: str = Field(..., description="金额，格式：19.90", example="19.90")
    currency: str = Field(default="USD", description="货币代码，默认：USD")
    product_name: str = Field(..., description="产品名称，如：月订阅会员", example="月订阅会员")
    customer_email: EmailStr = Field(..., description="客户邮箱", example="user@example.com")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="元数据（可选）")


class CreatePaymentSessionResponse(BaseModel):
    """创建支付会话响应"""
    success: bool
    session_id: Optional[str] = None
    checkout_url: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None


class VerifyPaymentRequest(BaseModel):
    """验证支付状态请求"""
    session_id: str = Field(..., description="Stripe Session ID")


class VerifyPaymentResponse(BaseModel):
    """验证支付状态响应"""
    success: bool
    status: Optional[str] = None
    payment_intent_id: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    customer_email: Optional[str] = None
    created_at: Optional[int] = None
    metadata: Optional[Dict[str, str]] = None
    message: Optional[str] = None


@router.post("/payment/create-session", response_model=CreatePaymentSessionResponse, summary="创建支付会话")
def create_payment_session(request: CreatePaymentSessionRequest):
    """
    创建Stripe支付会话
    
    - **amount**: 金额（字符串，如"19.90"）
    - **currency**: 货币代码，默认USD
    - **product_name**: 产品名称
    - **customer_email**: 客户邮箱
    - **metadata**: 元数据（可选）
    
    返回支付会话ID和支付页面URL
    """
    try:
        result = stripe_client.create_checkout_session(
            amount=request.amount,
            currency=request.currency,
            product_name=request.product_name,
            customer_email=request.customer_email,
            metadata=request.metadata,
        )
        
        return CreatePaymentSessionResponse(
            success=True,
            session_id=result["session_id"],
            checkout_url=result["checkout_url"],
            status=result["status"],
            message="支付会话创建成功",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建支付会话失败: {str(e)}"
        )


@router.post("/payment/verify", response_model=VerifyPaymentResponse, summary="验证支付状态")
def verify_payment(request: VerifyPaymentRequest):
    """
    验证支付状态
    
    - **session_id**: Stripe Session ID
    
    返回支付状态信息
    """
    try:
        result = stripe_client.retrieve_session(request.session_id)
        
        return VerifyPaymentResponse(
            success=True,
            status=result["status"],
            payment_intent_id=result.get("payment_intent_id"),
            amount=result.get("amount"),
            currency=result.get("currency"),
            customer_email=result.get("customer_email"),
            created_at=result.get("created_at"),
            metadata=result.get("metadata"),
            message="支付状态查询成功",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"验证支付状态失败: {str(e)}"
        )

