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

logger = logging.getLogger(__name__)


class PayPalClient:
    """PayPal支付客户端"""
    
    def __init__(self):
        """初始化PayPal客户端"""
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        self.mode = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox or live
        
        # 设置API基础URL
        if self.mode == "live":
            self.base_url = "https://api.paypal.com"
        else:
            self.base_url = "https://api.sandbox.paypal.com"
        
        if not self.client_id or not self.client_secret:
            logger.warning("PAYPAL_CLIENT_ID 或 PAYPAL_CLIENT_SECRET 环境变量未设置")
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
        cancel_url: Optional[str] = None
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
            cancel_url=cancel_url
        )
        
        # 转换字段名：order_id -> payment_id
        if result.get("success") and "order_id" in result:
            result["payment_id"] = result.pop("order_id")
        
        return result
    
    def create_order(
        self,
        amount: str,
        currency: str = "USD",
        description: str = "Purchase",
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建PayPal订单
        
        Args:
            amount: 金额（字符串，如"19.90"）
            currency: 货币代码（USD, EUR, GBP等）
            description: 订单描述
            return_url: 支付成功后跳转URL
            cancel_url: 取消支付跳转URL
        
        Returns:
            包含order_id和approval_url的字典
        """
        if not self.access_token:
            return {
                "success": False,
                "error": "PayPal客户端未初始化（无法获取访问令牌）"
            }
        
        try:
            # 设置默认URL
            if not return_url:
                frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
                return_url = f"{frontend_base}/frontend/payment-success.html?provider=paypal"
            
            if not cancel_url:
                frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
                cancel_url = f"{frontend_base}/frontend/payment-cancel.html?provider=paypal"
            
            # 构建请求数据
            url = f"{self.base_url}/v2/checkout/orders"
            headers = self._get_headers()
            data = {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": currency,
                        "value": amount
                    },
                    "description": description
                }],
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
                order_id = result.get("id")
                
                # 获取approval_url
                approval_url = None
                links = result.get("links", [])
                for link in links:
                    if link.get("rel") == "approve":
                        approval_url = link.get("href")
                        break
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "approval_url": approval_url,
                    "status": result.get("status"),
                    "message": "PayPal订单创建成功"
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
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "status": status,
                    "paid": status == "COMPLETED",
                    "payer_email": payer_email,
                    "amount": amount_info,
                    "currency": currency_info,
                    "message": "订单已完成"
                }
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
