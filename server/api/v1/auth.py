#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简易鉴权接口：
- /auth/login: 以预共享账号登录，返回 JWT 和 OAuth Token
环境变量：
- ADMIN_USERNAME（默认 admin）
- ADMIN_PASSWORD（默认 admin123）
- JWT_EXPIRE_MINUTES（默认 60）
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from server.utils.auth import create_access_token

# 尝试导入认证客户端（可选）
try:
    from src.clients.auth_client_grpc import get_auth_client
    AUTH_CLIENT_AVAILABLE = True
except ImportError:
    AUTH_CLIENT_AVAILABLE = False

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


@router.post("/auth/login")
async def login(req: LoginRequest):
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    if req.username != admin_user or req.password != admin_pass:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    
    # 创建 JWT Token（向后兼容）
    jwt_token = create_access_token({"sub": req.username, "role": "admin"}, expires_minutes=minutes)
    
    # 尝试创建 OAuth Token（用于认证服务验证）
    oauth_token = None
    if AUTH_CLIENT_AVAILABLE:
        try:
            auth_client = get_auth_client()
            # 使用默认的客户端 ID 和 Secret（从环境变量读取）
            from services.auth_service.config import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET
            result = auth_client.create_token(
                user_id=req.username,
                client_id=OAUTH_CLIENT_ID,
                scope=["read", "write"],
                access_token_expires_in=minutes * 60,
                refresh_token_expires_in=30 * 24 * 60 * 60  # 30天
            )
            if result.get("success"):
                oauth_token = result.get("access_token")
        except Exception as e:
            # 如果创建 OAuth Token 失败，只返回 JWT Token（降级）
            print(f"⚠️  创建 OAuth Token 失败: {e}，仅返回 JWT Token", flush=True)
    
    # 优先返回 OAuth Token（如果可用），否则返回 JWT Token
    access_token = oauth_token if oauth_token else jwt_token
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in_minutes": minutes,
        "jwt_token": jwt_token,  # 保留 JWT Token 用于向后兼容
        "oauth_token": oauth_token  # OAuth Token（如果创建成功）
    }


