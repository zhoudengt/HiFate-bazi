#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证相关 API
"""

from pydantic import BaseModel, Field
from fastapi import APIRouter
from typing import Optional
import jwt
import os
from datetime import datetime, timedelta

router = APIRouter()

# 简单的用户验证（开发环境）
VALID_USERS = {
    "admin": "admin123"
}

# JWT Secret（从环境变量读取，默认值仅用于开发）
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., description="用户名", example="admin")
    password: str = Field(..., description="密码", example="admin123")


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in_minutes: int = Field(default=1440, description="过期时间（分钟）")


@router.post("/auth/login", response_model=LoginResponse, summary="用户登录")
async def login(request: LoginRequest):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    
    返回 JWT Token
    """
    # 简单的用户名密码验证
    if request.username not in VALID_USERS:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if VALID_USERS[request.username] != request.password:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 生成 JWT Token
    payload = {
        "sub": request.username,
        "exp": datetime.utcnow() + timedelta(days=1),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=1440
    )

