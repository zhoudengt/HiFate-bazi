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
    
    # 只启用这些支付渠道
    ENABLED_PROVIDERS = {"stripe", "payermax"}

    def __init__(self):
        self._clients: Dict[str, Callable[[], BasePaymentClient]] = {}
        self._instances: Dict[str, BasePaymentClient] = {}  # 缓存客户端实例
        self._provider_status: Dict[str, bool] = {}  # 缓存启用状态
        self._status_cache_time: float = 0  # 状态缓存时间
        self._status_cache_ttl: float = 300  # 状态缓存有效期（秒）

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
        获取支付客户端实例（使用缓存）

        Args:
            provider_name: 支付平台名称

        Returns:
            支付客户端实例

        Raises:
            ValueError: 不支持的支付平台
        """
        if provider_name not in self._clients:
            raise ValueError(f"不支持的支付平台: {provider_name}")
        
        # 检查是否在启用列表中
        if provider_name not in self.ENABLED_PROVIDERS:
            raise ValueError(f"支付平台已禁用: {provider_name}")
        
        # 使用缓存的实例
        if provider_name not in self._instances:
            self._instances[provider_name] = self._clients[provider_name]()
        
        return self._instances[provider_name]

    def get_available_providers(self) -> Dict[str, bool]:
        """
        获取所有可用的支付平台及其启用状态（使用缓存）

        Returns:
            支付平台状态字典
        """
        import time
        current_time = time.time()
        
        # 检查缓存是否有效
        if self._provider_status and (current_time - self._status_cache_time) < self._status_cache_ttl:
            return self._provider_status.copy()
        
        # 重新检查状态（只检查启用的渠道）
        result = {}
        for provider_name in self.ENABLED_PROVIDERS:
            if provider_name not in self._clients:
                continue
            try:
                client = self.get_client(provider_name)
                result[provider_name] = client.is_enabled
            except Exception as e:
                logger.warning(f"检查支付平台 {provider_name} 状态失败: {e}")
                result[provider_name] = False
        
        # 更新缓存
        self._provider_status = result
        self._status_cache_time = current_time
        
        return result.copy()

    def list_clients(self) -> list:
        """获取所有已启用的支付平台列表"""
        return [p for p in self._clients.keys() if p in self.ENABLED_PROVIDERS]
    
    def clear_cache(self):
        """清除缓存（用于热更新）"""
        self._instances.clear()
        self._provider_status.clear()
        self._status_cache_time = 0
        logger.info("支付客户端缓存已清除")


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