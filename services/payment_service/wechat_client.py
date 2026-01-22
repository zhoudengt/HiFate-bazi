#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信支付客户端封装
支持微信支付Native、JSAPI等支付方式
"""

import os
import logging
import time
from typing import Optional, Dict, Any
import xml.etree.ElementTree as ET

try:
    from wechatpy.pay import WeChatPay
    from wechatpy.pay.utils import calculate_signature, WeChatSigner
except ImportError:
    WeChatPay = None
    logging.warning("wechatpy库未安装，请运行: pip install wechatpy")

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


class WeChatPayClient:
    """微信支付客户端"""
    
    def __init__(self, environment: Optional[str] = None):
        """
        初始化微信支付客户端
        
        Args:
            environment: 环境（production/sandbox），如果为None则自动查找is_active=1的记录
        """
        self.environment = environment
        
        # 从数据库读取配置，自动查找is_active=1的记录
        # 如果指定了environment，则优先匹配该环境且is_active=1的记录
        self.app_id = get_payment_config('wechat', 'app_id', environment) or os.getenv("WECHAT_APP_ID")
        self.mch_id = get_payment_config('wechat', 'mch_id', environment) or os.getenv("WECHAT_MCH_ID")
        self.api_key = get_payment_config('wechat', 'api_key', environment) or os.getenv("WECHAT_API_KEY")
        self.cert_path = get_payment_config('wechat', 'cert_path', environment) or os.getenv("WECHAT_CERT_PATH")
        self.key_path = get_payment_config('wechat', 'key_path', environment) or os.getenv("WECHAT_KEY_PATH")
        
        if not self.app_id:
            logger.warning("微信支付APP ID未配置（数据库或环境变量）")
        
        if not WeChatPay:
            logger.error("wechatpy库未安装")
            self.client = None
            return
        
        try:
            self.client = WeChatPay(
                appid=self.app_id,
                api_key=self.api_key,
                mch_id=self.mch_id,
                mch_cert=self.cert_path if self.cert_path and os.path.exists(self.cert_path) else None,
                mch_key=self.key_path if self.key_path and os.path.exists(self.key_path) else None
            )
        except Exception as e:
            logger.error(f"初始化微信支付客户端失败: {e}")
            self.client = None
    
    def create_native_order(
        self,
        out_trade_no: str,
        amount: float,
        body: str,
        notify_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建Native扫码支付订单
        
        Args:
            out_trade_no: 商户订单号（唯一）
            amount: 金额（元）
            body: 商品描述
            notify_url: 异步通知URL
        
        Returns:
            包含code_url（二维码链接）的字典
        """
        # 如果初始化时没有配置，尝试重新加载（支持热更新）
        if not self.client:
            # 重新加载配置
            self.app_id = get_payment_config('wechat', 'app_id', self.environment) or os.getenv("WECHAT_APP_ID")
            self.mch_id = get_payment_config('wechat', 'mch_id', self.environment) or os.getenv("WECHAT_MCH_ID")
            self.api_key = get_payment_config('wechat', 'api_key', self.environment) or os.getenv("WECHAT_API_KEY")
            self.cert_path = get_payment_config('wechat', 'cert_path', self.environment) or os.getenv("WECHAT_CERT_PATH")
            self.key_path = get_payment_config('wechat', 'key_path', self.environment) or os.getenv("WECHAT_KEY_PATH")
            
            # 重新初始化客户端
            if self.app_id and self.mch_id and self.api_key and WeChatPay:
                try:
                    self.client = WeChatPay(
                        appid=self.app_id,
                        api_key=self.api_key,
                        mch_id=self.mch_id,
                        mch_cert=self.cert_path if self.cert_path and os.path.exists(self.cert_path) else None,
                        mch_key=self.key_path if self.key_path and os.path.exists(self.key_path) else None
                    )
                except Exception as e:
                    logger.error(f"重新初始化微信支付客户端失败: {e}")
        
        if not self.client:
            return {
                "success": False,
                "error": "微信支付客户端未初始化"
            }
        
        try:
            # 设置默认通知URL
            # 从数据库读取URL，如果数据库中没有则降级到环境变量
            api_base = get_payment_config('shared', 'api_base_url') or os.getenv("API_BASE_URL", "http://localhost:8001")
            
            if not notify_url:
                notify_url = f"{api_base}/api/v1/payment/webhook/wechat"
            
            # 金额转为分
            total_fee = int(float(amount) * 100)
            
            # 创建订单
            result = self.client.order.create(
                trade_type='NATIVE',  # Native扫码支付
                body=body,
                out_trade_no=out_trade_no,
                total_fee=total_fee,
                notify_url=notify_url,
                user_ip='127.0.0.1'  # 可以从请求中获取真实IP
            )
            
            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                return {
                    "success": True,
                    "out_trade_no": out_trade_no,
                    "code_url": result.get("code_url"),  # 二维码链接
                    "status": "created",
                    "message": "微信支付订单创建成功"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("err_code_des", "创建订单失败")
                }
        
        except Exception as e:
            logger.error(f"创建微信支付订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_jsapi_order(
        self,
        out_trade_no: str,
        amount: float,
        body: str,
        openid: str,
        notify_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建JSAPI支付订单（小程序/公众号）
        
        Args:
            out_trade_no: 商户订单号
            amount: 金额（元）
            body: 商品描述
            openid: 用户openid
            notify_url: 异步通知URL
        
        Returns:
            包含prepay_id的字典
        """
        if not self.client:
            return {
                "success": False,
                "error": "微信支付客户端未初始化"
            }
        
        try:
            if not notify_url:
                api_base = os.getenv("API_BASE_URL", "http://localhost:8001")
                notify_url = f"{api_base}/api/v1/payment/webhook/wechat"
            
            # 金额转为分
            total_fee = int(float(amount) * 100)
            
            # 创建订单
            result = self.client.order.create(
                trade_type='JSAPI',
                body=body,
                out_trade_no=out_trade_no,
                total_fee=total_fee,
                notify_url=notify_url,
                user_ip='127.0.0.1',
                openid=openid
            )
            
            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                return {
                    "success": True,
                    "out_trade_no": out_trade_no,
                    "prepay_id": result.get("prepay_id"),
                    "status": "created",
                    "message": "微信支付订单创建成功"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("err_code_des", "创建订单失败")
                }
        
        except Exception as e:
            logger.error(f"创建微信JSAPI订单失败: {e}")
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
                "error": "微信支付客户端未初始化"
            }
        
        try:
            result = self.client.order.query(out_trade_no=out_trade_no)
            
            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                trade_state = result.get("trade_state")
                
                return {
                    "success": True,
                    "out_trade_no": out_trade_no,
                    "transaction_id": result.get("transaction_id"),  # 微信支付订单号
                    "status": trade_state,
                    "paid": trade_state == "SUCCESS",
                    "amount": str(float(result.get("total_fee", 0)) / 100),  # 分转元
                    "openid": result.get("openid"),
                    "message": f"订单状态: {trade_state}"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("err_code_des", "查询失败")
                }
        
        except Exception as e:
            logger.error(f"查询微信支付订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_notify(self, xml_data: str) -> tuple[bool, Optional[Dict]]:
        """
        验证异步通知签名
        
        Args:
            xml_data: 微信POST的XML数据
        
        Returns:
            (签名是否有效, 解析后的数据)
        """
        if not self.client:
            return False, None
        
        try:
            # 解析XML
            root = ET.fromstring(xml_data)
            data = {child.tag: child.text for child in root}
            
            # 验证签名
            sign = data.pop("sign", None)
            calculated_sign = calculate_signature(data, self.api_key)
            
            if sign == calculated_sign:
                return True, data
            else:
                logger.warning("微信支付签名验证失败")
                return False, None
        
        except Exception as e:
            logger.error(f"验证微信支付签名失败: {e}")
            return False, None
    
    def close_order(self, out_trade_no: str) -> Dict[str, Any]:
        """
        关闭订单
        
        Args:
            out_trade_no: 商户订单号
        
        Returns:
            关闭结果
        """
        if not self.client:
            return {
                "success": False,
                "error": "微信支付客户端未初始化"
            }
        
        try:
            result = self.client.order.close(out_trade_no=out_trade_no)
            
            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                return {
                    "success": True,
                    "message": "订单已关闭"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("err_code_des", "关闭订单失败")
                }
        
        except Exception as e:
            logger.error(f"关闭微信支付订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def refund(
        self,
        out_trade_no: str,
        out_refund_no: str,
        total_fee: float,
        refund_fee: float,
        refund_desc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        退款
        
        Args:
            out_trade_no: 商户订单号
            out_refund_no: 商户退款单号
            total_fee: 订单总金额（元）
            refund_fee: 退款金额（元）
            refund_desc: 退款原因
        
        Returns:
            退款结果
        """
        if not self.client:
            return {
                "success": False,
                "error": "微信支付客户端未初始化"
            }
        
        try:
            # 金额转为分
            total_fee_fen = int(float(total_fee) * 100)
            refund_fee_fen = int(float(refund_fee) * 100)
            
            result = self.client.refund.apply(
                out_trade_no=out_trade_no,
                out_refund_no=out_refund_no,
                total_fee=total_fee_fen,
                refund_fee=refund_fee_fen,
                refund_desc=refund_desc or "用户退款"
            )
            
            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                return {
                    "success": True,
                    "out_trade_no": out_trade_no,
                    "out_refund_no": out_refund_no,
                    "refund_id": result.get("refund_id"),
                    "refund_fee": str(float(result.get("refund_fee", 0)) / 100),
                    "message": "退款成功"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("err_code_des", "退款失败")
                }
        
        except Exception as e:
            logger.error(f"微信支付退款失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
