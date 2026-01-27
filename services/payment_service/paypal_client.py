#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PayPal支付客户端封装
支持PayPal Checkout支付功能
使用直接HTTP请求，无需额外SDK
"""

import os
import logging
import base64
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

# 导入货币转换工具
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

logger = logging.getLogger(__name__)


class PayPalClient:
    """PayPal支付客户端"""
    
    def __init__(self, environment: Optional[str] = None):
        """
        初始化PayPal客户端
        
        Args:
            environment: 环境（production/sandbox），如果为None则自动查找is_active=1的记录
        """
        self.environment = environment
        
        # 从数据库读取配置，自动查找is_active=1的记录
        # 如果指定了environment，则优先匹配该环境且is_active=1的记录
        self.client_id = get_payment_config('paypal', 'client_id', environment) or os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = get_payment_config('paypal', 'client_secret', environment) or os.getenv("PAYPAL_CLIENT_SECRET")
        mode_from_db = get_payment_config('paypal', 'mode', environment)
        self.mode = mode_from_db or os.getenv("PAYPAL_MODE", "sandbox")  # sandbox or live
        
        # 设置API基础URL
        if self.mode == "live":
            self.base_url = "https://api.paypal.com"
        else:
            self.base_url = "https://api.sandbox.paypal.com"
        
        if not self.client_id or not self.client_secret:
            logger.warning("PayPal客户端ID或密钥未配置（数据库或环境变量）")
            self.access_token = None
        else:
            # 获取访问令牌
            self.access_token = self._get_access_token()
    
    @property
    def is_enabled(self) -> bool:
        """检查PayPal客户端是否已启用"""
        return bool(self.client_id and self.client_secret and self.access_token)
    
    def _get_access_token(self) -> Optional[str]:
        """
        获取PayPal访问令牌（OAuth 2.0）
        
        Returns:
            访问令牌，失败返回None
        """
        if not self.client_id or not self.client_secret:
            return None
        
        try:
            # 构建认证头
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            # 请求访问令牌
            url = f"{self.base_url}/v1/oauth2/token"
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {
                "grant_type": "client_credentials"
            }
            
            response = requests.post(url, headers=headers, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                token = result.get("access_token")
                logger.info("PayPal访问令牌获取成功")
                return token
            else:
                logger.error(f"获取PayPal访问令牌失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取PayPal访问令牌异常: {e}")
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        if not self.access_token:
            # 尝试重新获取令牌
            self.access_token = self._get_access_token()
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def create_payment(
        self,
        amount: str,
        currency: str = "USD",
        product_name: Optional[str] = None,
        description: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建PayPal支付（统一支付API接口）
        
        Args:
            amount: 金额（字符串，如"19.90"）
            currency: 货币代码（USD, EUR, GBP等）
            product_name: 产品名称（优先使用）
            description: 订单描述（如果未提供product_name则使用）
            return_url: 支付成功后跳转URL
            cancel_url: 取消支付跳转URL
        
        Returns:
            包含payment_id（即order_id）和approval_url的字典
        """
        # 使用 product_name 或 description
        order_description = product_name or description or "Purchase"
        
        # 调用 create_order
        result = self.create_order(
            amount=amount,
            currency=currency,
            description=order_description,
            return_url=return_url,
            cancel_url=cancel_url,
            order_id=order_id
        )
        
        # 转换字段名：order_id -> payment_id
        if result.get("success") and "order_id" in result:
            result["payment_id"] = result.pop("order_id")
        
        return result
    
    @staticmethod
    def _get_payment_api_logger():
        """获取支付接口调用日志记录器"""
        if get_payment_api_logger:
            return get_payment_api_logger()
        return None
    
    def get_exchange_rate_quote(
        self,
        base_currency: str,
        base_amount: str,
        quote_currency: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取 PayPal 汇率报价（FXaaS）
        
        Args:
            base_currency: 源货币代码
            base_amount: 源金额
            quote_currency: 目标货币代码
        
        Returns:
            汇率报价信息，包含 fx_id, fx_rate, quote_amount 等
        """
        if not self.access_token:
            return None
        
        try:
            url = f"{self.base_url}/v2/pricing/quote-exchange-rates"
            headers = self._get_headers()
            data = {
                "base_currency": base_currency,
                "base_amount": {
                    "value": base_amount,
                    "currency_code": base_currency
                },
                "quote_currency": quote_currency
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "fx_id": result.get("fx_id"),
                    "fx_rate": result.get("fx_rate"),
                    "quote_amount": result.get("quote_amount", {}).get("value"),
                    "expires_at": result.get("expires_at")
                }
            else:
                logger.error(f"获取PayPal汇率报价失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"获取PayPal汇率报价异常: {e}", exc_info=True)
            return None
    
    def create_order(
        self,
        amount: str,
        currency: str = "USD",
        description: str = "Purchase",
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建PayPal订单
        
        Args:
            amount: 金额（字符串，如"19.90"）
            currency: 货币代码（USD, EUR, GBP等）
            description: 订单描述
            return_url: 支付成功后跳转URL
            cancel_url: 取消支付跳转URL
            order_id: 订单号（用于关联交易记录）
        
        Returns:
            包含order_id和approval_url的字典
        """
        # 使用接口调用日志记录器
        api_logger = self._get_payment_api_logger()
        if api_logger:
            decorator = api_logger.log_api_call(
                "paypal.create_order",
                log_request=True,
                log_response=True,
                log_billing=True
            )
            return decorator(self._create_order_impl)(
                amount, currency, description, return_url, cancel_url, order_id
            )
        else:
            return self._create_order_impl(
                amount, currency, description, return_url, cancel_url, order_id
            )
    
    def _create_order_impl(
        self,
        amount: str,
        currency: str = "USD",
        description: str = "Purchase",
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建PayPal订单的实现方法
        """
        # 如果初始化时没有配置，尝试重新加载（支持热更新）
        if not self.access_token:
            self.client_id = get_payment_config('paypal', 'client_id', self.environment) or os.getenv("PAYPAL_CLIENT_ID")
            self.client_secret = get_payment_config('paypal', 'client_secret', self.environment) or os.getenv("PAYPAL_CLIENT_SECRET")
            if self.client_id and self.client_secret:
                self.access_token = self._get_access_token()
        
        if not self.access_token:
            return {
                "success": False,
                "error": "PayPal客户端未初始化（无法获取访问令牌）"
            }
        
        # 货币转换逻辑
        original_currency = currency.upper()
        needs_conversion = False
        converted_amount = amount
        converted_currency = currency
        conversion_fee_info = None
        fx_quote = None
        exchange_rate = None
        
        if CurrencyConverter:
            needs_conversion = CurrencyConverter.needs_conversion(original_currency)
            
            if needs_conversion:
                # 需要转换：转换为HKD
                converted_currency = CurrencyConverter.get_target_currency()
                
                # 获取 PayPal 汇率报价（FXaaS）
                fx_quote = self.get_exchange_rate_quote(
                    base_currency=original_currency,
                    base_amount=amount,
                    quote_currency=converted_currency
                )
                
                if fx_quote:
                    exchange_rate = float(fx_quote.get("fx_rate", 1.0))
                    converted_amount = fx_quote.get("quote_amount", amount)
                    logger.info(f"PayPal汇率报价: {original_currency} -> {converted_currency}, 汇率={exchange_rate}, 金额={converted_amount}")
                else:
                    # 如果获取汇率报价失败，使用默认汇率（1:1，实际应该从其他地方获取）
                    logger.warning(f"获取PayPal汇率报价失败，使用默认汇率")
                    exchange_rate = 1.0
                    converted_amount = amount
                
                # 计算转换费用（商家承担）
                conversion_fee_info = CurrencyConverter.calculate_conversion_fee(
                    converted_amount, "paypal", original_currency
                )
                logger.info(f"货币需要转换: {original_currency} -> {converted_currency}, 费用: {conversion_fee_info}")
        
        try:
            # 设置默认URL
            frontend_base = get_payment_config('shared', 'frontend_base_url') or os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
            
            if not return_url:
                return_url = f"{frontend_base}/frontend/payment-success.html?provider=paypal"
            
            if not cancel_url:
                cancel_url = f"{frontend_base}/frontend/payment-cancel.html?provider=paypal"
            
            # 构建请求数据
            url = f"{self.base_url}/v2/checkout/orders"
            headers = self._get_headers()
            
            # 构建 purchase_units
            purchase_unit = {
                "amount": {
                    "currency_code": converted_currency if needs_conversion else currency,
                    "value": converted_amount if needs_conversion else amount
                },
                "description": description
            }
            
            # 如果使用了 FXaaS，添加 fx 参数
            if needs_conversion and fx_quote and fx_quote.get("fx_id"):
                purchase_unit["fx"] = {
                    "fx_id": fx_quote["fx_id"],
                    "fx_rate": fx_quote["fx_rate"]
                }
            
            data = {
                "intent": "CAPTURE",
                "purchase_units": [purchase_unit],
                "application_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                    "brand_name": "HiFate",
                    "user_action": "PAY_NOW"
                }
            }
            
            # 执行请求
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                paypal_order_id = result.get("id")
                
                # 获取approval_url
                approval_url = None
                links = result.get("links", [])
                for link in links:
                    if link.get("rel") == "approve":
                        approval_url = link.get("href")
                        break
                
                # 记录交易信息到数据库
                if PaymentTransactionDAO and order_id:
                    transaction_id = PaymentTransactionDAO.create_transaction(
                        order_id=order_id,
                        provider="paypal",
                        original_amount=amount,
                        original_currency=original_currency,
                        converted_amount=converted_amount if needs_conversion else None,
                        converted_currency=converted_currency if needs_conversion else original_currency,
                        needs_conversion=needs_conversion,
                        conversion_fee=conversion_fee_info.get("conversion_fee") if conversion_fee_info else None,
                        conversion_fee_rate=conversion_fee_info.get("conversion_fee_rate") if conversion_fee_info else None,
                        fixed_fee=conversion_fee_info.get("fixed_fee") if conversion_fee_info else None,
                        exchange_rate=exchange_rate,
                        customer_email=None,  # PayPal在支付时获取
                        product_name=description,
                        metadata={"paypal_order_id": paypal_order_id}
                    )
                    
                    # 记录汇率和费率到历史表
                    if get_fx_risk_monitor:
                        fx_monitor = get_fx_risk_monitor()
                        if exchange_rate:
                            fx_monitor.record_exchange_rate(
                                from_currency=original_currency,
                                to_currency=converted_currency if needs_conversion else original_currency,
                                exchange_rate=exchange_rate,
                                provider="paypal",
                                transaction_id=transaction_id,
                                source="fx_quote"
                            )
                        if conversion_fee_info and conversion_fee_info.get("conversion_fee_rate"):
                            fx_monitor.record_conversion_fee(
                                provider="paypal",
                                from_currency=original_currency,
                                to_currency=converted_currency if needs_conversion else original_currency,
                                fee_rate=conversion_fee_info["conversion_fee_rate"],
                                fixed_fee=conversion_fee_info.get("fixed_fee", 0.0),
                                transaction_id=transaction_id
                            )
                
                return {
                    "success": True,
                    "order_id": paypal_order_id,
                    "approval_url": approval_url,
                    "status": result.get("status"),
                    "message": "PayPal订单创建成功",
                    "needs_conversion": needs_conversion,
                    "original_currency": original_currency,
                    "converted_currency": converted_currency if needs_conversion else original_currency,
                    "fx_id": fx_quote.get("fx_id") if fx_quote else None,
                }
            else:
                error_msg = response.text
                logger.error(f"创建PayPal订单失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"创建订单失败: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"创建PayPal订单失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def capture_order(self, order_id: str) -> Dict[str, Any]:
        """
        捕获（完成）PayPal订单
        
        Args:
            order_id: PayPal订单ID
        
        Returns:
            捕获结果
        """
        if not self.access_token:
            return {
                "success": False,
                "error": "PayPal客户端未初始化（无法获取访问令牌）"
            }
        
        try:
            url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
            headers = self._get_headers()
            
            # 执行请求（POST请求，无需body）
            response = requests.post(url, headers=headers, json={}, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                status = result.get("status")
                
                # 提取支付信息
                payer_info = result.get("payer", {})
                payer_email = payer_info.get("email_address") if payer_info else None
                
                purchase_units = result.get("purchase_units", [])
                amount_info = None
                currency_info = None
                if purchase_units:
                    amount_obj = purchase_units[0].get("payments", {}).get("captures", [{}])[0].get("amount", {})
                    amount_info = amount_obj.get("value")
                    currency_info = amount_obj.get("currency_code")
                
                result = {
                    "success": True,
                    "order_id": order_id,
                    "status": status,
                    "paid": status == "COMPLETED",
                    "payer_email": payer_email,
                    "amount": amount_info,
                    "currency": currency_info,
                    "message": "订单已完成"
                }
                
                # 支付成功时，更新交易记录的实际汇率
                if PaymentTransactionDAO:
                    # 从 PayPal 响应中提取实际汇率
                    # PayPal 的汇率信息可能在 purchase_units 中
                    actual_exchange_rate = None
                    if purchase_units:
                        fx_info = purchase_units[0].get("fx")
                        if fx_info:
                            actual_exchange_rate = float(fx_info.get("fx_rate", 0))
                    
                    # 更新交易记录（通过 order_id 查找）
                    transaction = PaymentTransactionDAO.get_transaction_by_order_id(order_id)
                    if transaction:
                        PaymentTransactionDAO.update_transaction(
                            transaction_id=transaction['id'],
                            provider_payment_id=order_id,
                            status="success" if status == "COMPLETED" else "pending",
                            actual_exchange_rate=actual_exchange_rate,
                            paid_at=datetime.now().isoformat() if status == "COMPLETED" else None
                        )
                        
                        # 记录实际汇率到历史表
                        if actual_exchange_rate and get_fx_risk_monitor:
                            fx_monitor = get_fx_risk_monitor()
                            fx_monitor.record_exchange_rate(
                                from_currency=transaction.get('original_currency', 'USD'),
                                to_currency=transaction.get('converted_currency', 'HKD'),
                                exchange_rate=actual_exchange_rate,
                                provider="paypal",
                                transaction_id=transaction['id'],
                                source="transaction"
                            )
                
                return result
            else:
                error_msg = response.text
                logger.error(f"捕获PayPal订单失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"捕获订单失败: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"捕获PayPal订单失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_payment(self, order_id: str) -> Dict[str, Any]:
        """
        查询订单状态
        
        Args:
            order_id: PayPal订单ID
        
        Returns:
            订单状态信息
        """
        if not self.access_token:
            return {
                "success": False,
                "error": "PayPal客户端未初始化（无法获取访问令牌）"
            }
        
        try:
            url = f"{self.base_url}/v2/checkout/orders/{order_id}"
            headers = self._get_headers()
            
            # 执行请求
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("status")
                
                # 提取金额信息
                purchase_units = result.get("purchase_units", [])
                amount_info = None
                currency_info = None
                if purchase_units:
                    amount_obj = purchase_units[0].get("amount", {})
                    amount_info = amount_obj.get("value")
                    currency_info = amount_obj.get("currency_code")
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "status": status,
                    "paid": status == "COMPLETED",
                    "amount": amount_info,
                    "currency": currency_info,
                    "message": f"订单状态: {status}"
                }
            else:
                error_msg = response.text
                logger.error(f"查询PayPal订单失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"查询订单失败: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"查询PayPal订单失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
