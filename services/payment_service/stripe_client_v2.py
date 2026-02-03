#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stripe支付客户端 - 基于插件化架构重构
继承自BasePaymentClient，提供统一的接口
"""

import os
import logging
from typing import Optional, Dict, Any, Union

# 导入支付配置加载器
try:
    from services.payment_service.payment_config_loader import get_payment_config, get_payment_environment
except ImportError:
    # 降级到环境变量
    def get_payment_config(provider: str, config_key: str, environment: str = 'production', default: Optional[str] = None) -> Optional[str]:
        return os.getenv(f"{provider.upper()}_{config_key.upper()}", default)
    def get_payment_environment(default: str = 'production') -> str:
        return os.getenv("PAYMENT_ENVIRONMENT", default)

# 导入支付工具
try:
    from services.payment_service.currency_converter import CurrencyConverter
    from services.payment_service.payment_api_logger import get_payment_api_logger
    from services.payment_service.fx_risk_monitor import get_fx_risk_monitor
    from server.db.payment_transaction_dao import PaymentTransactionDAO
except ImportError as e:
    logging.warning(f"导入支付工具模块失败: {e}")
    CurrencyConverter = None
    get_payment_api_logger = None
    get_fx_risk_monitor = None
    PaymentTransactionDAO = None

from .base_client import BasePaymentClient
from .client_factory import register_payment_client

logger = logging.getLogger(__name__)


def _import_stripe():
    """动态导入stripe模块"""
    try:
        import stripe
        return stripe
    except ImportError:
        return None


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
        return bool(self.api_key and _import_stripe())

    def get_supported_currencies(self) -> list:
        """获取Stripe支持的货币列表"""
        return ["USD", "EUR", "HKD", "PHP", "GBP", "AUD", "CAD", "SGD", "JPY", "CNY"]

    def get_supported_regions(self) -> list:
        """获取Stripe支持的地区列表"""
        return ["美洲", "欧洲", "香港", "菲律宾", "新加坡", "日本", "中国", "全球"]

    @staticmethod
    def _get_payment_api_logger():
        """获取支付接口调用日志记录器"""
        if get_payment_api_logger:
            return get_payment_api_logger()
        return None

    def create_payment(self, **kwargs) -> Dict[str, Any]:
        """
        创建Stripe支付订单

        Args:
            amount: 金额（字符串，如"19.90"）
            currency: 货币代码，默认USD
            product_name: 产品名称
            customer_email: 客户邮箱（必需）
            metadata: 元数据
            order_id: 订单号
            enable_adaptive_pricing: 是否启用 Adaptive Pricing
            enable_link: 是否启用 Stripe Link

        Returns:
            包含session_id和checkout_url的字典
        """
        amount = kwargs.get('amount', '19.90')
        currency = kwargs.get('currency', 'USD')
        product_name = kwargs.get('product_name', '月订阅会员')
        customer_email = kwargs.get('customer_email', '')
        metadata = kwargs.get('metadata', {})
        order_id = kwargs.get('order_id')
        enable_adaptive_pricing = kwargs.get('enable_adaptive_pricing', True)
        enable_link = kwargs.get('enable_link', True)
        success_url = kwargs.get('success_url')
        cancel_url = kwargs.get('cancel_url')

        return self.create_checkout_session(
            amount=amount,
            currency=currency,
            product_name=product_name,
            customer_email=customer_email,
            metadata=metadata,
            enable_adaptive_pricing=enable_adaptive_pricing,
            enable_link=enable_link,
            order_id=order_id,
            success_url=success_url,
            cancel_url=cancel_url
        )

    def verify_payment(self, **kwargs) -> Dict[str, Any]:
        """
        验证Stripe支付状态

        Args:
            session_id: Stripe Session ID（必需）
            payment_id: 支付ID（兼容旧接口）

        Returns:
            支付状态信息
        """
        session_id = kwargs.get('session_id') or kwargs.get('payment_id')
        if not session_id:
            return {
                "success": False,
                "error": "Stripe验证需要提供session_id或payment_id"
            }

        return self.verify_payment_status(session_id)

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
        """创建Stripe支付会话的实现"""
        stripe_module = _import_stripe()
        if not stripe_module:
            return {
                "success": False,
                "error": "Stripe模块未安装"
            }

        if not self.api_key:
            return {
                "success": False,
                "error": "Stripe API key未配置"
            }

        try:
            # 设置API key
            stripe_module.api_key = self.api_key

            # 从数据库读取URL，如果数据库中没有则降级到环境变量
            frontend_base = get_payment_config('shared', 'frontend_base_url') or os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")

            if not success_url:
                success_url = f"{frontend_base}/frontend/payment-success.html?provider=stripe"

            if not cancel_url:
                cancel_url = f"{frontend_base}/frontend/payment-cancel.html?provider=stripe"

            # 转换金额为最小货币单位（Stripe要求整数）
            # USD, EUR 等使用 cents（分），CNY使用分，JPY使用日元（整数）
            amount_cents = self._convert_to_stripe_amount(amount, currency)

            # 构建metadata
            session_metadata = metadata.copy() if metadata else {}
            if order_id:
                session_metadata["order_id"] = order_id

            # 构建支付方式
            payment_method_types = ["card"]
            if enable_link:
                payment_method_types.append("link")

            # 创建checkout session
            session_data = {
                "payment_method_types": payment_method_types,
                "line_items": [{
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {
                            "name": product_name,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                "mode": "payment",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "customer_email": customer_email if customer_email else None,
                "metadata": session_metadata,
            }

            # 添加自动定价（如果启用且支持）
            if enable_adaptive_pricing and currency.upper() != "USD":
                session_data["automatic_tax"] = {"enabled": True}

            session = stripe_module.checkout.Session.create(**session_data)

            # 记录到数据库（如果有交易记录DAO）
            if PaymentTransactionDAO and order_id:
                try:
                    PaymentTransactionDAO().create_transaction(
                        order_id=order_id,
                        provider="stripe",
                        payment_id=session.id,
                        amount=amount,
                        currency=currency,
                        status="pending",
                        customer_email=customer_email,
                        metadata=session_metadata
                    )
                except Exception as e:
                    logger.warning(f"记录Stripe交易到数据库失败: {e}")

            return {
                "success": True,
                "session_id": session.id,
                "checkout_url": session.url,
                "status": "created",
                "order_id": order_id,
                "message": "Stripe支付会话创建成功"
            }

        except Exception as e:
            logger.error(f"创建Stripe支付会话失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def verify_payment_status(self, session_id: str) -> Dict[str, Any]:
        """
        验证Stripe支付状态

        Args:
            session_id: Stripe Session ID

        Returns:
            支付状态信息
        """
        stripe_module = _import_stripe()
        if not stripe_module:
            return {
                "success": False,
                "error": "Stripe模块未安装"
            }

        if not self.api_key:
            return {
                "success": False,
                "error": "Stripe API key未配置"
            }

        try:
            # 设置API key
            stripe_module.api_key = self.api_key

            # 获取session信息
            session = stripe_module.checkout.Session.retrieve(session_id)

            # 获取支付意图信息
            payment_intent = None
            if session.payment_intent:
                payment_intent = stripe_module.PaymentIntent.retrieve(session.payment_intent)

            # 判断支付状态
            status = "pending"
            paid = False
            if payment_intent:
                if payment_intent.status == "succeeded":
                    status = "success"
                    paid = True
                elif payment_intent.status in ["canceled", "requires_payment_method"]:
                    status = "failed"
                else:
                    status = payment_intent.status

            # 获取金额信息
            amount = None
            currency = None
            if session.amount_total:
                amount = str(session.amount_total / 100)  # Stripe金额以分存储
                currency = session.currency.upper()

            # 获取客户邮箱
            customer_email = session.customer_details.email if session.customer_details else None

            # 获取创建时间
            created_at = session.created if hasattr(session, 'created') else None

            return {
                "success": True,
                "status": status,
                "paid": paid,
                "amount": amount,
                "currency": currency,
                "customer_email": customer_email,
                "created_at": created_at,
                "session_id": session_id,
                "message": f"支付状态: {status}"
            }

        except Exception as e:
            logger.error(f"验证Stripe支付状态失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _convert_to_stripe_amount(self, amount: str, currency: str) -> int:
        """
        将金额转换为Stripe要求的格式（最小货币单位）

        Args:
            amount: 金额字符串（如"19.90"）
            currency: 货币代码

        Returns:
            最小货币单位的整数值
        """
        currency = currency.upper()

        # 零小数货币（直接使用整数）
        zero_decimal_currencies = ["JPY", "KRW", "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"]

        try:
            if currency in zero_decimal_currencies:
                return int(float(amount))
            else:
                # 大多数货币使用分（cents）作为最小单位
                return int(float(amount) * 100)
        except (ValueError, TypeError):
            logger.warning(f"金额格式无效: {amount}，使用默认值100")
            return 100

    def refund(self, **kwargs) -> Dict[str, Any]:
        """
        Stripe退款

        Args:
            payment_id: 支付ID（Stripe Payment Intent ID）
            amount: 退款金额（可选，不提供则全额退款）
            reason: 退款原因

        Returns:
            退款结果
        """
        payment_id = kwargs.get('payment_id')
        amount = kwargs.get('amount')
        reason = kwargs.get('reason', 'customer_request')

        if not payment_id:
            return {
                "success": False,
                "error": "退款需要提供payment_id"
            }

        stripe_module = _import_stripe()
        if not stripe_module:
            return {
                "success": False,
                "error": "Stripe模块未安装"
            }

        try:
            # 设置API key
            stripe_module.api_key = self.api_key

            refund_data = {
                "payment_intent": payment_id,
                "reason": reason
            }

            if amount:
                # 转换金额为最小货币单位
                refund_data["amount"] = int(float(amount) * 100)

            refund = stripe_module.Refund.create(**refund_data)

            return {
                "success": True,
                "refund_id": refund.id,
                "amount": amount or "full",
                "status": refund.status,
                "message": "退款请求已提交"
            }

        except Exception as e:
            logger.error(f"Stripe退款失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }