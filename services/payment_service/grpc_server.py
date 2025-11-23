#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC server for payment-service.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent import futures

import grpc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 导入生成的 gRPC 代码
sys.path.insert(0, os.path.join(PROJECT_ROOT, "proto", "generated"))
import payment_pb2
import payment_pb2_grpc

from services.payment_service.stripe_client import StripeClient


class PaymentServicer(payment_pb2_grpc.PaymentServiceServicer):
    """实现 PaymentService 的 gRPC 服务"""

    def __init__(self):
        self.stripe_client = StripeClient()

    def CreatePaymentSession(
        self,
        request: payment_pb2.CreatePaymentSessionRequest,
        context: grpc.ServicerContext
    ) -> payment_pb2.CreatePaymentSessionResponse:
        """创建支付会话"""
        try:
            result = self.stripe_client.create_checkout_session(
                amount=request.amount,
                currency=request.currency or "USD",
                product_name=request.product_name,
                customer_email=request.customer_email,
                metadata=dict(request.metadata) if request.metadata else None,
            )
            
            response = payment_pb2.CreatePaymentSessionResponse()
            response.session_id = result["session_id"]
            response.checkout_url = result["checkout_url"]
            response.status = result["status"]
            response.message = "支付会话创建成功"
            
            return response
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"创建支付会话失败: {str(e)}")
            response = payment_pb2.CreatePaymentSessionResponse()
            response.status = "failed"
            response.message = str(e)
            return response

    def VerifyPayment(
        self,
        request: payment_pb2.VerifyPaymentRequest,
        context: grpc.ServicerContext
    ) -> payment_pb2.VerifyPaymentResponse:
        """验证支付状态"""
        try:
            result = self.stripe_client.retrieve_session(request.session_id)
            
            response = payment_pb2.VerifyPaymentResponse()
            response.status = result["status"]
            
            if result.get("payment_intent_id"):
                response.payment_intent_id = result["payment_intent_id"]
            if result.get("amount"):
                response.amount = result["amount"]
            if result.get("currency"):
                response.currency = result["currency"]
            if result.get("customer_email"):
                response.customer_email = result["customer_email"]
            if result.get("created_at"):
                response.created_at = result["created_at"]
            if result.get("metadata"):
                response.metadata.update(result["metadata"])
            
            return response
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"验证支付状态失败: {str(e)}")
            return payment_pb2.VerifyPaymentResponse()

    def HealthCheck(
        self,
        request: payment_pb2.HealthCheckRequest,
        context: grpc.ServicerContext
    ) -> payment_pb2.HealthCheckResponse:
        """健康检查"""
        return payment_pb2.HealthCheckResponse(status="ok")


def serve(port: int = 9006):
    """启动 gRPC 服务器"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    payment_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentServicer(), server)
    
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    
    server.start()
    print(f"✅ Payment gRPC 服务已启动，监听端口: {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n>>> 正在停止服务...")
        server.stop(grace=5)
        print("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Payment gRPC 服务")
    parser.add_argument("--port", type=int, default=9006, help="服务端口（默认: 9006）")
    args = parser.parse_args()
    serve(args.port)

