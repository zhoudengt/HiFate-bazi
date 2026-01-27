#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一支付API接口
支持：Stripe、PayPal、支付宝国际版、微信支付、Line Pay
"""

import sys
import os
import time
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Literal
from enum import Enum

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入新的插件化支付客户端
from services.payment_service.client_factory import get_payment_client, payment_client_factory

# 导入支付服务模块（触发客户端注册）
import services.payment_service

# 导入区域配置和白名单管理
try:
    from services.payment_service.payment_region_config_manager import get_region_config_manager
    from services.payment_service.payment_whitelist_manager import get_whitelist_manager
    from services.payment_service.currency_converter import CurrencyConverter
except ImportError as e:
    logger.warning(f"导入区域配置和白名单管理模块失败: {e}")
    get_region_config_manager = None
    get_whitelist_manager = None
    CurrencyConverter = None

# 导入支付交易 DAO（用于过期检查）
try:
    from server.db.payment_transaction_dao import PaymentTransactionDAO
except ImportError as e:
    logger.warning(f"导入支付交易DAO失败: {e}")
    PaymentTransactionDAO = None

router = APIRouter()

# 支付客户端通过工厂模式动态获取，无需预初始化


class PaymentProvider(str, Enum):
    """支付渠道枚举"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    ALIPAY = "alipay"
    WECHAT = "wechat"
    LINEPAY = "linepay"
    PAYSSION = "payssion"
    PAYERMAX = "payermax"


