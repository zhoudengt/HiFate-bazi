#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一支付API接口
支持：Stripe、PayPal、支付宝国际版、微信支付、Line Pay
"""

import sys
import os
import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Literal
from enum import Enum

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services.payment_service.stripe_client import StripeClient
from services.payment_service.paypal_client import PayPalClient
from services.payment_service.alipay_client import AlipayClient
from services.payment_service.wechat_client import WeChatPayClient
from services.payment_service.linepay_client import LinePayClient

router = APIRouter()

# 初始化支付客户端
stripe_client = StripeClient()
paypal_client = PayPalClient()
alipay_client = AlipayClient()
wechat_client = WeChatPayClient()
linepay_client = LinePayClient()


class PaymentProvider(str, Enum):
    """支付渠道枚举"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    ALIPAY = "alipay"
    WECHAT = "wechat"
    LINEPAY = "linepay"


class CreatePaymentRequest(BaseModel):
    """创建支付请求"""
    provider: PaymentProvider = Field(..., description="支付渠道：stripe/paypal/alipay/wechat/linepay")
    amount: str = Field(..., description="金额，格式：19.90", example="19.90")
    currency: str = Field(default="USD", description="货币代码")
    product_name: str = Field(..., description="产品名称", example="月订阅会员")
    customer_email: Optional[EmailStr] = Field(None, description="客户邮箱（Stripe必需）")
    openid: Optional[str] = Field(None, description="微信用户openid（微信JSAPI支付必需）")
    payment_type: Optional[str] = Field("native", description="微信支付类型：native/jsapi")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="元数据")


class CreatePaymentResponse(BaseModel):
    """创建支付响应"""
    success: bool
    provider: str
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    checkout_url: Optional[str] = None
    approval_url: Optional[str] = None
    code_url: Optional[str] = None
    jsapi_params: Optional[Dict] = None
    status: Optional[str] = None
    message: Optional[str] = None


class VerifyPaymentRequest(BaseModel):
    """验证支付请求"""
    provider: PaymentProvider = Field(..., description="支付渠道")
    payment_id: Optional[str] = Field(None, description="支付ID（Stripe/PayPal）")
    order_id: Optional[str] = Field(None, description="订单号（支付宝/微信）")
    session_id: Optional[str] = Field(None, description="Stripe Session ID")
    transaction_id: Optional[str] = Field(None, description="交易ID（Line Pay使用）")


class VerifyPaymentResponse(BaseModel):
    """验证支付响应"""
    success: bool
    provider: str
    status: Optional[str] = None
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    customer_email: Optional[str] = None
    paid_time: Optional[str] = None
    message: Optional[str] = None


