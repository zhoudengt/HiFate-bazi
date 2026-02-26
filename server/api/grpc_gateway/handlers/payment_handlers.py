# -*- coding: utf-8 -*-
"""
支付相关 gRPC-Web 端点处理器

v1 旧接口 /payment/create-session、/payment/verify 已下线，
前端统一走 /payment/unified/* 系列接口（stripe_client_v2）。
"""

from typing import Any, Dict

from server.api.grpc_gateway.endpoints import _register
from server.api.v1.unified_payment import (
    CreatePaymentRequest as UnifiedCreatePaymentRequest,
    VerifyPaymentRequest as UnifiedVerifyPaymentRequest,
    create_unified_payment,
    verify_unified_payment,
    get_payment_providers,
)


@_register("/payment/unified/create")
async def _handle_unified_payment_create(payload: Dict[str, Any]):
    """处理统一支付创建请求"""
    request_model = UnifiedCreatePaymentRequest(**payload)
    return create_unified_payment(request_model)


@_register("/payment/unified/verify")
async def _handle_unified_payment_verify(payload: Dict[str, Any]):
    """处理统一支付验证请求"""
    request_model = UnifiedVerifyPaymentRequest(**payload)
    return verify_unified_payment(request_model)


@_register("/payment/providers")
async def _handle_payment_providers(payload: Dict[str, Any]):
    """处理获取支付渠道列表请求（GET 转 POST）"""
    return get_payment_providers()
