#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI entrypoint for the payment microservice."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

from services.payment_service.schemas import (
    CreatePaymentSessionRequest,
    CreatePaymentSessionResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from services.payment_service.stripe_client import StripeClient

app = FastAPI(
    title="Payment Service",
    version="1.0.0",
    description="支付服务（魔方西元）- 集成Stripe支付",
)

# 初始化Stripe客户端
stripe_client = StripeClient()


@app.post("/payment/create-session", response_model=CreatePaymentSessionResponse)
def create_payment_session(payload: CreatePaymentSessionRequest) -> Dict[str, Any]:
    """创建支付会话"""
    try:
        result = stripe_client.create_checkout_session(
            amount=payload.amount,
            currency=payload.currency,
            product_name=payload.product_name,
            customer_email=payload.customer_email,
            metadata=payload.metadata,
        )
        
        return CreatePaymentSessionResponse(
            session_id=result["session_id"],
            checkout_url=result["checkout_url"],
            status=result["status"],
            message="支付会话创建成功",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"创建支付会话失败: {str(exc)}"
        ) from exc


@app.post("/payment/verify", response_model=VerifyPaymentResponse)
def verify_payment(payload: VerifyPaymentRequest) -> Dict[str, Any]:
    """验证支付状态"""
    try:
        result = stripe_client.retrieve_session(payload.session_id)
        
        return VerifyPaymentResponse(
            status=result["status"],
            payment_intent_id=result.get("payment_intent_id"),
            amount=result.get("amount"),
            currency=result.get("currency"),
            customer_email=result.get("customer_email"),
            created_at=result.get("created_at"),
            metadata=result.get("metadata"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"验证支付状态失败: {str(exc)}"
        ) from exc


@app.get("/healthz", tags=["health"])
def health_check() -> Dict[str, str]:
    """健康检查"""
    return {"status": "ok"}

