#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stripe支付客户端封装"""

from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any

try:
    import stripe
except ImportError:
    stripe = None
    logging.warning("stripe库未安装，请运行: pip install stripe")

logger = logging.getLogger(__name__)


class StripeClient:
    """Stripe支付客户端"""
    
    def __init__(self):
        """初始化Stripe客户端"""
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        if not self.api_key:
            logger.warning("STRIPE_SECRET_KEY环境变量未设置")
        
        if stripe:
            stripe.api_key = self.api_key
    
    def create_checkout_session(
        self,
        amount: str,
        currency: str = "USD",
        product_name: str = "月订阅会员",
        customer_email: str = "",
        metadata: Optional[Dict[str, str]] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建Stripe支付会话
        
        Args:
            amount: 金额（字符串，如"19.90"）
            currency: 货币代码，默认USD
            product_name: 产品名称
            customer_email: 客户邮箱
            metadata: 元数据
            success_url: 支付成功后的跳转URL
            cancel_url: 支付取消后的跳转URL
        
        Returns:
            包含session_id和checkout_url的字典
        """
        if not stripe:
            raise RuntimeError("stripe库未安装")
        
        if not self.api_key:
            raise RuntimeError("STRIPE_SECRET_KEY未配置")
        
        # 转换金额为分（Stripe使用最小货币单位）
        amount_float = float(amount)
        if currency.upper() == "USD":
            amount_cents = int(amount_float * 100)
        else:
            # 其他货币也使用类似逻辑
            amount_cents = int(amount_float * 100)
        
        # 构建成功和取消URL
        base_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:8080")
        if not success_url:
            success_url = f"{base_url}/payment-success.html?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"{base_url}/payment-cancel.html"
        
        try:
            session_params = {
                "payment_method_types": ["card"],
                "line_items": [
                    {
                        "price_data": {
                            "currency": currency.lower(),
                            "product_data": {
                                "name": product_name,
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                "mode": "payment",
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
            
            if customer_email:
                session_params["customer_email"] = customer_email
            
            if metadata:
                session_params["metadata"] = metadata
            
            session = stripe.checkout.Session.create(**session_params)
            
            logger.info(f"创建支付会话成功: session_id={session.id}")
            
            return {
                "session_id": session.id,
                "checkout_url": session.url,
                "status": "created",
            }
        except stripe.error.StripeError as e:
            logger.error(f"创建支付会话失败: {e}")
            raise RuntimeError(f"Stripe支付会话创建失败: {str(e)}")
    
    def retrieve_session(self, session_id: str) -> Dict[str, Any]:
        """
        获取支付会话信息
        
        Args:
            session_id: Stripe Session ID
        
        Returns:
            会话信息字典
        """
        if not stripe:
            raise RuntimeError("stripe库未安装")
        
        if not self.api_key:
            raise RuntimeError("STRIPE_SECRET_KEY未配置")
        
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            result = {
                "status": session.payment_status,  # paid, unpaid, no_payment_required
                "payment_intent_id": session.payment_intent if hasattr(session, 'payment_intent') else None,
                "amount": str(session.amount_total / 100) if session.amount_total else None,
                "currency": session.currency.upper() if session.currency else None,
                "customer_email": session.customer_email if hasattr(session, 'customer_email') else None,
                "created_at": session.created,
                "metadata": dict(session.metadata) if session.metadata else {},
            }
            
            # 映射Stripe状态到我们的状态
            if session.payment_status == "paid":
                result["status"] = "success"
            elif session.payment_status == "unpaid":
                if session.status == "expired":
                    result["status"] = "failed"
                else:
                    result["status"] = "pending"
            elif session.status == "expired":
                result["status"] = "failed"
            else:
                result["status"] = "pending"
            
            return result
        except stripe.error.StripeError as e:
            logger.error(f"获取支付会话失败: {e}")
            raise RuntimeError(f"获取支付会话失败: {str(e)}")

