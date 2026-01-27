#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Payssion支付客户端
支持LINE Pay等第三方支付方式，主要用于台湾地区
"""

import os
import logging
import hashlib
import hmac
import json
import requests
from typing import Optional, Dict, Any
from datetime import datetime

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


@register_payment_client("payssion")
class PayssionClient(BasePaymentClient):
    """Payssion支付客户端 - 专门用于LINE Pay等第三方支付"""

    def __init__(self, environment: Optional[str] = None):
        """初始化Payssion客户端

        Args:
            environment: 环境（production/sandbox），如果为None则自动查找is_active=1的记录
        """
        super().__init__(environment)

        # 从数据库读取配置
        self.api_key = get_payment_config('payssion', 'api_key', environment) or os.getenv("PAYSSION_API_KEY")
        self.secret = get_payment_config('payssion', 'secret', environment) or os.getenv("PAYSSION_SECRET")
        self.merchant_id = get_payment_config('payssion', 'merchant_id', environment) or os.getenv("PAYSSION_MERCHANT_ID")

        # 设置API基础URL
        if self.environment == "production":
            self.base_url = "https://api.payssion.com"
        else:
            self.base_url = "https://sandbox-api.payssion.com"

        if not all([self.api_key, self.secret, self.merchant_id]):
            logger.warning("Payssion配置不完整（数据库或环境变量）")

    @property
    def provider_name(self) -> str:
        """支付平台名称"""
        return "payssion"

    @property
    def is_enabled(self) -> bool:
        """检查Payssion客户端是否已启用"""
        return bool(self.api_key and self.secret and self.merchant_id)

    def get_supported_currencies(self) -> list:
        """获取Payssion支持的货币列表"""
        return ["USD", "HKD", "TWD", "JPY", "THB", "CNY", "EUR"]

    def get_supported_regions(self) -> list:
        """获取Payssion支持的地区列表"""
        return ["台湾", "日本", "泰国", "香港", "中国", "全球"]

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """生成Payssion API签名"""
        # 按照API文档要求构建签名字符串
        # 通常是按key排序后拼接
        sorted_keys = sorted(data.keys())
        sign_string = ""
        for key in sorted_keys:
            if data[key] is not None:
                sign_string += f"{key}={data[key]}&"

        # 移除最后一个&
        sign_string = sign_string.rstrip('&')

        # 使用HMAC-SHA256生成签名
        signature = hmac.new(
            self.secret.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def create_payment(self, **kwargs) -> Dict[str, Any]:
        """
        创建Payssion支付订单（主要用于LINE Pay）

        Args:
            amount: 金额（字符串，如"19.90"）
            currency: 货币代码（TWD, JPY, THB等）
            product_name: 产品名称
            order_id: 订单号
            payment_method: 支付方式（linepay等）
            customer_email: 客户邮箱

        Returns:
            包含transaction_id和payment_url的字典
        """
        amount = kwargs.get('amount', '19.90')
        currency = kwargs.get('currency', 'TWD')
        product_name = kwargs.get('product_name', '月订阅会员')
        order_id = kwargs.get('order_id', f"PAYSSION_{int(datetime.now().timestamp() * 1000)}")
        payment_method = kwargs.get('payment_method', 'linepay')
        customer_email = kwargs.get('customer_email', '')

        # 使用接口调用日志记录器
        api_logger = self._get_payment_api_logger()
        if api_logger:
            decorator = api_logger.log_api_call(
                "payssion.create_payment",
                log_request=True,
                log_response=True,
                log_billing=True
            )
            return decorator(self._create_payment_impl)(
                amount, currency, product_name, order_id, payment_method, customer_email
            )
        else:
            return self._create_payment_impl(
                amount, currency, product_name, order_id, payment_method, customer_email
            )

    def _create_payment_impl(
        self,
        amount: str,
        currency: str,
        product_name: str,
        order_id: str,
        payment_method: str,
        customer_email: str
    ) -> Dict[str, Any]:
        """创建支付订单的实现"""
        if not self.is_enabled:
            return {
                "success": False,
                "error": "Payssion客户端未初始化（缺少凭证）"
            }

        try:
            # 构建请求数据
            request_data = {
                "api_key": self.api_key,
                "merchant_id": self.merchant_id,
                "order_id": order_id,
                "amount": amount,
                "currency": currency.upper(),
                "description": product_name,
                "payment_method": payment_method,
                "notify_url": self._get_notify_url(),
                "success_url": self._get_success_url(),
                "fail_url": self._get_fail_url(),
            }

            if customer_email:
                request_data["payer_email"] = customer_email

            # 生成签名
            signature = self._generate_signature(request_data)
            request_data["sign"] = signature

            # 发送请求
            url = f"{self.base_url}/api/v1/payment"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Payssion-Client/1.0"
            }

            response = requests.post(url, json=request_data, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()

                if result.get("result_code") == "0000":  # 成功
                    transaction_data = result.get("transaction", {})

                    # 记录到数据库
                    if PaymentTransactionDAO:
                        try:
                            PaymentTransactionDAO().create_transaction(
                                order_id=order_id,
                                provider="payssion",
                                payment_id=transaction_data.get("transaction_id"),
                                amount=amount,
                                currency=currency,
                                status="pending",
                                customer_email=customer_email,
                                metadata={"payment_method": payment_method}
                            )
                        except Exception as e:
                            logger.warning(f"记录Payssion交易到数据库失败: {e}")

                    return {
                        "success": True,
                        "transaction_id": transaction_data.get("transaction_id"),
                        "order_id": order_id,
                        "payment_url": transaction_data.get("payment_url"),
                        "status": "created",
                        "payment_method": payment_method,
                        "message": "Payssion支付订单创建成功"
                    }
                else:
                    error_msg = result.get("result_message", "创建订单失败")
                    logger.error(f"创建Payssion订单失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"创建Payssion订单失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"创建订单失败: {error_msg}"
                }

        except Exception as e:
            logger.error(f"创建Payssion支付订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def verify_payment(self, **kwargs) -> Dict[str, Any]:
        """
        验证Payssion支付状态

        Args:
            transaction_id: 交易ID（必需）
            order_id: 订单号（可选）

        Returns:
            支付状态信息
        """
        transaction_id = kwargs.get('transaction_id')
        order_id = kwargs.get('order_id')

        if not transaction_id and not order_id:
            return {
                "success": False,
                "error": "Payssion验证需要提供transaction_id或order_id"
            }

        # 使用接口调用日志记录器
        api_logger = self._get_payment_api_logger()
        if api_logger:
            decorator = api_logger.log_api_call(
                "payssion.verify_payment",
                log_request=True,
                log_response=True
            )
            return decorator(self._verify_payment_impl)(transaction_id, order_id)
        else:
            return self._verify_payment_impl(transaction_id, order_id)

    def _verify_payment_impl(self, transaction_id: Optional[str], order_id: Optional[str]) -> Dict[str, Any]:
        """验证支付状态的实现"""
        if not self.is_enabled:
            return {
                "success": False,
                "error": "Payssion客户端未初始化（缺少凭证）"
            }

        try:
            # 构建请求数据
            request_data = {
                "api_key": self.api_key,
                "merchant_id": self.merchant_id,
            }

            if transaction_id:
                request_data["transaction_id"] = transaction_id
            if order_id:
                request_data["order_id"] = order_id

            # 生成签名
            signature = self._generate_signature(request_data)
            request_data["sign"] = signature

            # 发送请求
            url = f"{self.base_url}/api/v1/payment/status"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Payssion-Client/1.0"
            }

            response = requests.post(url, json=request_data, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()

                if result.get("result_code") == "0000":
                    transaction_data = result.get("transaction", {})
                    state = transaction_data.get("state", "")

                    # 转换状态
                    status_mapping = {
                        "completed": "success",
                        "pending": "pending",
                        "failed": "failed",
                        "cancelled": "cancelled"
                    }

                    status = status_mapping.get(state, state)
                    paid = status == "success"

                    return {
                        "success": True,
                        "status": status,
                        "paid": paid,
                        "transaction_id": transaction_data.get("transaction_id"),
                        "order_id": transaction_data.get("order_id"),
                        "amount": transaction_data.get("amount"),
                        "currency": transaction_data.get("currency"),
                        "paid_time": transaction_data.get("paid_time"),
                        "message": f"支付状态: {status}"
                    }
                else:
                    error_msg = result.get("result_message", "查询失败")
                    logger.error(f"查询Payssion订单失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"查询Payssion订单失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"查询订单失败: {error_msg}"
                }

        except Exception as e:
            logger.error(f"验证Payssion支付状态失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def refund(self, **kwargs) -> Dict[str, Any]:
        """
        Payssion退款

        Args:
            transaction_id: 原交易ID
            amount: 退款金额（可选）
            reason: 退款原因

        Returns:
            退款结果
        """
        transaction_id = kwargs.get('transaction_id')
        amount = kwargs.get('amount')
        reason = kwargs.get('reason', 'customer_request')

        if not transaction_id:
            return {
                "success": False,
                "error": "退款需要提供transaction_id"
            }

        if not self.is_enabled:
            return {
                "success": False,
                "error": "Payssion客户端未初始化（缺少凭证）"
            }

        try:
            # 构建请求数据
            request_data = {
                "api_key": self.api_key,
                "merchant_id": self.merchant_id,
                "transaction_id": transaction_id,
                "reason": reason
            }

            if amount:
                request_data["amount"] = amount

            # 生成签名
            signature = self._generate_signature(request_data)
            request_data["sign"] = signature

            # 发送请求
            url = f"{self.base_url}/api/v1/refund"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Payssion-Client/1.0"
            }

            response = requests.post(url, json=request_data, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()

                if result.get("result_code") == "0000":
                    return {
                        "success": True,
                        "refund_id": result.get("refund", {}).get("refund_id"),
                        "amount": amount or "full",
                        "status": "processing",
                        "message": "退款请求已提交"
                    }
                else:
                    error_msg = result.get("result_message", "退款失败")
                    logger.error(f"Payssion退款失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"Payssion退款失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"退款失败: {error_msg}"
                }

        except Exception as e:
            logger.error(f"Payssion退款失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def _get_payment_api_logger():
        """获取支付接口调用日志记录器"""
        if get_payment_api_logger:
            return get_payment_api_logger()
        return None

    def _get_notify_url(self) -> str:
        """获取支付通知URL"""
        api_base = get_payment_config('shared', 'api_base_url') or os.getenv("API_BASE_URL", "http://localhost:8001")
        return f"{api_base}/api/v1/payment/webhook/payssion"

    def _get_success_url(self) -> str:
        """获取支付成功跳转URL"""
        frontend_base = get_payment_config('shared', 'frontend_base_url') or os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
        return f"{frontend_base}/frontend/payment-success.html?provider=payssion"

    def _get_fail_url(self) -> str:
        """获取支付失败跳转URL"""
        frontend_base = get_payment_config('shared', 'frontend_base_url') or os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
        return f"{frontend_base}/frontend/payment-cancel.html?provider=payssion"