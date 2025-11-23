#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PayPal支付客户端封装
支持PayPal Checkout支付功能
"""

import os
import logging
from typing import Optional, Dict, Any

try:
    from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment
    from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest, OrdersGetRequest
except ImportError:
    PayPalHttpClient = None
    logging.warning("paypalcheckoutsdk库未安装，请运行: pip install paypalcheckoutsdk")

logger = logging.getLogger(__name__)


class PayPalClient:
    """PayPal支付客户端"""
    
    def __init__(self):
        """初始化PayPal客户端"""
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        self.mode = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox or live
        
        if not self.client_id:
            logger.warning("PAYPAL_CLIENT_ID环境变量未设置")
        
        if not PayPalHttpClient:
            logger.error("paypalcheckoutsdk库未安装")
            self.client = None
            return
        
        try:
            # 选择环境
            if self.mode == "live":
                environment = LiveEnvironment(
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            else:
                environment = SandboxEnvironment(
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            
            self.client = PayPalHttpClient(environment)
        except Exception as e:
            logger.error(f"初始化PayPal客户端失败: {e}")
            self.client = None
    
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
        if not self.client:
            return {
                "success": False,
                "error": "PayPal客户端未初始化"
            }
        
        try:
            # 设置默认URL
            if not return_url:
                frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
                return_url = f"{frontend_base}/frontend/payment-success.html?provider=paypal"
            
            if not cancel_url:
                frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
                cancel_url = f"{frontend_base}/frontend/payment-cancel.html?provider=paypal"
            
            # 创建订单请求
            request = OrdersCreateRequest()
            request.prefer('return=representation')
            request.request_body({
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
            })
            
            # 执行请求
            response = self.client.execute(request)
            
            if response.status_code in [200, 201]:
                order_id = response.result.id
                
                # 获取approval_url
                approval_url = None
                for link in response.result.links:
                    if link.rel == "approve":
                        approval_url = link.href
                        break
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "approval_url": approval_url,
                    "status": response.result.status,
                    "message": "PayPal订单创建成功"
                }
            else:
                return {
                    "success": False,
                    "error": "创建订单失败"
                }
        
        except Exception as e:
            logger.error(f"创建PayPal订单失败: {e}")
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
        if not self.client:
            return {
                "success": False,
                "error": "PayPal客户端未初始化"
            }
        
        try:
            request = OrdersCaptureRequest(order_id)
            response = self.client.execute(request)
            
            if response.status_code in [200, 201]:
                result = response.result
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "status": result.status,
                    "paid": result.status == "COMPLETED",
                    "payer_email": result.payer.email_address if hasattr(result.payer, 'email_address') else None,
                    "amount": result.purchase_units[0].amount.value,
                    "currency": result.purchase_units[0].amount.currency_code,
                    "message": "订单已完成"
                }
            else:
                return {
                    "success": False,
                    "error": "捕获订单失败"
                }
        
        except Exception as e:
            logger.error(f"捕获PayPal订单失败: {e}")
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
        if not self.client:
            return {
                "success": False,
                "error": "PayPal客户端未初始化"
            }
        
        try:
            request = OrdersGetRequest(order_id)
            response = self.client.execute(request)
            
            if response.status_code == 200:
                result = response.result
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "status": result.status,
                    "paid": result.status == "COMPLETED",
                    "amount": result.purchase_units[0].amount.value,
                    "currency": result.purchase_units[0].amount.currency_code,
                    "message": f"订单状态: {result.status}"
                }
            else:
                return {
                    "success": False,
                    "error": "查询订单失败"
                }
        
        except Exception as e:
            logger.error(f"查询PayPal订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
