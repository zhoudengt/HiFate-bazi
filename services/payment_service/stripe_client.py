#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stripe支付客户端封装"""

from __future__ import annotations

import os
import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 动态导入 stripe，支持运行时安装
def _import_stripe():
    """动态导入 stripe 库"""
    try:
        import stripe
        return stripe
    except ImportError:
        return None

# 首次导入尝试
stripe = _import_stripe()
if stripe is None:
    logging.warning("stripe库未安装，请运行: pip install stripe")

logger = logging.getLogger(__name__)

# 延迟导入 payment_config_loader，避免循环依赖
def _get_payment_config(provider: str, config_key: str, environment: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    """从数据库或环境变量获取支付配置"""
    try:
        from services.payment_service.payment_config_loader import get_payment_config
        return get_payment_config(provider, config_key, environment, None, default)
    except Exception as e:
        logger.warning(f"⚠️ 从数据库加载配置失败，使用环境变量降级: {e}")
        return None


class StripeClient:
    """Stripe支付客户端"""
    
    def __init__(self, environment: Optional[str] = None):
        """初始化Stripe客户端
        
        Args:
            environment: 支付环境（production/sandbox/test），如果为None则自动查找is_active=1的记录
        """
        self.environment = environment
        
        # 优先从数据库读取配置，降级到环境变量
        self.api_key = _get_payment_config('stripe', 'secret_key', environment) or os.getenv("STRIPE_SECRET_KEY")
        
        if not self.api_key:
            logger.warning("STRIPE_SECRET_KEY未配置（数据库和环境变量都未设置）")
        else:
            logger.info(f"✓ Stripe API Key 已加载（来源: {'数据库' if _get_payment_config('stripe', 'secret_key', environment) else '环境变量'}）")
        
        # 初始化时尝试设置 API key
        stripe_module = _import_stripe()
        if stripe_module and self.api_key:
            stripe_module.api_key = self.api_key
    
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
        # 动态检查 stripe 是否可用
        stripe_module = _import_stripe()
        if stripe_module is None:
            raise RuntimeError("stripe库未安装")
        
        # 如果初始化时没有配置，尝试重新加载（支持热更新）
        if not self.api_key:
            self.api_key = _get_payment_config('stripe', 'secret_key', self.environment) or os.getenv("STRIPE_SECRET_KEY")
        
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
            
            # 设置 API key（每次调用前确保设置）
            stripe_module.api_key = self.api_key
            session = stripe_module.checkout.Session.create(**session_params)
            
            logger.info(f"创建支付会话成功: session_id={session.id}")
            
            return {
                "session_id": session.id,
                "checkout_url": session.url,
                "status": "created",
            }
        except stripe_module.error.StripeError as e:
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
        # 动态检查 stripe 是否可用
        stripe_module = _import_stripe()
        if stripe_module is None:
            raise RuntimeError("stripe库未安装")
        
        # 如果初始化时没有配置，尝试重新加载（支持热更新）
        if not self.api_key:
            self.api_key = _get_payment_config('stripe', 'secret_key', self.environment) or os.getenv("STRIPE_SECRET_KEY")
        
        if not self.api_key:
            raise RuntimeError("STRIPE_SECRET_KEY未配置")
        
        try:
            # 设置 API key（每次调用前确保设置）
            stripe_module.api_key = self.api_key
            session = stripe_module.checkout.Session.retrieve(session_id)
            
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
        except stripe_module.error.StripeError as e:
            logger.error(f"获取支付会话失败: {e}")
            raise RuntimeError(f"获取支付会话失败: {str(e)}")
    
    def verify_payment(self, session_id: str) -> Dict[str, Any]:
        """
        验证支付状态（统一支付API接口）
        
        Args:
            session_id: Stripe Session ID
        
        Returns:
            包含success、status、amount等字段的字典
        """
        try:
            result = self.retrieve_session(session_id)
            
            # 转换为统一格式
            return {
                "success": True,
                "status": result.get("status"),  # success, pending, failed
                "amount": result.get("amount"),
                "currency": result.get("currency"),
                "customer_email": result.get("customer_email"),
                "created_at": result.get("created_at"),
                "message": f"支付状态: {result.get('status')}"
            }
        except RuntimeError as e:
            logger.error(f"验证支付失败: {e}")
            return {
                "success": False,
                "status": "error",
                "message": str(e)
            }

