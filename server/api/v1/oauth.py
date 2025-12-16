#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth 2.0 认证 API

实现标准的 OAuth 2.0 授权码流程：
1. 前端重定向到 /oauth/authorize 获取授权码
2. 前端使用授权码调用 /oauth/token 获取 Token
3. 前端使用 Refresh Token 调用 /oauth/refresh 刷新 Token
"""

import os
import secrets
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse

from .oauth_models import (
    AuthorizeRequest,
    AuthorizeResponse,
    TokenRequest,
    TokenResponse,
    RefreshTokenRequest,
    RevokeTokenRequest,
    RevokeTokenResponse,
)

from services.auth_service.config import (
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_SECRET,
    OAUTH_AUTHORIZATION_CODE_EXPIRE_MINUTES,
    OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES,
    OAUTH_REFRESH_TOKEN_EXPIRE_DAYS,
    REDIS_KEY_PREFIX_AUTH_CODE,
    REDIS_KEY_PREFIX_ACCESS_TOKEN,
    REDIS_KEY_PREFIX_REFRESH_TOKEN,
)

from src.clients.auth_client_grpc import get_auth_client

router = APIRouter()

# 尝试导入 Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Redis 客户端（如果可用）
redis_client = None
if REDIS_AVAILABLE:
    try:
        from services.auth_service.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=2
        )
        redis_client.ping()
    except Exception:
        redis_client = None

# 内存存储（Redis 不可用时的降级方案）
_memory_storage = {}
_memory_storage_ttl = {}


def _get_redis_key(key_type: str, value: str) -> str:
    """获取 Redis 键"""
    prefixes = {
        "auth_code": REDIS_KEY_PREFIX_AUTH_CODE,
        "access_token": REDIS_KEY_PREFIX_ACCESS_TOKEN,
        "refresh_token": REDIS_KEY_PREFIX_REFRESH_TOKEN,
    }
    return f"{prefixes.get(key_type, 'auth:')}{value}"


def _save_auth_code(code: str, client_id: str, redirect_uri: str, user_id: str = "default_user", ttl_seconds: int = None):
    """保存授权码"""
    if ttl_seconds is None:
        ttl_seconds = OAUTH_AUTHORIZATION_CODE_EXPIRE_MINUTES * 60
    
    info = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "user_id": user_id,
        "created_at": time.time(),
    }
    
    if redis_client:
        try:
            key = _get_redis_key("auth_code", code)
            redis_client.setex(key, ttl_seconds, str(info))  # 简化存储
        except Exception:
            pass
    
    # 降级到内存存储
    _memory_storage[code] = info
    _memory_storage_ttl[code] = time.time() + ttl_seconds


def _get_auth_code(code: str) -> Optional[dict]:
    """获取授权码信息"""
    if redis_client:
        try:
            key = _get_redis_key("auth_code", code)
            data = redis_client.get(key)
            if data:
                # 简化解析（实际应该存储 JSON）
                return {"client_id": OAUTH_CLIENT_ID, "redirect_uri": "", "user_id": "default_user"}
        except Exception:
            pass
    
    # 降级到内存存储
    if code in _memory_storage:
        if code in _memory_storage_ttl:
            if time.time() > _memory_storage_ttl[code]:
                del _memory_storage[code]
                del _memory_storage_ttl[code]
                return None
        return _memory_storage[code]
    
    return None


def _delete_auth_code(code: str):
    """删除授权码（使用后立即删除）"""
    if redis_client:
        try:
            key = _get_redis_key("auth_code", code)
            redis_client.delete(key)
        except Exception:
            pass
    
    # 降级到内存存储
    if code in _memory_storage:
        del _memory_storage[code]
        if code in _memory_storage_ttl:
            del _memory_storage_ttl[code]


def _generate_token() -> str:
    """生成安全的 Token"""
    return secrets.token_urlsafe(32)


@router.get("/oauth/authorize")
async def authorize(
    client_id: str = Query(..., description="客户端 ID"),
    redirect_uri: str = Query(..., description="重定向 URI"),
    response_type: str = Query(default="code", description="响应类型"),
    state: Optional[str] = Query(None, description="状态参数"),
    scope: Optional[str] = Query(None, description="权限范围"),
):
    """
    OAuth 2.0 授权端点
    
    前端重定向到此端点，获取授权码后重定向回 redirect_uri
    """
    # 验证客户端 ID
    if client_id != OAUTH_CLIENT_ID:
        raise HTTPException(status_code=400, detail="无效的客户端 ID")
    
    # 验证 response_type
    if response_type != "code":
        raise HTTPException(status_code=400, detail="response_type 必须为 'code'")
    
    # 生成授权码
    auth_code = _generate_token()
    
    # 保存授权码（临时存储，10分钟后过期）
    _save_auth_code(auth_code, client_id, redirect_uri)
    
    # 构建重定向 URL
    redirect_url = f"{redirect_uri}?code={auth_code}"
    if state:
        redirect_url += f"&state={state}"
    
    # 重定向到前端
    return RedirectResponse(url=redirect_url)


@router.post("/oauth/token", response_model=TokenResponse)
async def token(request: TokenRequest):
    """
    OAuth 2.0 Token 获取端点
    
    使用授权码或 Refresh Token 获取 Access Token
    """
    # 验证客户端凭证
    if request.client_id != OAUTH_CLIENT_ID or request.client_secret != OAUTH_CLIENT_SECRET:
        raise HTTPException(status_code=401, detail="客户端凭证无效")
    
    if request.grant_type == "authorization_code":
        # 授权码流程
        if not request.code:
            raise HTTPException(status_code=400, detail="授权码不能为空")
        
        # 获取授权码信息
        code_info = _get_auth_code(request.code)
        if not code_info:
            raise HTTPException(status_code=400, detail="授权码无效或已过期")
        
        # 验证 redirect_uri（如果提供）
        if request.redirect_uri and request.redirect_uri != code_info.get("redirect_uri"):
            raise HTTPException(status_code=400, detail="redirect_uri 不匹配")
        
        # 删除授权码（一次性使用）
        _delete_auth_code(request.code)
        
        # 获取用户信息
        user_id = code_info.get("user_id", "default_user")
        expires_in = OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh_token_expires_in = OAUTH_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        
        # 解析 scope（如果有）
        scope_list = []
        if hasattr(request, 'scope') and request.scope:
            if isinstance(request.scope, str):
                scope_list = [s.strip() for s in request.scope.split() if s.strip()]
            elif isinstance(request.scope, list):
                scope_list = request.scope
        
        # 调用认证服务创建 Token
        auth_client = get_auth_client()
        result = auth_client.create_token(
            user_id=user_id,
            client_id=request.client_id,
            scope=scope_list,
            access_token_expires_in=expires_in,
            refresh_token_expires_in=refresh_token_expires_in
        )
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Token 创建失败"))
        
        return TokenResponse(
            access_token=result["access_token"],
            token_type=result.get("token_type", "bearer"),
            expires_in=result.get("expires_in", expires_in),
            refresh_token=result.get("refresh_token"),
            scope=request.scope if hasattr(request, 'scope') and request.scope else None,
        )
    
    elif request.grant_type == "refresh_token":
        # Refresh Token 流程
        if not request.refresh_token:
            raise HTTPException(status_code=400, detail="Refresh Token 不能为空")
        
        # 调用认证服务刷新 Token
        auth_client = get_auth_client()
        result = auth_client.refresh_token(
            request.refresh_token,
            request.client_id,
            request.client_secret
        )
        
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Token 刷新失败"))
        
        # 解析 scope（如果有）
        scope_list = []
        if hasattr(request, 'scope') and request.scope:
            if isinstance(request.scope, str):
                scope_list = [s.strip() for s in request.scope.split() if s.strip()]
            elif isinstance(request.scope, list):
                scope_list = request.scope
        
        return TokenResponse(
            access_token=result["access_token"],
            token_type=result.get("token_type", "bearer"),
            expires_in=result.get("expires_in", OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60),
            refresh_token=result.get("refresh_token"),
            scope=request.scope if hasattr(request, 'scope') and request.scope else None,
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"不支持的 grant_type: {request.grant_type}")


@router.post("/oauth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Token 刷新端点（简化版，直接调用认证服务）
    """
    # 调用认证服务刷新 Token
    auth_client = get_auth_client()
    result = auth_client.refresh_token(
        request.refresh_token,
        request.client_id,
        request.client_secret
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Token 刷新失败"))
    
    return TokenResponse(
        access_token=result["access_token"],
        token_type=result.get("token_type", "bearer"),
        expires_in=result.get("expires_in", OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        refresh_token=result.get("refresh_token"),
    )


@router.post("/oauth/revoke", response_model=RevokeTokenResponse)
async def revoke_token(request: RevokeTokenRequest):
    """
    Token 撤销端点（可选功能）
    """
    # 简化实现：从 Redis 删除 Token
    if redis_client:
        try:
            if request.token_type_hint == "access_token" or not request.token_type_hint:
                key = _get_redis_key("access_token", request.token)
                redis_client.delete(key)
            if request.token_type_hint == "refresh_token" or not request.token_type_hint:
                key = _get_redis_key("refresh_token", request.token)
                redis_client.delete(key)
        except Exception:
            pass
    
    # 降级到内存存储
    if request.token in _memory_storage:
        del _memory_storage[request.token]
        if request.token in _memory_storage_ttl:
            del _memory_storage_ttl[request.token]
    
    return RevokeTokenResponse(success=True)
