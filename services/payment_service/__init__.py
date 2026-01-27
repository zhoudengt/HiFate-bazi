#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付服务模块初始化
自动注册所有支付客户端
"""

import logging

logger = logging.getLogger(__name__)

# 导入客户端工厂
from .client_factory import payment_client_factory

# 导入所有支付客户端（触发注册装饰器）
try:
    from .stripe_client_v2 import StripeClient  # 新版插件化 Stripe 客户端
    logger.info("✅ Stripe 客户端已注册")
except ImportError as e:
    logger.warning(f"⚠️ Stripe 客户端导入失败: {e}")

try:
    # 导入并注册旧版 PayPal 客户端（需要适配）
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    # 临时创建 PayPal 客户端的注册版本
    from services.payment_service.paypal_client import PayPalClient as OldPayPalClient

    # 创建适配器
    from .client_factory import register_payment_client

    @register_payment_client("paypal")
    class PayPalClientAdapter(OldPayPalClient):
        @property
        def provider_name(self) -> str:
            return "paypal"

        def create_payment(self, **kwargs):
            return self.create_payment(
                amount=kwargs.get('amount', '19.90'),
                currency=kwargs.get('currency', 'USD'),
                product_name=kwargs.get('product_name', '商品'),
                description=kwargs.get('product_name', '商品'),
                order_id=kwargs.get('order_id')
            )

        def verify_payment(self, **kwargs):
            payment_id = kwargs.get('payment_id')
            if payment_id:
                return self.verify_payment(payment_id)
            return {"success": False, "error": "需要 payment_id"}

    logger.info("✅ PayPal 客户端已注册")
except ImportError as e:
    logger.warning(f"⚠️ PayPal 客户端导入失败: {e}")

try:
    from .payssion_client import PayssionClient
    logger.info("✅ Payssion 客户端已注册")
except ImportError as e:
    logger.warning(f"⚠️ Payssion 客户端导入失败: {e}")

try:
    from .payermax_client import PayerMaxClient
    logger.info("✅ PayerMax 客户端已注册")
except ImportError as e:
    logger.warning(f"⚠️ PayerMax 客户端导入失败: {e}")

try:
    from .alipay_client import AlipayClient
    logger.info("✅ Alipay 客户端已注册")
except ImportError as e:
    logger.warning(f"⚠️ Alipay 客户端导入失败: {e}")

try:
    from .wechat_client import WeChatPayClient
    logger.info("✅ WeChat 客户端已注册")
except ImportError as e:
    logger.warning(f"⚠️ WeChat 客户端导入失败: {e}")

try:
    from .linepay_client import LinePayClient
    logger.info("✅ LinePay 客户端已注册")
except ImportError as e:
    logger.warning(f"⚠️ LinePay 客户端导入失败: {e}")

# 输出注册统计
registered_providers = list(payment_client_factory.get_available_providers().keys())
logger.info(f"📊 支付平台注册完成，共 {len(registered_providers)} 个平台: {registered_providers}")

__all__ = [
    'payment_client_factory',
    'get_payment_client',
]