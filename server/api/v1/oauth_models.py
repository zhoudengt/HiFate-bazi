#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth 2.0 请求/响应模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class AuthorizeRequest(BaseModel):
    """授权码获取请求"""
    client_id: str = Field(..., description="客户端 ID")
    redirect_uri: str = Field(..., description="重定向 URI")
    response_type: str = Field(default="code", description="响应类型，固定为 'code'")
    state: Optional[str] = Field(None, description="状态参数，用于防止 CSRF 攻击")
    scope: Optional[str] = Field(None, description="权限范围（可选）")


class AuthorizeResponse(BaseModel):
    """授权码获取响应"""
    code: str = Field(..., description="授权码")
    state: Optional[str] = Field(None, description="状态参数（如果请求中包含）")


class TokenRequest(BaseModel):
    """Token 获取请求"""
    grant_type: str = Field(..., description="授权类型，'authorization_code' 或 'refresh_token'")
    code: Optional[str] = Field(None, description="授权码（grant_type='authorization_code' 时必需）")
    refresh_token: Optional[str] = Field(None, description="Refresh Token（grant_type='refresh_token' 时必需）")
    redirect_uri: Optional[str] = Field(None, description="重定向 URI（grant_type='authorization_code' 时必需）")
    client_id: str = Field(..., description="客户端 ID")
    client_secret: str = Field(..., description="客户端密钥")


class TokenResponse(BaseModel):
    """Token 获取响应"""
    access_token: str = Field(..., description="Access Token")
    token_type: str = Field(default="bearer", description="Token 类型，固定为 'bearer'")
    expires_in: int = Field(..., description="Access Token 过期时间（秒）")
    refresh_token: Optional[str] = Field(None, description="Refresh Token（可选）")
    scope: Optional[str] = Field(None, description="权限范围（可选）")


class RefreshTokenRequest(BaseModel):
    """Token 刷新请求"""
    refresh_token: str = Field(..., description="Refresh Token")
    client_id: str = Field(..., description="客户端 ID")
    client_secret: str = Field(..., description="客户端密钥")


class RefreshTokenResponse(BaseModel):
    """Token 刷新响应"""
    access_token: str = Field(..., description="新的 Access Token")
    token_type: str = Field(default="bearer", description="Token 类型，固定为 'bearer'")
    expires_in: int = Field(..., description="Access Token 过期时间（秒）")
    refresh_token: Optional[str] = Field(None, description="新的 Refresh Token（可选，如果提供了则替换旧的）")
    scope: Optional[str] = Field(None, description="权限范围（可选）")


class RevokeTokenRequest(BaseModel):
    """Token 撤销请求"""
    token: str = Field(..., description="要撤销的 Token（Access Token 或 Refresh Token）")
    token_type_hint: Optional[str] = Field(None, description="Token 类型提示：'access_token' 或 'refresh_token'")


class RevokeTokenResponse(BaseModel):
    """Token 撤销响应"""
    success: bool = Field(..., description="是否成功")
