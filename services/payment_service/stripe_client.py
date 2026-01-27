#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stripe支付客户端封装"""

from __future__ import annotations

import os
import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

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

# 导入支付配置加载器（统一使用 LinePayClient/NewebPayClient 方式）
try:
    from services.payment_service.payment_config_loader import get_payment_config, get_payment_environment
except ImportError:
    # 降级到环境变量
    def get_payment_config(provider: str, config_key: str, environment: str = 'production', default: Optional[str] = None) -> Optional[str]:
        return os.getenv(f"{provider.upper()}_{config_key.upper()}", default)
    def get_payment_environment(default: str = 'production') -> str:
        return os.getenv("PAYMENT_ENVIRONMENT", default)

# 导入货币转换工具
try:
    from services.payment_service.currency_converter import CurrencyConverter
    from services.payment_service.payment_api_logger import get_payment_api_logger
    from services.payment_service.fx_risk_monitor import get_fx_risk_monitor
    from server.db.payment_transaction_dao import PaymentTransactionDAO
except ImportError as e:
    logger.warning(f"导入支付工具模块失败: {e}")
    CurrencyConverter = None
    get_payment_api_logger = None
    get_fx_risk_monitor = None
    PaymentTransactionDAO = None

from .base_client import BasePaymentClient
from .client_factory import register_payment_client


