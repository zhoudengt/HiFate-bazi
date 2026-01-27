#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付客户端基类
提供统一的支付接口，便于快速继承和扩展
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BasePaymentClient(ABC):
    """支付客户端基类"""

    def __init__(self, environment: Optional[str] = None):
        """
        初始化支付客户端

        Args:
            environment: 环境（production/sandbox/test），如果为None则自动查找is_active=1的记录
        """
        self.environment = environment

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """支付平台名称"""
        pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """检查客户端是否已启用"""
        pass

    @abstractmethod
    def create_payment(self, **kwargs) -> Dict[str, Any]:
        """
        创建支付订单

        Args:
            amount: 金额（字符串）
            currency: 货币代码
            product_name: 产品名称
            order_id: 订单号（可选）
            customer_email: 客户邮箱（可选）
            metadata: 元数据（可选）
            其他平台特定参数...

        Returns:
            包含支付信息的字典
        """
        pass

    @abstractmethod
    def verify_payment(self, **kwargs) -> Dict[str, Any]:
        """
        验证支付状态

        Args:
            payment_id: 支付ID（Stripe/PayPal）
            order_id: 订单号（支付宝/微信）
            session_id: Stripe Session ID
            transaction_id: 交易ID（Line Pay/Payssion）

        Returns:
            支付状态信息
        """
        pass

    def refund(self, **kwargs) -> Dict[str, Any]:
        """
        退款（可选实现）

        Args:
            payment_id: 原支付ID
            amount: 退款金额
            reason: 退款原因

        Returns:
            退款结果
        """
        return {
            "success": False,
            "error": "退款功能未实现"
        }

    def get_supported_currencies(self) -> list:
        """获取支持的货币列表（可选实现）"""
        return ["USD"]

    def get_supported_regions(self) -> list:
        """获取支持的地区列表（可选实现）"""
        return ["global"]