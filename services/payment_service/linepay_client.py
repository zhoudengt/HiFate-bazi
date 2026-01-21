#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Line Pay支付客户端封装
支持Line Pay在线支付功能
使用直接HTTP请求，无需额外SDK
"""

import os
import logging
import hmac
import hashlib
import base64
import uuid
import json
import requests
from typing import Optional, Dict, Any

# 导入支付配置加载器
try:
    from services.payment_service.payment_config_loader import get_payment_config, get_payment_environment
except ImportError:
    # 降级到环境变量
    def get_payment_config(provider: str, config_key: str, environment: str = 'production', default: Optional[str] = None) -> Optional[str]:
        return os.getenv(f"{provider.upper()}_{config_key.upper()}", default)
    def get_payment_environment(default: str = 'production') -> str:
        return os.getenv("PAYMENT_ENVIRONMENT", default)

logger = logging.getLogger(__name__)


class LinePayClient:
    """Line Pay支付客户端"""
    
    def __init__(self, environment: Optional[str] = None):
        """
        初始化Line Pay客户端
        
        Args:
            environment: 环境（production/sandbox），如果为None则自动查找is_active=1的记录
        """
        # 从数据库读取配置，自动查找is_active=1的记录
        # 如果指定了environment，则优先匹配该环境且is_active=1的记录
        self.channel_id = get_payment_config('linepay', 'channel_id', environment) or os.getenv("LINEPAY_CHANNEL_ID")
        self.channel_secret = get_payment_config('linepay', 'channel_secret', environment) or os.getenv("LINEPAY_CHANNEL_SECRET")
        mode_from_db = get_payment_config('linepay', 'mode', environment)
        self.mode = mode_from_db or os.getenv("LINEPAY_MODE", "sandbox")  # sandbox or production
        
        # 设置API基础URL
        if self.mode == "production":
            production_url = get_payment_config('linepay', 'production_url', environment)
            self.base_url = production_url or os.getenv(
                "LINEPAY_PRODUCTION_URL", 
                "https://api-pay.line.me"
            )
        else:
            sandbox_url = get_payment_config('linepay', 'sandbox_url', environment)
            self.base_url = sandbox_url or os.getenv(
                "LINEPAY_SANDBOX_URL",
                "https://sandbox-api-pay.line.me"
            )
        
        if not self.channel_id or not self.channel_secret:
            logger.warning("Line Pay渠道ID或密钥未配置（数据库或环境变量）")
    
    @property
    def is_enabled(self) -> bool:
        """检查Line Pay客户端是否已启用"""
        return bool(self.channel_id and self.channel_secret)
    
    def _generate_signature(self, uri: str, body: str, nonce: str) -> str:
        """
        生成LINE Pay HMAC-SHA256签名
        
        Args:
            uri: API路径（如 /v3/payments/request）
            body: 请求体JSON字符串
            nonce: 随机UUID或时间戳
        
        Returns:
            Base64编码的签名
        """
        message = self.channel_secret + uri + body + nonce
        signature = hmac.new(
            self.channel_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(self, uri: str, body: str) -> Dict[str, str]:
        """获取API请求头（包含签名）"""
        nonce = str(uuid.uuid4())
        signature = self._generate_signature(uri, body, nonce)
        
        return {
            "Content-Type": "application/json",
            "X-LINE-ChannelId": self.channel_id,
            "X-LINE-Authorization-Nonce": nonce,
            "X-LINE-Authorization": signature
        }
    
    def create_payment(
        self,
        amount: str,
        currency: str = "TWD",
        product_name: Optional[str] = None,
        order_id: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        confirm_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建Line Pay支付请求
        
        Args:
            amount: 金额（字符串，如"100.00"）
            currency: 货币代码（TWD, JPY, THB, USD）
            product_name: 产品名称
            order_id: 商户订单号（可选，如不提供则自动生成）
            return_url: 支付成功后跳转URL
            cancel_url: 支付取消后跳转URL
            confirm_url: 支付确认回调URL
        
        Returns:
            包含transactionId和paymentUrl的字典
        """
        if not self.is_enabled:
            return {
                "success": False,
                "error": "Line Pay客户端未初始化（缺少凭证）"
            }
        
        try:
            # 设置默认URL
            # 从数据库读取URL，如果数据库中没有则降级到环境变量
            frontend_base = get_payment_config('shared', 'frontend_base_url') or os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
            api_base = get_payment_config('shared', 'api_base_url') or os.getenv("API_BASE_URL", "http://localhost:8001")
            
            if not return_url:
                return_url = f"{frontend_base}/frontend/payment-success.html?provider=linepay"
            
            if not cancel_url:
                cancel_url = f"{frontend_base}/frontend/payment-cancel.html?provider=linepay"
            
            if not confirm_url:
                confirm_url = f"{api_base}/api/v1/payment/webhook/linepay"
            
            # 生成订单号
            if not order_id:
                import time
                order_id = f"ORDER_{int(time.time() * 1000)}"
            
            # 构建请求数据
            uri = "/v3/payments/request"
            url = f"{self.base_url}{uri}"
            
            # TWD、JPY、THB 是零小数货币，必须使用整数
            currency_upper = currency.upper()
            zero_decimal_currencies = ["TWD", "JPY", "THB"]
            
            if currency_upper in zero_decimal_currencies:
                # 零小数货币：直接使用整数
                amount_value = int(float(amount))
            else:
                # 其他货币：使用浮点数（如USD需要乘以100）
                amount_value = float(amount)
            
            data = {
                "amount": amount_value,
                "currency": currency_upper,
                "orderId": order_id,
                "packages": [{
                    "id": f"package_{order_id}",
                    "amount": amount_value,
                    "name": product_name or "Purchase",
                    "products": [{
                        "name": product_name or "Purchase",
                        "quantity": 1,
                        "price": amount_value
                    }]
                }],
                "redirectUrls": {
                    "confirmUrl": confirm_url,
                    "cancelUrl": cancel_url
                }
            }
            
            body = json.dumps(data, separators=(',', ':'))
            headers = self._get_headers(uri, body)
            
            # 执行请求
            response = requests.post(url, headers=headers, data=body, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("returnCode") == "0000":
                    info = result.get("info", {})
                    transaction_id = info.get("transactionId")
                    payment_url = info.get("paymentUrl", {}).get("web")
                    
                    return {
                        "success": True,
                        "transaction_id": transaction_id,
                        "order_id": order_id,
                        "payment_url": payment_url,
                        "status": "created",
                        "message": "Line Pay订单创建成功"
                    }
                else:
                    error_msg = result.get("returnMessage", "创建订单失败")
                    logger.error(f"创建Line Pay订单失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"创建Line Pay订单失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"创建订单失败: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"创建Line Pay订单失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def confirm_payment(
        self,
        transaction_id: str,
        amount: str,
        currency: str = "TWD"
    ) -> Dict[str, Any]:
        """
        确认Line Pay支付（在用户完成支付后调用）
        
        Args:
            transaction_id: 交易ID（从create_payment返回）
            amount: 金额（必须与创建时一致）
            currency: 货币代码
        
        Returns:
            确认结果
        """
        if not self.is_enabled:
            return {
                "success": False,
                "error": "Line Pay客户端未初始化（缺少凭证）"
            }
        
        try:
            uri = f"/v3/payments/{transaction_id}/confirm"
            url = f"{self.base_url}{uri}"
            
            # TWD、JPY、THB 是零小数货币，必须使用整数
            currency_upper = currency.upper()
            zero_decimal_currencies = ["TWD", "JPY", "THB"]
            
            if currency_upper in zero_decimal_currencies:
                # 零小数货币：直接使用整数
                amount_value = int(float(amount))
            else:
                # 其他货币：使用浮点数
                amount_value = float(amount)
            
            data = {
                "amount": amount_value,
                "currency": currency_upper
            }
            
            body = json.dumps(data, separators=(',', ':'))
            headers = self._get_headers(uri, body)
            
            # 执行请求
            response = requests.post(url, headers=headers, data=body, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("returnCode") == "0000":
                    info = result.get("info", {})
                    
                    return {
                        "success": True,
                        "transaction_id": transaction_id,
                        "status": "success",
                        "paid": True,
                        "amount": str(info.get("payInfo", [{}])[0].get("amount", amount)),
                        "currency": currency.upper(),
                        "message": "支付确认成功"
                    }
                else:
                    error_msg = result.get("returnMessage", "确认支付失败")
                    logger.error(f"确认Line Pay支付失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"确认Line Pay支付失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"确认支付失败: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"确认Line Pay支付失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        查询Line Pay支付状态
        
        Args:
            transaction_id: 交易ID或订单号
        
        Returns:
            支付状态信息
        """
        if not self.is_enabled:
            return {
                "success": False,
                "error": "Line Pay客户端未初始化（缺少凭证）"
            }
        
        try:
            uri = f"/v3/payments/requests/{transaction_id}/check"
            url = f"{self.base_url}{uri}"
            
            # GET请求，body为空
            body = ""
            headers = self._get_headers(uri, body)
            
            # 执行请求
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("returnCode") == "0000":
                    info = result.get("info", {})
                    pay_status = info.get("payStatus")
                    
                    return {
                        "success": True,
                        "transaction_id": transaction_id,
                        "status": pay_status,
                        "paid": pay_status == "PAYMENT",
                        "amount": str(info.get("payInfo", [{}])[0].get("amount", "0")),
                        "currency": info.get("payInfo", [{}])[0].get("currency", "TWD"),
                        "message": f"订单状态: {pay_status}"
                    }
                else:
                    error_msg = result.get("returnMessage", "查询失败")
                    logger.error(f"查询Line Pay订单失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"查询Line Pay订单失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"查询订单失败: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"查询Line Pay订单失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def refund(
        self,
        transaction_id: str,
        refund_amount: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        退款
        
        Args:
            transaction_id: 原交易ID
            refund_amount: 退款金额（可选，不提供则全额退款）
        
        Returns:
            退款结果
        """
        if not self.is_enabled:
            return {
                "success": False,
                "error": "Line Pay客户端未初始化（缺少凭证）"
            }
        
        try:
            uri = f"/v3/payments/{transaction_id}/refund"
            url = f"{self.base_url}{uri}"
            
            data = {}
            if refund_amount:
                data["refundAmount"] = float(refund_amount)
            
            body = json.dumps(data, separators=(',', ':')) if data else ""
            headers = self._get_headers(uri, body)
            
            # 执行请求
            response = requests.post(url, headers=headers, data=body, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("returnCode") == "0000":
                    return {
                        "success": True,
                        "transaction_id": transaction_id,
                        "refund_amount": refund_amount or "full",
                        "message": "退款成功"
                    }
                else:
                    error_msg = result.get("returnMessage", "退款失败")
                    logger.error(f"Line Pay退款失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                logger.error(f"Line Pay退款失败: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"退款失败: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"Line Pay退款失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
