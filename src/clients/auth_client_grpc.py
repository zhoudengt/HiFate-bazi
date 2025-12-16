#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gRPC client for calling the auth-service."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, Optional

import grpc

# 导入生成的 gRPC 代码
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "proto", "generated"))

import auth_pb2
import auth_pb2_grpc

logger = logging.getLogger(__name__)


class AuthClient:
    """gRPC client for the auth-service."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        # base_url 格式: host:port 或 [host]:port
        base_url = base_url or os.getenv("AUTH_SERVICE_URL", "")
        if not base_url:
            # 默认使用 localhost:9011
            base_url = "localhost:9011"
        
        # 解析地址（移除 http:// 前缀）
        if base_url.startswith("http://"):
            base_url = base_url[7:]
        elif base_url.startswith("https://"):
            base_url = base_url[8:]
        
        # 如果没有端口，添加默认端口
        if ":" not in base_url:
            base_url = f"{base_url}:9011"
        
        self.address = base_url
        self.timeout = timeout

    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证 Token 是否有效"""
        request = auth_pb2.VerifyTokenRequest(token=token)
        
        logger.debug(f"调用 auth-service (gRPC): {self.address}, token={token[:20]}...")
        
        # 设置连接选项
        options = [
            ('grpc.keepalive_time_ms', 300000),  # 5分钟
            ('grpc.keepalive_timeout_ms', 20000),  # 20秒超时
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),  # ping 之间至少间隔60秒
        ]
        
        with grpc.insecure_channel(self.address, options=options) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            try:
                response = stub.VerifyToken(request, timeout=self.timeout)
                
                return {
                    "valid": response.valid,
                    "user_id": response.user_id,
                    "client_id": response.client_id,
                    "expires_at": response.expires_at,
                    "error": response.error if response.error else None,
                }
                
            except grpc.RpcError as e:
                logger.error(f"auth-service (gRPC): 调用失败 - {e}")
                return {
                    "valid": False,
                    "error": f"认证服务错误: {e.code()}",
                }

    def refresh_token(self, refresh_token: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """刷新 Token"""
        request = auth_pb2.RefreshTokenRequest(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret
        )
        
        logger.debug(f"调用 auth-service (gRPC): {self.address}, refresh_token={refresh_token[:20]}...")
        
        # 设置连接选项
        options = [
            ('grpc.keepalive_time_ms', 300000),  # 5分钟
            ('grpc.keepalive_timeout_ms', 20000),  # 20秒超时
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),
        ]
        
        with grpc.insecure_channel(self.address, options=options) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            try:
                response = stub.RefreshToken(request, timeout=self.timeout)
                
                return {
                    "success": response.success,
                    "access_token": response.access_token,
                    "refresh_token": response.refresh_token if response.refresh_token else None,
                    "expires_in": response.expires_in,
                    "token_type": response.token_type,
                    "error": response.error if response.error else None,
                }
                
            except grpc.RpcError as e:
                logger.error(f"auth-service (gRPC): 刷新 Token 失败 - {e}")
                return {
                    "success": False,
                    "error": f"认证服务错误: {e.code()}",
                }

    def get_token_info(self, token: str) -> Dict[str, Any]:
        """获取 Token 信息"""
        request = auth_pb2.GetTokenInfoRequest(token=token)
        
        logger.debug(f"调用 auth-service (gRPC): {self.address}, token={token[:20]}...")
        
        # 设置连接选项
        options = [
            ('grpc.keepalive_time_ms', 300000),  # 5分钟
            ('grpc.keepalive_timeout_ms', 20000),  # 20秒超时
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),
        ]
        
        with grpc.insecure_channel(self.address, options=options) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            try:
                response = stub.GetTokenInfo(request, timeout=self.timeout)
                
                return {
                    "valid": response.valid,
                    "user_id": response.user_id,
                    "client_id": response.client_id,
                    "scope": list(response.scope),
                    "issued_at": response.issued_at,
                    "expires_at": response.expires_at,
                    "error": response.error if response.error else None,
                }
                
            except grpc.RpcError as e:
                logger.error(f"auth-service (gRPC): 获取 Token 信息失败 - {e}")
                return {
                    "valid": False,
                    "error": f"认证服务错误: {e.code()}",
                }

    def create_token(self, user_id: str, client_id: str, scope: list = None, 
                     access_token_expires_in: int = 0, refresh_token_expires_in: int = 0) -> Dict[str, Any]:
        """创建 Token"""
        request = auth_pb2.CreateTokenRequest(
            user_id=user_id,
            client_id=client_id,
            scope=scope or [],
            access_token_expires_in=access_token_expires_in,
            refresh_token_expires_in=refresh_token_expires_in
        )
        
        logger.debug(f"调用 auth-service (gRPC): {self.address}, user_id={user_id}, client_id={client_id}")
        
        # 设置连接选项
        options = [
            ('grpc.keepalive_time_ms', 300000),  # 5分钟
            ('grpc.keepalive_timeout_ms', 20000),  # 20秒超时
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),
        ]
        
        with grpc.insecure_channel(self.address, options=options) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            try:
                response = stub.CreateToken(request, timeout=self.timeout)
                
                return {
                    "success": response.success,
                    "access_token": response.access_token,
                    "refresh_token": response.refresh_token,
                    "expires_in": response.expires_in,
                    "token_type": response.token_type,
                    "error": response.error if response.error else None,
                }
                
            except grpc.RpcError as e:
                logger.error(f"auth-service (gRPC): 创建 Token 失败 - {e}")
                return {
                    "success": False,
                    "error": f"认证服务错误: {e.code()}",
                }

    def health_check(self) -> bool:
        """健康检查"""
        request = auth_pb2.HealthCheckRequest()
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = auth_pb2_grpc.AuthServiceStub(channel)
                response = stub.HealthCheck(request, timeout=5.0)
                return response.status == "ok"
        except grpc.RpcError:
            logger.exception("auth-service health check failed")
            return False


# 全局客户端实例（单例模式）
_auth_client_instance: Optional[AuthClient] = None


def get_auth_client() -> AuthClient:
    """获取认证客户端实例（单例）"""
    global _auth_client_instance
    if _auth_client_instance is None:
        _auth_client_instance = AuthClient()
    return _auth_client_instance