class CreatePaymentRequest(BaseModel):
    """创建支付请求"""
    provider: PaymentProvider = Field(..., description="支付渠道：stripe/paypal/alipay/wechat/linepay/payssion/payermax")
    amount: str = Field(..., description="金额，格式：19.90", example="19.90")
    currency: str = Field(default="USD", description="货币代码")
    product_name: str = Field(..., description="产品名称", example="月订阅会员")
    customer_email: Optional[EmailStr] = Field(None, description="客户邮箱（Stripe必需）")
    openid: Optional[str] = Field(None, description="微信用户openid（微信JSAPI支付必需）")
    payment_type: Optional[str] = Field("native", description="微信支付类型：native/jsapi")
    payment_method: Optional[str] = Field(None, description="具体支付方式（如linepay用于Payssion，card用于PayerMax）")
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
    expires_at: Optional[str] = None  # 订单过期时间（ISO 8601格式）
    created_at: Optional[str] = None  # 订单创建时间（ISO 8601格式）


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
def create_unified_payment(request: CreatePaymentRequest, http_request: Request):
    """
    统一支付接口 - 基于插件化架构，支持快速扩展

    **支持的支付渠道：**
    - **Stripe**: 全球通用，适合美洲、欧洲、香港、菲律宾等地区
    - **PayPal**: 全球认知度高，备选方案
    - **Payssion**: LINE Pay 中转，适合台湾地区
    - **PayerMax**: 全球多支付方式聚合
    - **Alipay**: 支付宝国际版，适合中国客户
    - **WeChat**: 微信支付，适合中国客户
    - **Line Pay**: 直接集成，适合台湾、日本、泰国等地区

    **货币代码：**
    - USD: 美元（Stripe, PayPal, Payssion, PayerMax）
    - HKD: 港币（Stripe, PayPal, Alipay, WeChat, PayerMax）
    - CNY: 人民币（Alipay, WeChat, PayerMax）
    - EUR: 欧元（Stripe, PayPal, PayerMax）
    - PHP: 菲律宾比索（Stripe, PayerMax）
    - TWD: 台币（Line Pay, Payssion，零小数货币，必须整数）
    - JPY: 日元（Line Pay, Payssion，零小数货币，必须整数）
    - THB: 泰铢（Line Pay, Payssion，零小数货币，必须整数）

    **区域限制：**
    - 系统会根据用户所在区域检查是否开放支付
    - 如果区域关闭，只有白名单用户可以使用支付功能
    """
    try:
        provider = request.provider
        # 确保 provider 是字符串（如果是枚举，转换为值）
        provider_str = provider.value if hasattr(provider, 'value') else str(provider)

        # 获取支付客户端（如果失败，尝试重新加载模块）
        try:
            payment_client = get_payment_client(provider_str)
        except ValueError as e:
            # 如果客户端未注册，尝试重新加载支付服务模块
            if "不支持的支付平台" in str(e):
                try:
                    import importlib
                    import sys
                    if 'services.payment_service' in sys.modules:
                        importlib.reload(sys.modules['services.payment_service'])
                    # 再次尝试获取客户端
                    payment_client = get_payment_client(provider_str)
                except Exception as reload_error:
                    logger.warning(f"重新加载支付服务模块失败: {reload_error}")
                    raise HTTPException(status_code=400, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))

        # 检查支付客户端是否启用
        if not payment_client.is_enabled:
            raise HTTPException(status_code=400, detail=f"支付渠道 {provider_str} 未启用，请检查配置")

        # 生成订单号
        import time
        order_id = f"{provider_str.upper()}_{int(time.time() * 1000)}"

        # 区域检查和白名单检查（临时跳过，等正式支付时再启用）
        # TODO: 正式支付时启用区域检查
        SKIP_REGION_CHECK = os.getenv("SKIP_PAYMENT_REGION_CHECK", "true").lower() == "true"
        
        user_region = None
        region_open = True
        is_whitelisted = False

        if not SKIP_REGION_CHECK and get_region_config_manager and get_whitelist_manager:
            region_manager = get_region_config_manager()
            whitelist_manager = get_whitelist_manager()

            # 检测用户所在区域
            client_ip = None
            if http_request and hasattr(http_request, 'client') and http_request.client:
                client_ip = http_request.client.host

            user_region = region_manager.detect_user_region(
                ip=client_ip,
                email=request.customer_email,
                phone=None,  # 可以从 request 中获取，如果有 phone 字段
                user_id=None  # 可以从 request 中获取，如果有 user_id 字段
            )

            # 检查区域是否开放
            region_open = region_manager.is_region_open(user_region)

            # 如果区域关闭，检查白名单
            if not region_open:
                is_whitelisted = whitelist_manager.is_whitelisted(
                    user_id=None,  # 可以从 request 中获取
                    email=request.customer_email
                )

                if not is_whitelisted:
                    raise HTTPException(
                        status_code=403,
                        detail=f"区域 {user_region} 暂不支持支付，请联系客服或申请白名单"
                    )

        # 记录区域和白名单信息到 metadata
        if not request.metadata:
            request.metadata = {}
        request.metadata["user_region"] = user_region or "UNKNOWN"
        request.metadata["region_open"] = str(region_open)
        request.metadata["is_whitelisted"] = str(is_whitelisted)
        request.metadata["order_id"] = order_id

        # 构建支付参数
        payment_params = {
            "amount": request.amount,
            "currency": request.currency,
            "product_name": request.product_name,
            "order_id": order_id,
            "customer_email": request.customer_email,
            "metadata": request.metadata,
        }

        # 根据支付平台添加特定参数
        if provider_str == "stripe":
            if not request.customer_email:
                raise HTTPException(status_code=400, detail="Stripe支付需要提供customer_email")
            payment_params.update({
                "enable_adaptive_pricing": True,
                "enable_link": True,
            })
        elif provider_str == "payssion":
            payment_params["payment_method"] = request.payment_method or "linepay"
        elif provider_str == "payermax":
            payment_params["payment_method"] = request.payment_method
        elif provider_str == "wechat":
            if request.payment_type == "jsapi" and not request.openid:
                raise HTTPException(status_code=400, detail="微信JSAPI支付需要提供openid")
            payment_params.update({
                "payment_type": request.payment_type,
                "openid": request.openid,
            })

        # 调用支付客户端创建支付
        result = payment_client.create_payment(**payment_params)

        if not result.get('success', False):
            raise HTTPException(
                status_code=400,
                detail=result.get('error', f'{provider_str} 支付创建失败')
            )

        # 计算过期时间（30分钟后）和创建时间
        from datetime import datetime, timedelta
        created_at = datetime.now()
        expires_at = created_at + timedelta(minutes=30)
        created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
        expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')

        # 统一更新数据库中的 expires_at（确保所有支付渠道都保存过期时间）
        if PaymentTransactionDAO and order_id:
            try:
                # 查找交易记录并更新 expires_at
                transaction = PaymentTransactionDAO.get_transaction_by_order_id(order_id)
                if transaction:
                    # 如果交易记录存在但没有 expires_at，更新它
                    from server.config.mysql_config import get_mysql_connection, return_mysql_connection
                    conn = get_mysql_connection()
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(
                                "UPDATE payment_transactions SET expires_at = %s WHERE order_id = %s",
                                (expires_at_str, order_id)
                            )
                            conn.commit()
                            logger.info(f"已更新订单过期时间: order_id={order_id}, expires_at={expires_at_str}")
                    finally:
                        return_mysql_connection(conn)
            except Exception as e:
                logger.warning(f"更新订单过期时间失败: {e}")

        # 构建统一的响应格式
        response_data = {
            "success": True,
            "provider": provider_str,
            "status": result.get('status', 'created'),
            "message": result.get('message', f'{provider_str} 支付创建成功'),
            "created_at": result.get('created_at', created_at_str),  # 优先使用客户端返回的时间
            "expires_at": result.get('expires_at', expires_at_str),  # 优先使用客户端返回的过期时间
        }

        # 根据支付平台的返回结果设置相应的字段
        if 'transaction_id' in result:
            response_data['transaction_id'] = result['transaction_id']
            # 统一接口：PayerMax 的 transaction_id 也映射到 payment_id（与其他支付渠道保持一致）
            if provider_str == "payermax" and not response_data.get('payment_id'):
                response_data['payment_id'] = result['transaction_id']
        if 'order_id' in result:
            response_data['order_id'] = result['order_id']
        if 'payment_id' in result:
            response_data['payment_id'] = result['payment_id']
        if 'payment_url' in result:
            response_data['payment_url'] = result['payment_url']
        if 'checkout_url' in result:
            response_data['checkout_url'] = result['checkout_url']
        if 'approval_url' in result:
            response_data['approval_url'] = result['approval_url']
        if 'code_url' in result:
            response_data['code_url'] = result['code_url']
        if 'jsapi_params' in result:
            response_data['jsapi_params'] = result['jsapi_params']

        return CreatePaymentResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"支付创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"支付创建失败: {str(e)}")


