#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证服务配置
"""

import os
from typing import Optional

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# OAuth 2.0 配置
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "hifate_client")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "hifate_secret_change_me")
OAUTH_AUTHORIZATION_CODE_EXPIRE_MINUTES = int(os.getenv("OAUTH_AUTHORIZATION_CODE_EXPIRE_MINUTES", "10"))
OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
OAUTH_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("OAUTH_REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Token 存储键前缀
REDIS_KEY_PREFIX_ACCESS_TOKEN = "auth:access_token:"
REDIS_KEY_PREFIX_REFRESH_TOKEN = "auth:refresh_token:"
REDIS_KEY_PREFIX_AUTH_CODE = "auth:code:"
REDIS_KEY_PREFIX_TOKEN_INFO = "auth:token_info:"

# 服务端口
AUTH_SERVICE_PORT = int(os.getenv("AUTH_SERVICE_PORT", "9011"))
