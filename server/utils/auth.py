#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWT 简易鉴权工具（最小实现）
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt


ALGORITHM = "HS256"
security = HTTPBearer(auto_error=True)


def _get_secret() -> str:
    secret = os.getenv("JWT_SECRET") or "dev-secret-change-me"
    return secret


def create_access_token(data: Dict[str, Any], expires_minutes: int = 60) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, _get_secret(), algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的 Token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    payload = verify_token(token)
    # 简单返回 payload（包含 sub/role 等），生产可查询数据库
    return payload


