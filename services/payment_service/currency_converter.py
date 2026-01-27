#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
货币转换工具类
实现货币判断、费用计算、汇率记录等功能
"""

import logging
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

# 支持的货币列表（1v1入账，不需要转换）
SUPPORTED_CURRENCIES = [
    "HKD",  # 港币
    "CNY",  # 人民币
    "USD",  # 美元
    "EUR",  # 欧元
    "AUD",  # 澳元
    "CAD",  # 加元
    "CHF",  # 瑞士法郎
    "GBP",  # 英镑
    "JPY",  # 日元
    "NZD",  # 新西兰元
    "SGD",  # 新加坡元
]

# 目标货币（不支持的货币转换为该货币）
TARGET_CURRENCY = "HKD"

# 转换费率配置（基于中间市场汇率）
CONVERSION_FEE_RATES = {
    "stripe": {
        "min_rate": 0.02,  # 2%
        "max_rate": 0.04,  # 4%
        "default_rate": 0.03,  # 3%（中间值）
    },
    "paypal": {
        "min_rate": 0.03,  # 3%
        "max_rate": 0.04,  # 4%
        "default_rate": 0.035,  # 3.5%（中间值）
    }
}

# PayPal 固定费用配置
PAYPAL_FIXED_FEES = {
    "TWD": Decimal("10.00"),  # 台币交易固定费用
    "HKD": Decimal("2.35"),   # 港币交易固定费用
}


class CurrencyConverter:
    """货币转换工具类"""
    
    @staticmethod
    def is_supported_currency(currency: str) -> bool:
        """
        检查货币是否在支持列表中（1v1入账）
        
        Args:
            currency: 货币代码（如：USD, HKD, TWD等）
        
        Returns:
            bool: 如果货币在支持列表中返回True，否则返回False
        """
        return currency.upper() in SUPPORTED_CURRENCIES
    
    @staticmethod
    def needs_conversion(currency: str) -> bool:
        """
        判断货币是否需要转换
        
        Args:
            currency: 货币代码
        
        Returns:
            bool: 如果需要转换返回True，否则返回False
        """
        return not CurrencyConverter.is_supported_currency(currency)
    
    @staticmethod
    def get_target_currency() -> str:
        """
        获取目标货币（不支持的货币转换为该货币）
        
        Returns:
            str: 目标货币代码（默认HKD）
        """
        return TARGET_CURRENCY
    
    @staticmethod
    def calculate_conversion_fee(
        amount: str,
        provider: str,
        currency: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算转换费用
        
        Args:
            amount: 原始金额（字符串，如："19.90"）
            provider: 支付渠道（stripe/paypal）
            currency: 货币代码（可选，用于计算固定费用）
        
        Returns:
            包含转换费用信息的字典：
            {
                "conversion_fee": 转换费用金额,
                "conversion_fee_rate": 转换费率,
                "fixed_fee": 固定费用（PayPal）,
                "total_fee": 总费用
            }
        """
        amount_decimal = Decimal(str(amount))
        
        # 获取费率配置
        fee_config = CONVERSION_FEE_RATES.get(provider, CONVERSION_FEE_RATES["stripe"])
        fee_rate = fee_config["default_rate"]
        
        # 计算转换费用
        conversion_fee = amount_decimal * Decimal(str(fee_rate))
        conversion_fee = conversion_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # 计算固定费用（PayPal）
        fixed_fee = Decimal("0.00")
        if provider == "paypal" and currency:
            fixed_fee = PAYPAL_FIXED_FEES.get(currency.upper(), Decimal("0.00"))
        
        # 计算总费用
        total_fee = conversion_fee + fixed_fee
        
        return {
            "conversion_fee": float(conversion_fee),
            "conversion_fee_rate": float(fee_rate),
            "fixed_fee": float(fixed_fee),
            "total_fee": float(total_fee)
        }
    
    @staticmethod
    def calculate_converted_amount(
        original_amount: str,
        exchange_rate: Decimal,
        conversion_fee: Optional[Decimal] = None
    ) -> Decimal:
        """
        计算转换后的金额
        
        Args:
            original_amount: 原始金额（字符串）
            exchange_rate: 汇率
            conversion_fee: 转换费用（可选，如果提供则从金额中扣除）
        
        Returns:
            Decimal: 转换后的金额
        """
        amount_decimal = Decimal(str(original_amount))
        
        # 计算转换后的金额
        converted_amount = amount_decimal * exchange_rate
        
        # 如果提供了转换费用，从金额中扣除（商家承担，不影响客户支付金额）
        # 注意：这里不扣除，因为转换费用是商家承担的，客户支付的是转换后的金额
        # 转换费用单独记录
        
        return converted_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def get_fee_rate_range(provider: str) -> Tuple[float, float]:
        """
        获取费率范围
        
        Args:
            provider: 支付渠道（stripe/paypal）
        
        Returns:
            Tuple[float, float]: (最小费率, 最大费率)
        """
        fee_config = CONVERSION_FEE_RATES.get(provider, CONVERSION_FEE_RATES["stripe"])
        return (fee_config["min_rate"], fee_config["max_rate"])
    
    @staticmethod
    def get_paypal_fixed_fee(currency: str) -> Decimal:
        """
        获取 PayPal 固定费用
        
        Args:
            currency: 货币代码
        
        Returns:
            Decimal: 固定费用金额
        """
        return PAYPAL_FIXED_FEES.get(currency.upper(), Decimal("0.00"))