@router.post("/payment/unified/create", response_model=CreatePaymentResponse, summary="统一创建支付")
def create_unified_payment(request: CreatePaymentRequest):
    """
    统一支付接口 - 根据provider路由到不同支付渠道
    
    **支付渠道适用场景：**
    - **Stripe**: 全球通用，适合美洲、欧洲、香港、菲律宾等地区
    - **PayPal**: 全球认知度高，备选方案
    - **Alipay**: 支付宝国际版，适合中国客户
    - **WeChat**: 微信支付，适合中国客户
    - **Line Pay**: 适合台湾、日本、泰国等地区
    
    **货币代码：**
    - USD: 美元（Stripe, PayPal）
    - HKD: 港币（Stripe, PayPal, Alipay, WeChat）
    - CNY: 人民币（Alipay, WeChat）
    - EUR: 欧元（Stripe, PayPal）
    - PHP: 菲律宾比索（Stripe）
    - TWD: 台币（Line Pay，零小数货币，必须整数）
    - JPY: 日元（Line Pay，零小数货币，必须整数）
    - THB: 泰铢（Line Pay，零小数货币，必须整数）
    """
    try:
        provider = request.provider
        
        # Stripe支付
        if provider == PaymentProvider.STRIPE:
            if not request.customer_email:
                raise HTTPException(status_code=400, detail="Stripe支付需要提供customer_email")
            
            result = stripe_client.create_checkout_session(
                amount=request.amount,
                currency=request.currency,
                product_name=request.product_name,
                customer_email=request.customer_email,
                metadata=request.metadata
            )
            
            return CreatePaymentResponse(
                success=result.get('success', False),
                provider="stripe",
                payment_id=result.get('session_id'),
                checkout_url=result.get('checkout_url'),
                status=result.get('status'),
                message=result.get('message')
            )
        
        # PayPal支付
        elif provider == PaymentProvider.PAYPAL:
            result = paypal_client.create_payment(
                amount=request.amount,
                currency=request.currency,
                product_name=request.product_name,
                description=request.product_name
            )
            
            return CreatePaymentResponse(
                success=result.get('success', False),
                provider="paypal",
                payment_id=result.get('payment_id'),
                approval_url=result.get('approval_url'),
                status=result.get('status'),
                message=result.get('message') or result.get('error', 'PayPal支付处理完成')
            )
        
        # 支付宝支付
        elif provider == PaymentProvider.ALIPAY:
            # 生成订单号
            out_trade_no = f"ALIPAY_{int(time.time() * 1000)}"
            result = alipay_client.create_payment(
                out_trade_no=out_trade_no,
                amount=request.amount,
                subject=request.product_name
            )
            
            return CreatePaymentResponse(
                success=result.get('success', False),
                provider="alipay",
                order_id=result.get('out_trade_no'),
                payment_url=result.get('payment_url'),
                status=result.get('status'),
                message=result.get('message') or result.get('error', '支付宝支付处理完成')
            )
        
        # 微信支付
        elif provider == PaymentProvider.WECHAT:
            # Native支付（扫码）
            if request.payment_type == "native":
                result = wechat_client.create_native_order(
                    out_trade_no=f"WX_{int(time.time() * 1000)}",
                    amount=float(request.amount),
                    body=request.product_name
                )
                
                return CreatePaymentResponse(
                    success=result.get('success', False),
                    provider="wechat",
                    order_id=result.get('out_trade_no'),
                    code_url=result.get('code_url'),
                    status=result.get('status'),
                    message=result.get('message') or result.get('error', '微信支付处理完成')
                )
            
            # JSAPI支付（公众号/小程序）
            elif request.payment_type == "jsapi":
                if not request.openid:
                    raise HTTPException(status_code=400, detail="微信JSAPI支付需要提供openid")
                
                result = wechat_client.create_jsapi_order(
                    out_trade_no=f"WX_{int(time.time() * 1000)}",
                    amount=float(request.amount),
                    body=request.product_name,
                    openid=request.openid
                )
                
                return CreatePaymentResponse(
                    success=result.get('success', False),
                    provider="wechat",
                    order_id=result.get('out_trade_no'),
                    jsapi_params=result.get('jsapi_params'),
                    status=result.get('status'),
                    message=result.get('message') or result.get('error', '微信支付处理完成')
                )
            
            else:
                raise HTTPException(status_code=400, detail="不支持的微信支付类型")
        
        # Line Pay支付
        elif provider == PaymentProvider.LINEPAY:
            result = linepay_client.create_payment(
                amount=request.amount,
                currency=request.currency,
                product_name=request.product_name
            )
            
            # 确保 transaction_id 是字符串类型
            transaction_id = result.get('transaction_id')
            if transaction_id is not None:
                transaction_id = str(transaction_id)
            
            return CreatePaymentResponse(
                success=result.get('success', False),
                provider="linepay",
                transaction_id=transaction_id,
                order_id=result.get('order_id'),
                payment_url=result.get('payment_url'),
                status=result.get('status'),
                message=result.get('message') or result.get('error', 'Line Pay支付处理完成')
            )
        
        else:
            raise HTTPException(status_code=400, detail="不支持的支付渠道")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"支付创建失败: {str(e)}")


@router.post("/payment/unified/verify", response_model=VerifyPaymentResponse, summary="统一验证支付")
def verify_unified_payment(request: VerifyPaymentRequest):
    """
    统一验证支付状态
    
    根据不同支付渠道，使用对应的ID进行验证：
    - **Stripe**: session_id
    - **PayPal**: payment_id
    - **Alipay**: order_id
    - **WeChat**: order_id
    - **Line Pay**: transaction_id
    """
    try:
        provider = request.provider
        
        # Stripe验证
        if provider == PaymentProvider.STRIPE:
            if not request.session_id:
                raise HTTPException(status_code=400, detail="Stripe验证需要提供session_id")
            
            result = stripe_client.verify_payment(request.session_id)
            
            return VerifyPaymentResponse(
                success=result.get('success', False),
                provider="stripe",
                status=result.get('status'),
                payment_id=request.session_id,
                amount=result.get('amount'),
                currency=result.get('currency'),
                customer_email=result.get('customer_email'),
                paid_time=str(result.get('created_at')) if result.get('created_at') else None,
                message=result.get('message')
            )
        
        # PayPal验证
        elif provider == PaymentProvider.PAYPAL:
            if not request.payment_id:
                raise HTTPException(status_code=400, detail="PayPal验证需要提供payment_id")
            
            result = paypal_client.verify_payment(request.payment_id)
            
            return VerifyPaymentResponse(
                success=result.get('success', False),
                provider="paypal",
                status=result.get('status'),
                payment_id=request.payment_id,
                amount=result.get('amount'),
                currency=result.get('currency'),
                customer_email=result.get('payer_email'),
                paid_time=result.get('update_time'),
                message=result.get('message', '验证成功')
            )
        
        # 支付宝验证
        elif provider == PaymentProvider.ALIPAY:
            if not request.order_id:
                raise HTTPException(status_code=400, detail="支付宝验证需要提供order_id")
            
            result = alipay_client.verify_payment(request.order_id)
            
            return VerifyPaymentResponse(
                success=result.get('success', False),
                provider="alipay",
                status=result.get('status'),
                order_id=request.order_id,
                amount=result.get('amount'),
                paid_time=result.get('paid_time'),
                message=result.get('message')
            )
        
        # 微信验证
        elif provider == PaymentProvider.WECHAT:
            if not request.order_id:
                raise HTTPException(status_code=400, detail="微信支付验证需要提供order_id")
            
            result = wechat_client.verify_payment(request.order_id)
            
            return VerifyPaymentResponse(
                success=result.get('success', False),
                provider="wechat",
                status=result.get('status'),
                order_id=request.order_id,
                amount=result.get('amount'),
                paid_time=result.get('paid_time'),
                message=result.get('message')
            )
        
        # Line Pay验证
        elif provider == PaymentProvider.LINEPAY:
            if not request.transaction_id:
                raise HTTPException(status_code=400, detail="Line Pay验证需要提供transaction_id")
            
            result = linepay_client.query_payment_status(request.transaction_id)
            
            # 确保 transaction_id 是字符串类型
            transaction_id = result.get('transaction_id')
            if transaction_id is not None:
                transaction_id = str(transaction_id)
            
            return VerifyPaymentResponse(
                success=result.get('success', False),
                provider="linepay",
                status=result.get('status'),
                payment_id=transaction_id,
                amount=result.get('amount'),
                currency=result.get('currency'),
                message=result.get('message')
            )
        
        else:
            raise HTTPException(status_code=400, detail="不支持的支付渠道")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"支付验证失败: {str(e)}")


