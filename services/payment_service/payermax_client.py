#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PayerMax支付客户端
支持全球600+支付方式，专注于新兴市场
"""

import os
import logging
import json
import base64
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

try:
    import requests
except ImportError:
    requests = None

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


@register_payment_client("payermax")
class PayerMaxClient(BasePaymentClient):
    """PayerMax支付客户端"""

    def __init__(self, environment: Optional[str] = None):
        """初始化PayerMax客户端

        Args:
            environment: 环境（production/sandbox），如果为None则自动查找is_active=1的记录
        """
        # 如果未指定环境，自动推断
        if environment is None:
            environment = get_payment_environment('payermax', 'production')
        
        super().__init__(environment)

        # 从数据库读取配置
        self.app_id = get_payment_config('payermax', 'app_id', environment) or os.getenv("PAYERMAX_APP_ID")
        self.merchant_no = get_payment_config('payermax', 'merchant_no', environment) or os.getenv("PAYERMAX_MERCHANT_NO")

        # 读取RSA密钥路径
        private_key_path = get_payment_config('payermax', 'private_key_path', environment) or os.getenv("PAYERMAX_PRIVATE_KEY_PATH")
        public_key_path = get_payment_config('payermax', 'public_key_path', environment) or os.getenv("PAYERMAX_PUBLIC_KEY_PATH")

        # 加载RSA密钥
        self.private_key = None
        self.public_key = None

        if private_key_path and os.path.exists(private_key_path):
            try:
                with open(private_key_path, 'rb') as f:
                    self.private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                        backend=default_backend()
                    )
                logger.info("PayerMax私钥加载成功")
            except Exception as e:
                logger.error(f"加载PayerMax私钥失败: {e}")

        if public_key_path and os.path.exists(public_key_path):
            try:
                with open(public_key_path, 'rb') as f:
                    self.public_key = serialization.load_pem_public_key(
                        f.read(),
                        backend=default_backend()
                    )
                logger.info("PayerMax公钥加载成功")
            except Exception as e:
                logger.error(f"加载PayerMax公钥失败: {e}")

        # 设置API基础URL（根据实际环境或 mode 配置）
        # 检查是否有 mode 配置（sandbox/production）
        mode = get_payment_config('payermax', 'mode', environment) or os.getenv("PAYERMAX_MODE", "")
        if mode and mode.lower() == "sandbox":
            self.base_url = "https://pay-gate-uat.payermax.com/aggregate-pay/api/gateway/"
        elif self.environment == "production":
            self.base_url = "https://pay-gate.payermax.com/aggregate-pay/api/gateway/"
        else:
            self.base_url = "https://pay-gate-uat.payermax.com/aggregate-pay/api/gateway/"
        
        logger.info(f"PayerMax API URL: {self.base_url} (environment={self.environment}, mode={mode})")

        if not all([self.app_id, self.merchant_no, self.private_key]):
            logger.warning("PayerMax配置不完整（数据库或环境变量）")

    @property
    def provider_name(self) -> str:
        """支付平台名称"""
        return "payermax"

    @property
    def is_enabled(self) -> bool:
        """检查PayerMax客户端是否已启用"""
        return bool(self.app_id and self.merchant_no and self.private_key and requests)

    def get_supported_currencies(self) -> list:
        """获取PayerMax支持的货币列表"""
        return ["USD", "HKD", "EUR", "GBP", "SGD", "AUD", "CAD", "JPY", "CNY", "THB", "PHP", "MYR", "IDR", "VND"]

    def get_supported_regions(self) -> list:
        """获取PayerMax支持的地区列表"""
        return ["全球", "东南亚", "欧洲", "美洲", "中东", "非洲"]

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """
        生成PayerMax RSA签名

        Args:
            data: 请求数据字典

        Returns:
            Base64编码的签名
        """
        if not self.private_key:
            raise ValueError("私钥未加载，无法生成签名")

        # 构建签名字符串
        sign_string = json.dumps(data, separators=(',', ':'), sort_keys=True)

        # 使用SHA256WithRSA签名
        signature = self.private_key.sign(
            sign_string.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        # Base64编码
        return base64.b64encode(signature).decode('utf-8')

    def _verify_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """
        验证PayerMax响应签名

        Args:
            data: 响应数据字典
            signature: Base64编码的签名

        Returns:
            签名是否有效
        """
        if not self.public_key:
            logger.warning("公钥未加载，无法验证签名")
            return False

        try:
            # 构建验证字符串
            verify_string = json.dumps(data, separators=(',', ':'), sort_keys=True)

            # 解码签名
            signature_bytes = base64.b64decode(signature)

            # 验证签名
            self.public_key.verify(
                signature_bytes,
                verify_string.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"验证PayerMax签名失败: {e}")
            return False

    def create_payment(self, **kwargs) -> Dict[str, Any]:
        """
        创建PayerMax支付订单

        Args:
            amount: 金额（字符串，如"19.90"）
            currency: 货币代码
            product_name: 产品名称
            order_id: 订单号
            payment_method: 支付方式（可选，空则使用收银台）
            customer_email: 客户邮箱

        Returns:
            包含订单信息的字典
        """
        amount = kwargs.get('amount', '19.90')
        currency = kwargs.get('currency', 'USD')
        product_name = kwargs.get('product_name', '月订阅会员')
        order_id = kwargs.get('order_id', f"PAYERMAX_{int(datetime.now().timestamp() * 1000)}")
        payment_method = kwargs.get('payment_method')
        customer_email = kwargs.get('customer_email', '')

        # 使用接口调用日志记录器
        api_logger = self._get_payment_api_logger()
        if api_logger:
            decorator = api_logger.log_api_call(
                "payermax.create_payment",
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
        payment_method: Optional[str],
        customer_email: str
    ) -> Dict[str, Any]:
        """创建支付订单的实现"""
        if not self.is_enabled:
            return {
                "success": False,
                "error": "PayerMax客户端未初始化（缺少凭证或密钥）"
            }

        try:
            # 构建请求数据
            request_data = {
                "version": "1.1",
                "keyVersion": "1",
                "requestTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "appId": self.app_id,
                "merchantNo": self.merchant_no,
                "data": {
                    "merchantOrderNo": order_id,
                    "amount": {
                        "value": amount,
                        "currency": currency.upper()
                    },
                    "subject": product_name,
                    "notifyUrl": self._get_notify_url(),
                    "returnUrl": self._get_success_url(),
                    "userInfo": {
                        "userId": customer_email or "anonymous",
                        "userEmail": customer_email
                    }
                }
            }

            # PayerMax 统一使用 orderAndPay 端点（收银台模式）
            # 如果指定了支付方式，添加到请求数据中
            if payment_method:
                request_data["data"]["paymentDetail"] = {
                    "paymentMethodType": payment_method
                }
            
            api_path = "orderAndPay"

            # 生成签名
            signature = self._generate_signature(request_data["data"])
            request_data["sign"] = signature

            # 发送请求
            url = f"{self.base_url}{api_path}"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "PayerMax-Client/1.0"
            }

            logger.info(f"PayerMax请求URL: {url}")
            logger.info(f"PayerMax请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
            response = requests.post(url, json=request_data, headers=headers, timeout=30)
            logger.info(f"PayerMax响应状态码: {response.status_code}")
            logger.info(f"PayerMax响应内容: {response.text[:500]}")

            if response.status_code == 200:
                result = response.json()

                # 验证响应签名
                response_data = result.get("data", {})
                response_sign = result.get("sign")
                if response_sign and not self._verify_signature(response_data, response_sign):
                    logger.warning("PayerMax响应签名验证失败")

                if result.get("code") == "APPLY_SUCCESS":
                    # 记录到数据库
                    if PaymentTransactionDAO:
                        try:
                            PaymentTransactionDAO().create_transaction(
                                order_id=order_id,
                                provider="payermax",
                                payment_id=response_data.get("transactionNo"),
                                amount=amount,
                                currency=currency,
                                status="pending",
                                customer_email=customer_email,
                                metadata={"payment_method": payment_method}
                            )
                        except Exception as e:
                            logger.warning(f"记录PayerMax交易到数据库失败: {e}")

                    payment_url = response_data.get("paymentUrl") or response_data.get("cashierUrl")

                    return {
                        "success": True,
                        "transaction_id": response_data.get("transactionNo"),
                        "order_id": order_id,
                        "payment_url": payment_url,
                        "status": "created",
                        "payment_method": payment_method,
                        "message": "PayerMax支付订单创建成功"
                    }
                else:
                    error_msg = result.get("message", "创建订单失败")
                    error_code = result.get("code", "UNKNOWN")
                    logger.error(f"创建PayerMax订单失败: code={error_code}, message={error_msg}, full_response={result}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"创建PayerMax订单失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"创建订单失败: {error_msg}"
                }

        except Exception as e:
            logger.error(f"创建PayerMax支付订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def verify_payment(self, **kwargs) -> Dict[str, Any]:
        """
        验证PayerMax支付状态

        Args:
            transaction_id: 交易ID
            order_id: 订单号

        Returns:
            支付状态信息
        """
        transaction_id = kwargs.get('transaction_id')
        order_id = kwargs.get('order_id')

        if not transaction_id and not order_id:
            return {
                "success": False,
                "error": "PayerMax验证需要提供transaction_id或order_id"
            }

        # 使用接口调用日志记录器
        api_logger = self._get_payment_api_logger()
        if api_logger:
            decorator = api_logger.log_api_call(
                "payermax.verify_payment",
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
                "error": "PayerMax客户端未初始化（缺少凭证或密钥）"
            }

        try:
            # 构建请求数据
            request_data = {
                "version": "1.1",
                "keyVersion": "1",
                "requestTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "appId": self.app_id,
                "merchantNo": self.merchant_no,
                "data": {}
            }

            if transaction_id:
                request_data["data"]["transactionNo"] = transaction_id
            if order_id:
                request_data["data"]["merchantOrderNo"] = order_id

            # 生成签名
            signature = self._generate_signature(request_data["data"])
            request_data["sign"] = signature

            # 发送请求
            url = f"{self.base_url}orderQuery"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "PayerMax-Client/1.0"
            }

            response = requests.post(url, json=request_data, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()

                # 验证响应签名
                response_data = result.get("data", {})
                response_sign = result.get("sign")
                if response_sign and not self._verify_signature(response_data, response_sign):
                    logger.warning("PayerMax响应签名验证失败")

                if result.get("code") == "APPLY_SUCCESS":
                    order_info = response_data.get("orderInfo", {})
                    pay_status = order_info.get("payStatus", "")

                    # 转换状态
                    status_mapping = {
                        "SUCCESS": "success",
                        "PENDING": "pending",
                        "FAILED": "failed",
                        "CANCELLED": "cancelled"
                    }

                    status = status_mapping.get(pay_status, pay_status)
                    paid = status == "success"

                    amount_info = order_info.get("amount", {})
                    currency_info = order_info.get("currency", {})

                    return {
                        "success": True,
                        "status": status,
                        "paid": paid,
                        "transaction_id": order_info.get("transactionNo"),
                        "order_id": order_info.get("merchantOrderNo"),
                        "amount": amount_info.get("value"),
                        "currency": amount_info.get("currency"),
                        "paid_time": order_info.get("payTime"),
                        "message": f"支付状态: {status}"
                    }
                else:
                    error_msg = result.get("message", "查询失败")
                    logger.error(f"查询PayerMax订单失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"查询PayerMax订单失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"查询订单失败: {error_msg}"
                }

        except Exception as e:
            logger.error(f"验证PayerMax支付状态失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def refund(self, **kwargs) -> Dict[str, Any]:
        """
        PayerMax退款

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
                "error": "PayerMax客户端未初始化（缺少凭证或密钥）"
            }

        try:
            # 构建请求数据
            request_data = {
                "version": "1.1",
                "keyVersion": "1",
                "requestTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "appId": self.app_id,
                "merchantNo": self.merchant_no,
                "data": {
                    "transactionNo": transaction_id,
                    "refundReason": reason
                }
            }

            if amount:
                request_data["data"]["refundAmount"] = {
                    "value": amount,
                    "currency": "USD"  # 假设退款货币与原交易相同
                }

            # 生成签名
            signature = self._generate_signature(request_data["data"])
            request_data["sign"] = signature

            # 发送请求
            url = f"{self.base_url}refund"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "PayerMax-Client/1.0"
            }

            response = requests.post(url, json=request_data, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()

                # 验证响应签名
                response_data = result.get("data", {})
                response_sign = result.get("sign")
                if response_sign and not self._verify_signature(response_data, response_sign):
                    logger.warning("PayerMax响应签名验证失败")

                if result.get("code") == "APPLY_SUCCESS":
                    return {
                        "success": True,
                        "refund_id": response_data.get("refundNo"),
                        "amount": amount or "full",
                        "status": "processing",
                        "message": "退款请求已提交"
                    }
                else:
                    error_msg = result.get("message", "退款失败")
                    logger.error(f"PayerMax退款失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"PayerMax退款失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"退款失败: {error_msg}"
                }

        except Exception as e:
            logger.error(f"PayerMax退款失败: {e}")
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
        return f"{api_base}/api/v1/payment/webhook/payermax"

    def _get_success_url(self) -> str:
        """获取支付成功跳转URL"""
        frontend_base = get_payment_config('shared', 'frontend_base_url') or os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
        return f"{frontend_base}/frontend/payment-success.html?provider=payermax"