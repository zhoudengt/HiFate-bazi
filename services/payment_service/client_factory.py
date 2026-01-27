#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付客户端工厂
管理所有支付客户端的注册和获取
"""

import logging
from typing import Dict, Type, Callable, Optional
from .base_client import BasePaymentClient

logger = logging.getLogger(__name__)


class PaymentClientFactory:
    """支付客户端工厂"""

    def __init__(self):
        self._clients: Dict[str, Callable[[], BasePaymentClient]] = {}

    def register_client(self, provider_name: str, client_factory: Callable[[], BasePaymentClient]):
        """
        注册支付客户端

        Args:
            provider_name: 支付平台名称
            client_factory: 客户端工厂函数
        """
        self._clients[provider_name] = client_factory
        logger.info(f"注册支付客户端: {provider_name}")

    def get_client(self, provider_name: str) -> BasePaymentClient:
        """
        获取支付客户端实例

        Args:
            provider_name: 支付平台名称

        Returns:
            支付客户端实例

        Raises:
            ValueError: 不支持的支付平台
        """
        if provider_name not in self._clients:
            raise ValueError(f"不支持的支付平台: {provider_name}")

        return self._clients[provider_name]()

    def get_available_providers(self) -> Dict[str, bool]:
        """
        获取所有可用的支付平台及其启用状态

        Returns:
            支付平台状态字典
        """
        result = {}
        for provider_name, factory in self._clients.items():
            try:
                client = factory()
                result[provider_name] = client.is_enabled
            except Exception as e:
                logger.warning(f"检查支付平台 {provider_name} 状态失败: {e}")
                result[provider_name] = False
        return result

    def list_clients(self) -> list:
        """获取所有已注册的支付平台列表"""
        return list(self._clients.keys())


# 全局工厂实例
payment_client_factory = PaymentClientFactory()

# 注册为热更新单例（确保模块重新加载时重新注册客户端）
try:
    from server.hot_reload.reloaders import SingletonReloader
    SingletonReloader.register_singleton(
        'services.payment_service.client_factory',
        'PaymentClientFactory',
        ['_clients']  # 重置客户端注册表
    )
    # 同时注册重新导入 services.payment_service 模块
    import importlib
    import sys
    def _reload_payment_service():
        """重新加载支付服务模块以触发客户端注册"""
        if 'services.payment_service' in sys.modules:
            importlib.reload(sys.modules['services.payment_service'])
    SingletonReloader.register_singleton(
        'services.payment_service',
        'payment_service',
        []  # 模块级别，通过重新导入触发
    )
except ImportError:
    pass  # 开发环境可能没有热更新模块


def register_payment_client(provider_name: str):
    """
    支付客户端注册装饰器

    使用方法：
    @register_payment_client("stripe")
    class StripeClient(BasePaymentClient):
        ...
    """
    def decorator(client_class: Type[BasePaymentClient]):
        payment_client_factory.register_client(provider_name, lambda: client_class())
        return client_class
    return decorator


def get_payment_client(provider_name: str) -> BasePaymentClient:
    """
    获取支付客户端实例的便捷函数

    Args:
        provider_name: 支付平台名称

    Returns:
        支付客户端实例
    """
    return payment_client_factory.get_client(provider_name)