@register_payment_client("stripe")
class StripeClient(BasePaymentClient):
    """Stripe支付客户端"""
    
    def __init__(self, environment: Optional[str] = None):
        """初始化Stripe客户端
        
        Args:
            environment: 支付环境（production/sandbox/test），如果为None则自动查找is_active=1的记录
        """
        super().__init__(environment)
        
        # 从数据库读取配置，自动查找is_active=1的记录
        # 如果指定了environment，则优先匹配该环境且is_active=1的记录
        self.api_key = get_payment_config('stripe', 'secret_key', environment) or os.getenv("STRIPE_SECRET_KEY")
        
        if not self.api_key:
            logger.warning("STRIPE_SECRET_KEY未配置（数据库或环境变量）")
        
        # 初始化时尝试设置 API key
        stripe_module = _import_stripe()
        if stripe_module and self.api_key:
            stripe_module.api_key = self.api_key
    
    @property
    def provider_name(self) -> str:
        """支付平台名称"""
        return "stripe"
    
    @property
    def is_enabled(self) -> bool:
        """检查Stripe客户端是否已启用"""
        stripe_module = _import_stripe()
        return bool(self.api_key and stripe_module)
    
    @staticmethod
    def _get_payment_api_logger():
        """获取支付接口调用日志记录器"""
        if get_payment_api_logger:
            return get_payment_api_logger()
        return None
    
    def create_payment(self, **kwargs) -> Dict[str, Any]:
        """
        创建支付订单（统一接口，实现抽象方法）
        
        Args:
            amount: 金额（字符串）
            currency: 货币代码
            product_name: 产品名称
            order_id: 订单号（可选）
            customer_email: 客户邮箱（可选）
            metadata: 元数据（可选）
            success_url: 支付成功后的跳转URL（可选）
            cancel_url: 支付取消后的跳转URL（可选）
            enable_adaptive_pricing: 是否启用 Adaptive Pricing（可选）
            enable_link: 是否启用 Stripe Link（可选）
        
        Returns:
            包含支付信息的字典
        """
        return self.create_checkout_session(
            amount=kwargs.get('amount', '0'),
            currency=kwargs.get('currency', 'USD'),
            product_name=kwargs.get('product_name', ''),
            customer_email=kwargs.get('customer_email', ''),
            metadata=kwargs.get('metadata'),
            success_url=kwargs.get('success_url'),
            cancel_url=kwargs.get('cancel_url'),
            enable_adaptive_pricing=kwargs.get('enable_adaptive_pricing', True),
            enable_link=kwargs.get('enable_link', True),
            order_id=kwargs.get('order_id')
        )
    
    def create_checkout_session(
        self,
        amount: str,
        currency: str = "USD",
        product_name: str = "月订阅会员",
        customer_email: str = "",
        metadata: Optional[Dict[str, str]] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        enable_adaptive_pricing: bool = True,
        enable_link: bool = True,
        order_id: Optional[str] = None,
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
            enable_adaptive_pricing: 是否启用 Adaptive Pricing（自动货币转换）
            enable_link: 是否启用 Stripe Link
            order_id: 订单号（用于关联交易记录）
        
        Returns:
            包含session_id和checkout_url的字典
        """
        # 使用接口调用日志记录器
        api_logger = self._get_payment_api_logger()
        if api_logger:
            decorator = api_logger.log_api_call(
                "stripe.create_checkout_session",
                log_request=True,
                log_response=True,
                log_billing=True
            )
            return decorator(self._create_checkout_session_impl)(
                amount, currency, product_name, customer_email, metadata,
                success_url, cancel_url, enable_adaptive_pricing, enable_link, order_id
            )
        else:
            return self._create_checkout_session_impl(
                amount, currency, product_name, customer_email, metadata,
                success_url, cancel_url, enable_adaptive_pricing, enable_link, order_id
            )
    
    def _create_checkout_session_impl(
        self,
        amount: str,
        currency: str = "USD",
        product_name: str = "月订阅会员",
        customer_email: str = "",
        metadata: Optional[Dict[str, str]] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        enable_adaptive_pricing: bool = True,
        enable_link: bool = True,
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建Stripe支付会话的实现方法
        """
        # 动态检查 stripe 是否可用
        stripe_module = _import_stripe()
        if stripe_module is None:
            raise RuntimeError("stripe库未安装")
        
        # 如果初始化时没有配置，尝试重新加载（支持热更新）
        if not self.api_key:
            self.api_key = get_payment_config('stripe', 'secret_key', self.environment) or os.getenv("STRIPE_SECRET_KEY")
        
        if not self.api_key:
            raise RuntimeError("STRIPE_SECRET_KEY未配置")
        
        # 货币转换逻辑
        original_currency = currency.upper()
        needs_conversion = False
        converted_amount = amount
        converted_currency = currency
        conversion_fee_info = None
        exchange_rate = None
        
        if CurrencyConverter:
            needs_conversion = CurrencyConverter.needs_conversion(original_currency)
            
            if needs_conversion:
                # 需要转换：转换为HKD
                converted_currency = CurrencyConverter.get_target_currency()
                # 计算转换费用（商家承担）
                conversion_fee_info = CurrencyConverter.calculate_conversion_fee(
                    amount, "stripe", original_currency
                )
                # 注意：Stripe Adaptive Pricing 会自动处理汇率转换
                # 这里只记录费用信息，实际汇率由 Stripe 提供
                logger.info(f"货币需要转换: {original_currency} -> {converted_currency}, 费用: {conversion_fee_info}")
        
        # 转换金额为分（Stripe使用最小货币单位）
        amount_float = float(converted_amount)
        currency_to_use = converted_currency.lower()
        
        # 处理零小数货币（如JPY, TWD等）
        if currency_to_use.upper() in ["JPY", "TWD", "KRW", "VND"]:
            amount_cents = int(amount_float)
        else:
            amount_cents = int(amount_float * 100)
        
        # 构建成功和取消URL
        base_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:8080")
        if not success_url:
            success_url = f"{base_url}/payment-success.html?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"{base_url}/payment-cancel.html"
        
        try:
            # 构建支付方式列表
            payment_method_types = ["card"]
            if enable_link:
                payment_method_types.append("link")
            
            session_params = {
                "payment_method_types": payment_method_types,
                "line_items": [
                    {
                        "price_data": {
                            "currency": currency_to_use,
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
            
            # 启用 Stripe Link（通过 payment_method_types 添加 link，不需要 payment_method_options）
            # 注意：Stripe Link 已通过 payment_method_types 中的 "link" 启用
            # 如果 enable_link 为 True，link 已经在 payment_method_types 中
            
            # 启用 Adaptive Pricing（通过配置，Stripe会自动处理货币转换）
            # 注意：Adaptive Pricing 需要在 Stripe Dashboard 中启用
            # 这里只是确保配置正确，实际转换由 Stripe 处理
            
            if customer_email:
                session_params["customer_email"] = customer_email
            
            if metadata:
                session_params["metadata"] = metadata
            
            # 设置过期时间（30分钟后）
            from datetime import timedelta
            expires_at_timestamp = int((datetime.now() + timedelta(minutes=30)).timestamp())
            session_params["expires_at"] = expires_at_timestamp
            
            # 计算过期时间字符串（用于保存到数据库）
            expires_at_str = (datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 设置 API key（每次调用前确保设置）
            stripe_module.api_key = self.api_key
            session = stripe_module.checkout.Session.create(**session_params)
            
            # 记录交易信息到数据库
            if PaymentTransactionDAO and order_id:
                transaction_id = PaymentTransactionDAO.create_transaction(
                    order_id=order_id,
                    provider="stripe",
                    original_amount=amount,
                    original_currency=original_currency,
                    converted_amount=converted_amount if needs_conversion else None,
                    converted_currency=converted_currency if needs_conversion else original_currency,
                    needs_conversion=needs_conversion,
                    conversion_fee=conversion_fee_info.get("conversion_fee") if conversion_fee_info else None,
                    conversion_fee_rate=conversion_fee_info.get("conversion_fee_rate") if conversion_fee_info else None,
                    fixed_fee=conversion_fee_info.get("fixed_fee") if conversion_fee_info else None,
                    exchange_rate=exchange_rate,
                    customer_email=customer_email,
                    product_name=product_name,
                    metadata=metadata,
                    expires_at=expires_at_str
                )
                
                # 记录汇率（如果有）
                if exchange_rate and get_fx_risk_monitor:
                    fx_monitor = get_fx_risk_monitor()
                    fx_monitor.record_exchange_rate(
                        from_currency=original_currency,
                        to_currency=converted_currency if needs_conversion else original_currency,
                        exchange_rate=exchange_rate,
                        provider="stripe",
                        transaction_id=transaction_id
                    )
            
            logger.info(f"创建支付会话成功: session_id={session.id}, currency={currency_to_use}, needs_conversion={needs_conversion}")
            
            return {
                "success": True,
                "session_id": session.id,
                "checkout_url": session.url,
                "status": "created",
                "expires_at": expires_at_str,
                "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "needs_conversion": needs_conversion,
                "original_currency": original_currency,
                "converted_currency": converted_currency if needs_conversion else original_currency,
            }
        except stripe_module.error.StripeError as e:
            logger.error(f"创建支付会话失败: {e}")
            raise RuntimeError(f"Stripe支付会话创建失败: {str(e)}")
    
    def retrieve_session(self, session_id: str, order_id: Optional[str] = None) -> Dict[str, Any]:
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
            self.api_key = get_payment_config('stripe', 'secret_key', self.environment) or os.getenv("STRIPE_SECRET_KEY")
        
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
                
                    # 支付成功时，更新交易记录的实际汇率
                if PaymentTransactionDAO and order_id:
                    # 从 session 中提取实际汇率（如果 Stripe 提供了）
                    # 注意：Stripe Adaptive Pricing 的汇率信息可能在 payment_intent 中
                    actual_exchange_rate = None
                    if hasattr(session, 'payment_intent') and session.payment_intent:
                        try:
                            payment_intent = stripe_module.PaymentIntent.retrieve(session.payment_intent)
                            # 提取汇率信息（如果可用）
                            # Stripe 的汇率信息可能在 payment_intent 的 metadata 或其他字段中
                            # 这里需要根据 Stripe API 文档获取
                        except:
                            pass
                    
                    # 更新交易记录
                    transaction = PaymentTransactionDAO.get_transaction_by_order_id(order_id)
                    if transaction:
                        PaymentTransactionDAO.update_transaction(
                            transaction_id=transaction['id'],
                            provider_payment_id=session.id,
                            status="success",
                            actual_exchange_rate=actual_exchange_rate,
                            paid_at=datetime.now().isoformat()
                        )
                        
                        # 记录实际汇率到历史表
                        if actual_exchange_rate and get_fx_risk_monitor:
                            fx_monitor = get_fx_risk_monitor()
                            fx_monitor.record_exchange_rate(
                                from_currency=transaction.get('original_currency', 'USD'),
                                to_currency=transaction.get('converted_currency', 'HKD'),
                                exchange_rate=actual_exchange_rate,
                                provider="stripe",
                                transaction_id=transaction['id'],
                                source="transaction"
                            )
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

