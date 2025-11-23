#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简易鉴权接口：
- /auth/login: 以预共享账号登录，返回 JWT（演示用途）
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
    token = create_access_token({"sub": req.username, "role": "admin"}, expires_minutes=minutes)
    return {"access_token": token, "token_type": "bearer", "expires_in_minutes": minutes}


