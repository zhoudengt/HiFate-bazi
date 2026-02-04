#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付 Webhook 处理
处理第三方支付平台的异步通知（如 Stripe Webhook）
"""

import sys
import os
import logging
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if str(project_root) not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

router = APIRouter()

# 导入支付交易 DAO
try:
    from server.db.payment_transaction_dao import PaymentTransactionDAO
except ImportError as e:
    logger.warning(f"导入支付交易DAO失败: {e}")
    PaymentTransactionDAO = None

# 导入 Stripe
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("stripe库未安装，Stripe Webhook功能不可用")

# 导入支付配置加载器
try:
    from services.payment_service.payment_config_loader import get_payment_config
except ImportError:
    def get_payment_config(provider: str, config_key: str, environment: str = 'production', default: Optional[str] = None) -> Optional[str]:
        return os.getenv(f"{provider.upper()}_{config_key.upper()}", default)


@router.post("/payment/webhook/stripe", summary="Stripe Webhook 处理")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """
    处理 Stripe Webhook 事件
    
    主要处理 `checkout.session.completed` 事件，用于可靠接收支付确认
    解决场景：用户已付款但跳转 success_url 时断网，后端通过 Webhook 可靠接收支付确认
    
    **安全要求**：
    - 必须验证 Stripe 签名，防止伪造请求
    - 必须处理重复事件（幂等性）
    """
    if not STRIPE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Stripe库未安装，Webhook功能不可用")
    
    if not PaymentTransactionDAO:
        raise HTTPException(status_code=503, detail="支付交易DAO未初始化")
    
    # 获取请求体
    payload = await request.body()
    
    # 获取 Stripe Webhook Secret
    webhook_secret = get_payment_config('stripe', 'webhook_secret', 'production') or os.getenv("STRIPE_WEBHOOK_SECRET")
    
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET未配置，无法验证Webhook签名")
        raise HTTPException(status_code=500, detail="Webhook配置不完整")
    
    if not stripe_signature:
        logger.warning("缺少Stripe签名头，拒绝请求")
        raise HTTPException(status_code=400, detail="缺少Stripe签名")
    
    try:
        # 验证签名并解析事件
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Webhook payload解析失败: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook签名验证失败: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # 处理事件
    event_type = event.get('type')
    event_data = event.get('data', {}).get('object', {})
    
    logger.info(f"收到Stripe Webhook事件: {event_type}, event_id={event.get('id')}")
    
    # 处理 checkout.session.completed 事件
    if event_type == 'checkout.session.completed':
        session_id = event_data.get('id')
        payment_status = event_data.get('payment_status')
        
        if not session_id:
            logger.warning("checkout.session.completed事件缺少session_id")
            return {"received": True, "message": "事件处理跳过（缺少session_id）"}
        
        # 查找交易记录
        transaction = PaymentTransactionDAO.get_transaction_by_provider_payment_id(
            provider_payment_id=session_id,
            provider='stripe'
        )
        
        if not transaction:
            logger.warning(f"未找到对应的交易记录: session_id={session_id}")
            return {"received": True, "message": "事件处理跳过（未找到交易记录）"}
        
        # 检查是否已经处理过（幂等性）
        if transaction.get('status') == 'success':
            logger.info(f"订单已处理过，跳过: order_id={transaction.get('order_id')}")
            return {"received": True, "message": "订单已处理过"}
        
        # 更新订单状态
        from datetime import datetime
        paid_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        success = PaymentTransactionDAO.update_status_by_provider_payment_id(
            provider_payment_id=session_id,
            provider='stripe',
            status='success' if payment_status == 'paid' else transaction.get('status', 'pending'),
            paid_at=paid_at if payment_status == 'paid' else None
        )
        
        if success:
            logger.info(f"订单状态已更新: session_id={session_id}, status=success")
            return {
                "received": True,
                "message": "订单状态已更新",
                "session_id": session_id,
                "status": "success"
            }
        else:
            logger.error(f"更新订单状态失败: session_id={session_id}")
            return {
                "received": True,
                "message": "更新订单状态失败",
                "session_id": session_id
            }
    
    # 其他事件类型（可选处理）
    else:
        logger.info(f"收到未处理的事件类型: {event_type}")
        return {"received": True, "message": f"事件类型 {event_type} 暂未处理"}


@router.get("/payment/webhook/stripe", summary="Stripe Webhook 测试端点")
def stripe_webhook_test():
    """
    Webhook 测试端点（用于 Stripe Dashboard 配置验证）
    """
    return {
        "status": "ok",
        "message": "Stripe Webhook端点已配置",
        "endpoint": "/api/v1/payment/webhook/stripe",
        "method": "POST"
    }


# ========== PayerMax Webhook ==========

@router.post("/payment/webhook/payermax", summary="PayerMax Webhook 处理")
async def payermax_webhook(request: Request):
    """
    处理 PayerMax 异步通知
    
    PayerMax 会在支付完成后发送异步通知到此端点
    """
    import json
    
    # 获取请求体
    try:
        payload = await request.body()
        data = json.loads(payload.decode('utf-8'))
    except Exception as e:
        logger.error(f"PayerMax Webhook 解析请求体失败: {e}")
        return {"code": "FAIL", "msg": f"解析请求失败: {e}"}
    
    logger.info(f"收到PayerMax Webhook通知: {json.dumps(data, ensure_ascii=False)[:500]}")
    
    # 提取关键字段
    out_trade_no = data.get('outTradeNo')  # 商户订单号
    trade_token = data.get('tradeToken')    # PayerMax 交易号
    trade_status = data.get('tradeStatus')  # 交易状态: SUCCESS / FAILED
    total_amount = data.get('totalAmount')  # 金额
    currency = data.get('currency')         # 货币
    
    logger.info(f"PayerMax回调: outTradeNo={out_trade_no}, tradeToken={trade_token}, status={trade_status}")
    
    if not out_trade_no:
        logger.warning("PayerMax Webhook 缺少 outTradeNo")
        return {"code": "FAIL", "msg": "缺少 outTradeNo"}
    
    # 更新订单状态（如果有 PaymentTransactionDAO）
    if PaymentTransactionDAO and trade_status:
        try:
            from datetime import datetime
            
            # 映射状态
            status_map = {
                'SUCCESS': 'success',
                'FAILED': 'failed',
                'PENDING': 'pending'
            }
            new_status = status_map.get(trade_status, 'pending')
            
            # 查找交易记录
            transaction = PaymentTransactionDAO.get_transaction_by_order_id(order_id=out_trade_no)
            
            if transaction:
                # 检查幂等性
                if transaction.get('status') == 'success':
                    logger.info(f"PayerMax订单已处理过，跳过: order_id={out_trade_no}")
                    return {"code": "SUCCESS", "msg": "订单已处理"}
                
                # 更新状态
                paid_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if new_status == 'success' else None
                PaymentTransactionDAO.update_status_by_order_id(
                    order_id=out_trade_no,
                    status=new_status,
                    paid_at=paid_at
                )
                logger.info(f"PayerMax订单状态已更新: order_id={out_trade_no}, status={new_status}")
            else:
                logger.warning(f"PayerMax Webhook 未找到订单: order_id={out_trade_no}")
        except Exception as e:
            logger.error(f"PayerMax Webhook 更新订单失败: {e}")
    
    # 返回成功响应（PayerMax 要求返回 code=SUCCESS）
    return {"code": "SUCCESS", "msg": "OK"}


@router.get("/payment/webhook/payermax", summary="PayerMax Webhook 测试端点")
def payermax_webhook_test():
    """
    PayerMax Webhook 测试端点（用于验证配置）
    """
    return {
        "status": "ok",
        "message": "PayerMax Webhook端点已配置",
        "endpoint": "/api/v1/payment/webhook/payermax",
        "method": "POST"
    }