@router.post("/payment/unified/verify", response_model=VerifyPaymentResponse, summary="统一验证支付")
def verify_unified_payment(request: VerifyPaymentRequest):
    """
    统一验证支付状态 - 基于插件化架构

    根据不同支付渠道，使用对应的ID进行验证：
    - **Stripe**: session_id
    - **PayPal**: payment_id
    - **Payssion**: transaction_id
    - **PayerMax**: transaction_id 或 order_id
    - **Alipay**: order_id
    - **WeChat**: order_id
    - **Line Pay**: transaction_id
    """
    try:
        provider = request.provider
        # 确保 provider 是字符串（如果是枚举，转换为值）
        provider_str = provider.value if hasattr(provider, 'value') else str(provider)

        # 获取支付客户端（如果失败，尝试重新加载模块）
        try:
            payment_client = get_payment_client(provider_str)
        except ValueError as e:
            # 如果客户端未注册，尝试重新加载支付服务模块
            if "不支持的支付平台" in str(e):
                try:
                    import importlib
                    import sys
                    if 'services.payment_service' in sys.modules:
                        importlib.reload(sys.modules['services.payment_service'])
                    # 再次尝试获取客户端
                    payment_client = get_payment_client(provider_str)
                except Exception as reload_error:
                    logger.warning(f"重新加载支付服务模块失败: {reload_error}")
                    raise HTTPException(status_code=400, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))

        # 检查支付客户端是否启用
        if not payment_client.is_enabled:
            raise HTTPException(status_code=400, detail=f"支付渠道 {provider_str} 未启用，请检查配置")

        # 构建验证参数
        verify_params = {}

        # 根据支付平台设置验证参数
        order_id_for_check = None
        if provider_str == "stripe":
            if not request.session_id:
                raise HTTPException(status_code=400, detail="Stripe验证需要提供session_id")
            verify_params["session_id"] = request.session_id
            # Stripe 通过 session_id 查找 order_id（从数据库）
            if PaymentTransactionDAO:
                transaction = PaymentTransactionDAO.get_transaction_by_provider_payment_id(
                    provider_payment_id=request.session_id,
                    provider='stripe'
                )
                if transaction:
                    order_id_for_check = transaction.get('order_id')
        elif provider_str == "paypal":
            if not request.payment_id:
                raise HTTPException(status_code=400, detail="PayPal验证需要提供payment_id")
            verify_params["payment_id"] = request.payment_id
            # PayPal 通过 payment_id 查找 order_id
            if PaymentTransactionDAO:
                transaction = PaymentTransactionDAO.get_transaction_by_provider_payment_id(
                    provider_payment_id=request.payment_id,
                    provider='paypal'
                )
                if transaction:
                    order_id_for_check = transaction.get('order_id')
        elif provider_str == "payermax":
            # PayerMax 支持 transaction_id 或 order_id 验证
            if request.transaction_id:
                verify_params["transaction_id"] = request.transaction_id
                # 通过 transaction_id 查找 order_id
                if PaymentTransactionDAO:
                    transaction = PaymentTransactionDAO.get_transaction_by_provider_payment_id(
                        provider_payment_id=request.transaction_id,
                        provider='payermax'
                    )
                    if transaction:
                        order_id_for_check = transaction.get('order_id')
            elif request.order_id:
                verify_params["order_id"] = request.order_id
                order_id_for_check = request.order_id
            else:
                raise HTTPException(status_code=400, detail="PayerMax验证需要提供transaction_id或order_id")
        elif provider in ["payssion", "linepay"]:
            if not request.transaction_id:
                raise HTTPException(status_code=400, detail=f"{provider}验证需要提供transaction_id")
            verify_params["transaction_id"] = request.transaction_id
            # 通过 transaction_id 查找 order_id
            if PaymentTransactionDAO:
                transaction = PaymentTransactionDAO.get_transaction_by_provider_payment_id(
                    provider_payment_id=request.transaction_id,
                    provider=provider
                )
                if transaction:
                    order_id_for_check = transaction.get('order_id')
        elif provider in ["alipay", "wechat"]:
            if not request.order_id:
                raise HTTPException(status_code=400, detail=f"{provider}验证需要提供order_id")
            verify_params["order_id"] = request.order_id
            order_id_for_check = request.order_id

        # 检查订单是否过期（后端强制检查）
        if PaymentTransactionDAO and order_id_for_check:
            is_expired = PaymentTransactionDAO.check_expired(order_id_for_check)
            if is_expired:
                return VerifyPaymentResponse(
                    success=False,
                    provider=provider_str,
                    message="订单已过期，请重新创建订单"
                )

        # 调用支付客户端验证支付
        result = payment_client.verify_payment(**verify_params)

        if not result.get('success', False):
            return VerifyPaymentResponse(
                success=False,
                provider=provider,
                message=result.get('error', f'{provider} 验证失败')
            )

        # 构建统一的响应格式
        response_data = {
            "success": True,
            "provider": provider_str,
            "status": result.get('status'),
            "paid": result.get('paid', False),
            "message": result.get('message', '验证成功'),
        }

        # 设置相应的字段
        if 'payment_id' in result:
            response_data['payment_id'] = result['payment_id']
        if 'order_id' in result:
            response_data['order_id'] = result['order_id']
        if 'amount' in result:
            response_data['amount'] = result['amount']
        if 'currency' in result:
            response_data['currency'] = result['currency']
        if 'customer_email' in result:
            response_data['customer_email'] = result['customer_email']
        if 'paid_time' in result:
            response_data['paid_time'] = result['paid_time']

        return VerifyPaymentResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"支付验证失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"支付验证失败: {str(e)}")


