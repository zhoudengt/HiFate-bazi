#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schemas for payment-service."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, EmailStr


class CreatePaymentSessionRequest(BaseModel):
    """创建支付会话请求"""
    amount: str = Field(..., description="金额，格式：19.90")
    currency: str = Field(default="USD", description="货币代码，默认：USD")
    product_name: str = Field(..., description="产品名称，如：月订阅会员")
    customer_email: EmailStr = Field(..., description="客户邮箱")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="元数据（可选）")


class CreatePaymentSessionResponse(BaseModel):
    """创建支付会话响应"""
    session_id: str = Field(..., description="Stripe Session ID")
    checkout_url: str = Field(..., description="支付页面URL")
    status: str = Field(..., description="状态：created/success/failed")
    message: str = Field(default="", description="消息")


class VerifyPaymentRequest(BaseModel):
    """验证支付状态请求"""
    session_id: str = Field(..., description="Stripe Session ID")


class VerifyPaymentResponse(BaseModel):
    """验证支付状态响应"""
    status: str = Field(..., description="支付状态：pending/success/failed/canceled")
    payment_intent_id: Optional[str] = Field(default=None, description="Payment Intent ID")
    amount: Optional[str] = Field(default=None, description="支付金额")
    currency: Optional[str] = Field(default=None, description="货币")
    customer_email: Optional[str] = Field(default=None, description="客户邮箱")
    created_at: Optional[int] = Field(default=None, description="创建时间戳")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="元数据")

