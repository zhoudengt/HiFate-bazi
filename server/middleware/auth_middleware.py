#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth 2.0 认证中间件

拦截所有请求，验证 Bearer Token，支持白名单路径
"""

import logging
from typing import Callable, Any, Set
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.clients.auth_client_grpc import get_auth_client

logger = logging.getLogger(__name__)

# 白名单路径（不需要认证的路径）
WHITELIST_PATHS: Set[str] = {
    "/health",
    "/healthz",
    "/api/v1/auth/login",
    "/api/v1/oauth/authorize",
    "/api/v1/oauth/token",
    "/api/v1/oauth/refresh",
    "/api/grpc-web/frontend.gateway.FrontendGateway/Call",  # gRPC 网关路径（需要在网关内部处理认证）
    "/docs",
    "/openapi.json",
    "/redoc",
}

# 白名单路径前缀（API路径前缀，不需要认证）
WHITELIST_API_PREFIXES: Set[str] = {
    "/api/v1/hot-reload",  # 热更新接口（必须不需要认证，否则无法触发热更新）
}

# 白名单路径前缀（静态文件路径）
WHITELIST_PREFIXES: Set[str] = {
    "/local_frontend",  # 本地前端目录
    "/frontend",  # 前端目录别名
}

# gRPC 网关中不需要认证的端点（在网关内部处理）
GRPC_WHITELIST_ENDPOINTS: Set[str] = {
    "/auth/login",  # 登录接口
    "/oauth/authorize",  # OAuth 授权
    "/oauth/token",  # OAuth Token 获取
    "/oauth/refresh",  # OAuth Token 刷新
}


class AuthMiddleware(BaseHTTPMiddleware):
    """OAuth 2.0 认证中间件"""
    
    def __init__(self, app, whitelist_paths: Set[str] = None, whitelist_prefixes: Set[str] = None):
        """
        初始化认证中间件
        
        Args:
            app: FastAPI 应用实例
            whitelist_paths: 白名单路径集合（可选，默认使用全局白名单）
            whitelist_prefixes: 白名单路径前缀集合（可选，默认使用全局白名单前缀）
        """
        super().__init__(app)
        # ⭐ 强制使用全局白名单（确保使用最新的配置）
        self.whitelist_paths = whitelist_paths if whitelist_paths is not None else WHITELIST_PATHS.copy()
        self.whitelist_prefixes = whitelist_prefixes if whitelist_prefixes is not None else WHITELIST_PREFIXES.copy()
        self.auth_client = get_auth_client()
        
        # 调试：打印初始化信息
        logger.info(f"🔧 [认证中间件] 初始化完成")
        logger.info(f"   白名单路径数: {len(self.whitelist_paths)}")
        logger.info(f"   白名单前缀: {list(self.whitelist_prefixes)}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """
        处理请求，验证 Token
        
        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            响应对象
        """
        path = request.url.path
        
        # ⭐ 关键修复：直接使用全局变量，而不是实例变量
        # 这样可以确保即使中间件实例是旧的，也能使用最新的白名单配置
        
        # 1. 优先检查静态文件前缀（最高优先级，必须在所有检查之前）
        #    使用全局变量 WHITELIST_PREFIXES，确保使用最新配置
        for prefix in WHITELIST_PREFIXES:
            if path.startswith(prefix):
                # 静态文件路径，直接放行，不记录日志（减少日志量）
                return await call_next(request)
        
        # 2. 检查是否在白名单API前缀中（如热更新接口）
        for prefix in WHITELIST_API_PREFIXES:
            if path.startswith(prefix):
                logger.debug(f"✅ [认证中间件] API路径在白名单中: {path} (前缀: {prefix})")
                return await call_next(request)
        
        # 3. 检查是否在白名单中（使用全局变量）
        if path in WHITELIST_PATHS:
            logger.debug(f"✅ [认证中间件] 路径在白名单中: {path}")
            return await call_next(request)
        
        # 特殊处理：根路径和静态资源
        if path == "/" or path.startswith("/static/") or path.startswith("/assets/"):
            logger.info(f"✅ [认证中间件] 静态资源路径，放行: {path}")
            return await call_next(request)
        
        logger.warning(f"⚠️ [认证中间件] 路径不在白名单中，需要认证: {path}")
        
        # 特殊处理：gRPC 网关路径，认证在网关内部处理
        if request.url.path == "/api/grpc-web/frontend.gateway.FrontendGateway/Call":
            # gRPC 网关路径已经在白名单中，直接放行
            # 认证逻辑在 gRPC 网关内部根据 endpoint 处理
            return await call_next(request)
        
        # 提取 Bearer Token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"未提供认证信息: {request.method} {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "未提供认证信息，请在请求头中添加 Authorization: Bearer <token>",
                    "error_type": "unauthorized"
                }
            )
        
        # 提取 Token
        token = auth_header[7:]  # 移除 "Bearer " 前缀
        
        if not token:
            logger.warning(f"Token 为空: {request.method} {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "Token 为空",
                    "error_type": "unauthorized"
                }
            )
        
        # 验证 Token
        try:
            result = self.auth_client.verify_token(token)
            
            if not result.get("valid", False):
                error_msg = result.get("error", "Token 无效或已过期")
                logger.warning(f"Token 验证失败: {request.method} {request.url.path}, error: {error_msg}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "error": error_msg,
                        "error_type": "unauthorized"
                    }
                )
            
            # Token 验证成功，将用户信息添加到请求状态中（可选）
            request.state.user_id = result.get("user_id", "")
            request.state.client_id = result.get("client_id", "")
            request.state.token_expires_at = result.get("expires_at", 0)
            
            # 继续处理请求
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"认证服务错误: {request.method} {request.url.path}, error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "认证服务暂时不可用，请稍后重试",
                    "error_type": "service_unavailable"
                }
            )