@router.get("/payment/providers", summary="获取可用支付渠道")
def get_payment_providers():
    """
    获取所有可用的支付渠道及其状态

    返回各支付渠道的配置状态和适用地区
    """
    # 获取所有已注册的支付平台状态
    available_providers = payment_client_factory.get_available_providers()

    # 支付平台信息配置
    provider_info = {
        "stripe": {
            "name": "Stripe",
            "regions": ["美洲", "欧洲", "香港", "菲律宾", "新加坡", "日本", "中国", "全球"],
            "currencies": ["USD", "EUR", "HKD", "PHP", "GBP", "AUD", "CAD", "SGD", "JPY", "CNY"],
            "description": "全球领先的在线支付平台，支持信用卡和多种本地支付方式"
        },
        "paypal": {
            "name": "PayPal",
            "regions": ["全球"],
            "currencies": ["USD", "EUR", "HKD", "GBP", "AUD"],
            "description": "全球认知度最高的支付平台，支持多种支付方式"
        },
        "payssion": {
            "name": "Payssion",
            "regions": ["台湾", "日本", "泰国", "香港", "中国", "全球"],
            "currencies": ["USD", "HKD", "TWD", "JPY", "THB", "CNY", "EUR"],
            "description": "第三方支付聚合平台，香港公司可用于台湾 LINE Pay"
        },
        "payermax": {
            "name": "PayerMax",
            "regions": ["全球", "东南亚", "欧洲", "美洲", "中东", "非洲"],
            "currencies": ["USD", "HKD", "EUR", "GBP", "SGD", "AUD", "CAD", "JPY", "CNY", "THB", "PHP", "MYR", "IDR", "VND"],
            "description": "全球支付聚合平台，支持600+支付方式"
        },
        "alipay": {
            "name": "支付宝国际版",
            "regions": ["中国", "香港", "澳门"],
            "currencies": ["CNY", "HKD", "USD"],
            "description": "中国用户首选支付方式"
        },
        "wechat": {
            "name": "微信支付",
            "regions": ["中国", "香港", "澳门"],
            "currencies": ["CNY", "HKD"],
            "description": "中国用户常用支付方式"
        },
        "linepay": {
            "name": "Line Pay",
            "regions": ["台湾", "日本", "泰国"],
            "currencies": ["TWD", "JPY", "THB", "USD"],
            "description": "台湾、日本、泰国地区常用支付方式（需要台湾公司账号）"
        }
    }

    providers = []
    for provider_id, enabled in available_providers.items():
        if provider_id in provider_info:
            info = provider_info[provider_id]
            providers.append({
                "id": provider_id,
                "name": info["name"],
                "enabled": enabled,
                "regions": info["regions"],
                "currencies": info["currencies"],
                "description": info["description"]
            })

    return {
        "success": True,
        "providers": providers
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
    - taiwan: 台湾
    - japan: 日本
    - thailand: 泰国
    """
    # 获取可用的支付平台
    available_providers = payment_client_factory.get_available_providers()
    enabled_providers = [p for p, enabled in available_providers.items() if enabled]

    recommendations = []

    # 智能推荐逻辑
    if region == "taiwan":
        # 台湾优先推荐 LINE Pay（通过 Payssion）
        if "payssion" in enabled_providers:
            recommendations.append("payssion")
        elif "linepay" in enabled_providers:
            recommendations.append("linepay")
        # 备选方案
        recommendations.extend([p for p in ["stripe", "paypal", "payermax"] if p in enabled_providers])
    elif region in ["japan", "thailand"]:
        # 日本、泰国优先 LINE Pay
        if "linepay" in enabled_providers:
            recommendations.append("linepay")
        elif "payssion" in enabled_providers:
            recommendations.append("payssion")
        recommendations.extend([p for p in ["stripe", "paypal", "payermax"] if p in enabled_providers])
    elif region == "china":
        # 中国大陆优先本地支付
        recommendations.extend([p for p in ["alipay", "wechat"] if p in enabled_providers])
        recommendations.extend([p for p in ["stripe", "paypal", "payermax"] if p in enabled_providers])
    elif region == "hongkong":
        # 香港支持多种支付
        recommendations.extend([p for p in ["stripe", "paypal", "alipay", "wechat", "payermax"] if p in enabled_providers])
    elif region in ["americas", "europe"]:
        # 美洲、欧洲优先 Stripe 和 PayPal
        recommendations.extend([p for p in ["stripe", "paypal", "payermax"] if p in enabled_providers])
    elif region == "philippines":
        # 菲律宾优先 Stripe（支持PHP）
        recommendations.extend([p for p in ["stripe", "paypal", "payermax"] if p in enabled_providers])
    else:  # global 或其他地区
        # 全局推荐所有可用支付
        recommendations = enabled_providers.copy()

    # 根据货币进一步优化推荐
    if currency == "CNY":
        # 人民币优先支付宝和微信
        china_payments = [p for p in ["alipay", "wechat"] if p in recommendations]
        other_payments = [p for p in recommendations if p not in ["alipay", "wechat"]]
        recommendations = china_payments + other_payments
    elif currency in ["TWD", "JPY", "THB"]:
        # 亚洲货币优先 LINE Pay 相关
        linepay_payments = [p for p in ["linepay", "payssion"] if p in recommendations]
        other_payments = [p for p in recommendations if p not in ["linepay", "payssion"]]
        recommendations = linepay_payments + other_payments
    elif currency in ["HKD", "PHP"]:
        # 特定货币优先支持的平台
        currency_supported = [p for p in recommendations if currency in get_payment_client(p).get_supported_currencies()]
        currency_supported.extend([p for p in recommendations if p not in currency_supported])
        recommendations = currency_supported[:len(recommendations)]  # 保持原有长度

    # 移除重复并保持顺序
    seen = set()
    recommendations = [p for p in recommendations if not (p in seen or seen.add(p))]

    return {
        "success": True,
        "region": region,
        "currency": currency,
        "recommended": recommendations,
        "primary": recommendations[0] if recommendations else "stripe",
        "available_count": len(recommendations)
    }

