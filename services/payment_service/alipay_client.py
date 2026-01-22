#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付宝国际版客户端封装
支持支付宝国际版支付功能
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from alipay import AliPay
    from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
    from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest
    from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
    from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel
except ImportError:
    AliPay = None
    logging.warning("alipay-sdk-python库未安装，请运行: pip install alipay-sdk-python")

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


class AlipayClient:
    """支付宝国际版客户端"""
    
    def __init__(self, environment: Optional[str] = None):
        """
        初始化支付宝客户端
        
        Args:
            environment: 环境（production/sandbox），如果为None则自动查找is_active=1的记录
        """
        self.environment = environment
        
        # 从数据库读取配置，自动查找is_active=1的记录
        # 如果指定了environment，则优先匹配该环境且is_active=1的记录
        self.app_id = get_payment_config('alipay', 'app_id', environment) or os.getenv("ALIPAY_APP_ID")
        self.private_key_path = get_payment_config('alipay', 'private_key_path', environment) or os.getenv("ALIPAY_PRIVATE_KEY_PATH")
        self.alipay_public_key_path = get_payment_config('alipay', 'public_key_path', environment) or os.getenv("ALIPAY_PUBLIC_KEY_PATH")
        gateway_from_db = get_payment_config('alipay', 'gateway', environment)
        self.gateway = gateway_from_db or os.getenv("ALIPAY_GATEWAY", "https://openapi.alipay.com/gateway.do")
        
        if not self.app_id:
            logger.warning("支付宝APP ID未配置（数据库或环境变量）")
        
        if not AliPay:
            logger.error("alipay-sdk-python库未安装")
            self.client = None
            return
        
        # 读取私钥
        try:
            if self.private_key_path and os.path.exists(self.private_key_path):
                with open(self.private_key_path, 'r') as f:
                    app_private_key = f.read()
            else:
                logger.warning("支付宝私钥路径未配置或文件不存在")
                app_private_key = ""
        except Exception as e:
            logger.error(f"读取支付宝私钥失败: {e}")
            app_private_key = ""
        
        # 读取支付宝公钥
        try:
            if self.alipay_public_key_path and os.path.exists(self.alipay_public_key_path):
                with open(self.alipay_public_key_path, 'r') as f:
                    alipay_public_key = f.read()
            else:
                logger.warning("支付宝公钥路径未配置或文件不存在")
                alipay_public_key = ""
        except Exception as e:
            logger.error(f"读取支付宝公钥失败: {e}")
            alipay_public_key = ""
        
        # 初始化SDK
        try:
            self.client = AliPay(
                appid=self.app_id,
                app_notify_url=None,  # 默认回调地址
                app_private_key_string=app_private_key,
                alipay_public_key_string=alipay_public_key,
                sign_type="RSA2",
                debug=os.getenv("ALIPAY_DEBUG", "false").lower() == "true"
            )
        except Exception as e:
            logger.error(f"初始化支付宝客户端失败: {e}")
            self.client = None
    
    def create_payment(
        self,
        out_trade_no: str,
        amount: str,
        subject: str,
        body: Optional[str] = None,
        return_url: Optional[str] = None,
        notify_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建支付宝支付订单（网页支付）
        
        Args:
            out_trade_no: 商户订单号（唯一）
            amount: 金额（字符串，如"19.90"）
            subject: 订单标题
            body: 订单描述（可选）
            return_url: 支付成功后跳转URL
            notify_url: 异步通知URL
        
        Returns:
            包含payment_url的字典
        """
        # 如果初始化时没有配置，尝试重新加载（支持热更新）
        if not self.client:
            # 重新加载配置
            self.app_id = get_payment_config('alipay', 'app_id', self.environment) or os.getenv("ALIPAY_APP_ID")
            self.private_key_path = get_payment_config('alipay', 'private_key_path', self.environment) or os.getenv("ALIPAY_PRIVATE_KEY_PATH")
            self.alipay_public_key_path = get_payment_config('alipay', 'public_key_path', self.environment) or os.getenv("ALIPAY_PUBLIC_KEY_PATH")
            
            # 重新初始化客户端
            if self.app_id and self.private_key_path and self.alipay_public_key_path and AliPay:
                try:
                    with open(self.private_key_path, 'r') as f:
                        app_private_key = f.read()
                    with open(self.alipay_public_key_path, 'r') as f:
                        alipay_public_key = f.read()
                    self.client = AliPay(
                        appid=self.app_id,
                        app_notify_url=None,
                        app_private_key_string=app_private_key,
                        alipay_public_key_string=alipay_public_key,
                        sign_type="RSA2",
                        debug=os.getenv("ALIPAY_DEBUG", "false").lower() == "true"
                    )
                except Exception as e:
                    logger.error(f"重新初始化支付宝客户端失败: {e}")
        
        if not self.client:
            return {
                "success": False,
                "error": "支付宝客户端未初始化"
            }
        
        try:
            # 设置默认URL
            # 从数据库读取URL，如果数据库中没有则降级到环境变量
            frontend_base = get_payment_config('shared', 'frontend_base_url') or os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
            api_base = get_payment_config('shared', 'api_base_url') or os.getenv("API_BASE_URL", "http://localhost:8001")
            
            if not return_url:
                return_url = f"{frontend_base}/frontend/payment-success.html?provider=alipay"
            
            if not notify_url:
                notify_url = f"{api_base}/api/v1/payment/webhook/alipay"
            
            # 构建订单参数
            order_string = self.client.api_alipay_trade_page_pay(
                out_trade_no=out_trade_no,
                total_amount=amount,
                subject=subject,
                body=body or subject,
                return_url=return_url,
                notify_url=notify_url
            )
            
            # 拼接支付URL
            payment_url = f"{self.gateway}?{order_string}"
            
            return {
                "success": True,
                "out_trade_no": out_trade_no,
                "payment_url": payment_url,
                "status": "created",
                "message": "支付宝订单创建成功"
            }
        
        except Exception as e:
            logger.error(f"创建支付宝订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_payment(self, out_trade_no: str) -> Dict[str, Any]:
        """
        查询支付状态
        
        Args:
            out_trade_no: 商户订单号
        
        Returns:
            支付状态信息
        """
        if not self.client:
            return {
                "success": False,
                "error": "支付宝客户端未初始化"
            }
        
        try:
            # 查询订单
            result = self.client.api_alipay_trade_query(
                out_trade_no=out_trade_no
            )
            
            if result.get("code") == "10000":
                trade_status = result.get("trade_status")
                
                return {
                    "success": True,
                    "out_trade_no": out_trade_no,
                    "trade_no": result.get("trade_no"),  # 支付宝交易号
                    "status": trade_status,
                    "paid": trade_status == "TRADE_SUCCESS",
                    "amount": result.get("total_amount"),
                    "buyer_email": result.get("buyer_logon_id"),
                    "message": f"订单状态: {trade_status}"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "查询失败")
                }
        
        except Exception as e:
            logger.error(f"查询支付宝订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_notify(self, data: Dict) -> bool:
        """
        验证异步通知签名
        
        Args:
            data: 支付宝POST的通知数据
        
        Returns:
            签名是否有效
        """
        if not self.client:
            return False
        
        try:
            signature = data.pop("sign", None)
            sign_type = data.pop("sign_type", None)
            
            # 验证签名
            return self.client.verify(data, signature)
        except Exception as e:
            logger.error(f"验证支付宝签名失败: {e}")
            return False
    
    def refund(
        self,
        out_trade_no: str,
        refund_amount: str,
        refund_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        退款
        
        Args:
            out_trade_no: 商户订单号
            refund_amount: 退款金额
            refund_reason: 退款原因
        
        Returns:
            退款结果
        """
        if not self.client:
            return {
                "success": False,
                "error": "支付宝客户端未初始化"
            }
        
        try:
            result = self.client.api_alipay_trade_refund(
                out_trade_no=out_trade_no,
                refund_amount=refund_amount,
                refund_reason=refund_reason or "用户退款"
            )
            
            if result.get("code") == "10000":
                return {
                    "success": True,
                    "out_trade_no": out_trade_no,
                    "trade_no": result.get("trade_no"),
                    "refund_amount": result.get("refund_fee"),
                    "message": "退款成功"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "退款失败")
                }
        
        except Exception as e:
            logger.error(f"支付宝退款失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