@router.get("/payment/providers", summary="获取可用支付渠道")
def get_payment_providers():
    """
    获取所有可用的支付渠道及其状态
    
    返回各支付渠道的配置状态和适用地区
    """
    return {
        "success": True,
        "providers": [
            {
                "id": "stripe",
                "name": "Stripe",
                "enabled": bool(stripe_client.api_key),
                "regions": ["美洲", "欧洲", "香港", "菲律宾", "全球"],
                "currencies": ["USD", "EUR", "HKD", "PHP", "GBP", "AUD"],
                "description": "全球领先的在线支付平台"
            },
            {
                "id": "paypal",
                "name": "PayPal",
                "enabled": paypal_client.is_enabled,
                "regions": ["全球"],
                "currencies": ["USD", "EUR", "HKD", "GBP", "AUD"],
                "description": "全球认知度最高的支付平台"
            },
            {
                "id": "alipay",
                "name": "支付宝国际版",
                "enabled": bool(alipay_client.client),
                "regions": ["中国", "香港", "澳门"],
                "currencies": ["CNY", "HKD", "USD"],
                "description": "中国用户首选支付方式"
            },
            {
                "id": "wechat",
                "name": "微信支付",
                "enabled": bool(wechat_client.client),
                "regions": ["中国", "香港", "澳门"],
                "currencies": ["CNY", "HKD"],
                "description": "中国用户常用支付方式"
            },
            {
                "id": "linepay",
                "name": "Line Pay",
                "enabled": linepay_client.is_enabled,
                "regions": ["台湾", "日本", "泰国"],
                "currencies": ["TWD", "JPY", "THB", "USD"],
                "description": "台湾、日本、泰国地区常用支付方式"
            }
        ]
    }


@router.get("/payment/recommend", summary="推荐支付渠道")
def recommend_payment_provider(
    region: str = "global",
    currency: str = "USD"
):
    """
    根据地区和货币推荐最合适的支付渠道
    
    **地区参数：**
    - global: 全球
    - americas: 美洲
    - europe: 欧洲
    - hongkong: 香港
    - philippines: 菲律宾
    - china: 中国大陆
    """
    recommendations = []
    
    # 地区推荐逻辑
    if region in ["americas", "europe", "philippines"]:
        recommendations = ["stripe", "paypal"]
    elif region == "hongkong":
        recommendations = ["stripe", "alipay", "wechat", "paypal"]
    elif region == "china":
        recommendations = ["alipay", "wechat", "stripe"]
    elif region in ["taiwan", "japan", "thailand"]:
        recommendations = ["linepay", "stripe", "paypal"]
    else:  # global
        recommendations = ["stripe", "paypal", "alipay", "wechat", "linepay"]
    
    # 根据货币调整
    if currency == "CNY":
        recommendations = ["alipay", "wechat"] + [p for p in recommendations if p not in ["alipay", "wechat"]]
    elif currency in ["TWD", "JPY", "THB"]:
        recommendations = ["linepay"] + [p for p in recommendations if p != "linepay"]
    
    return {
        "success": True,
        "region": region,
        "currency": currency,
        "recommended": recommendations,
        "primary": recommendations[0] if recommendations else "stripe"
    }

