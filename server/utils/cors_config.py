#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一 CORS 配置模块

集中管理所有 CORS 相关配置，确保一致性和安全性。
"""

import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# ============================================================
# CORS 配置
# ============================================================

def get_allowed_origins() -> List[str]:
    """
    获取允许的 CORS 来源列表
    
    配置优先级：
    1. 环境变量 ALLOWED_ORIGINS（逗号分隔）
    2. 根据 APP_ENV 使用默认值
    
    Returns:
        List[str]: 允许的来源列表
    """
    # 从环境变量读取
    origins_str = os.getenv("ALLOWED_ORIGINS", "").strip()
    
    if origins_str:
        # 用户显式配置了 ALLOWED_ORIGINS
        origins = [o.strip() for o in origins_str.split(",") if o.strip()]
        logger.info(f"✓ CORS 来源从环境变量加载: {origins}")
        return origins
    
    # 根据环境使用默认值
    app_env = os.getenv("APP_ENV", "development").lower()
    
    if app_env == "production":
        # 生产环境：只允许已知的前端域名
        default_origins = [
            "https://www.yuanqistation.com",
            "https://yuanqistation.com",
            "https://api.yuanqistation.com",
            # 如果有其他生产域名，在此添加
        ]
        logger.info(f"✓ CORS 生产环境默认配置: {default_origins}")
        return default_origins
    else:
        # 开发/测试环境：允许所有来源（方便调试）
        logger.info("✓ CORS 开发环境配置: 允许所有来源 (*)")
        return ["*"]


def get_cors_config() -> Dict:
    """
    获取完整的 CORS 中间件配置
    
    Returns:
        Dict: 可直接传递给 CORSMiddleware 的配置字典
    """
    origins = get_allowed_origins()
    
    # 如果是 ["*"]，需要特殊处理
    is_allow_all = origins == ["*"]
    
    return {
        "allow_origins": origins,
        "allow_credentials": not is_allow_all,  # 当允许所有来源时，不能同时允许凭证
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Content-Type",
            "Authorization", 
            "X-API-Key",
            "X-Request-ID",
            "X-Grpc-Web",
            "X-User-Agent",
            "Accept",
            "X-Requested-With",
            "X-Client-Version",
            "grpc-timeout",
        ],
    }


def get_grpc_cors_origin() -> str:
    """
    获取 gRPC-Web CORS 的 Access-Control-Allow-Origin 值
    
    gRPC-Web 响应头需要单个字符串值，不能是列表。
    对于多域名场景，需要根据请求动态返回。
    
    Returns:
        str: CORS Origin 值
    """
    origins = get_allowed_origins()
    
    if origins == ["*"]:
        return "*"
    
    # 对于多域名，返回第一个（实际使用时需要根据请求动态判断）
    # 这是一个简化处理，完整实现需要在请求处理中动态返回
    return origins[0] if origins else "*"


def get_grpc_cors_headers(request_origin: str = None) -> Dict[str, str]:
    """
    获取 gRPC-Web 响应所需的 CORS 头
    
    Args:
        request_origin: 请求的 Origin 头（可选，用于动态 CORS）
    
    Returns:
        Dict[str, str]: CORS 响应头字典
    """
    origins = get_allowed_origins()
    
    # 确定响应的 Origin
    if origins == ["*"]:
        cors_origin = "*"
    elif request_origin and request_origin in origins:
        # 动态 CORS：如果请求来源在允许列表中，返回该来源
        cors_origin = request_origin
    elif origins:
        # 返回第一个允许的来源（回退）
        cors_origin = origins[0]
    else:
        cors_origin = "*"
    
    return {
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": (
            "Content-Type, X-Grpc-Web, X-User-Agent, Accept, Authorization, "
            "X-Requested-With, X-Client-Version, grpc-timeout, "
            "x-grpc-web, x-requested-with, content-type"
        ),
        "Access-Control-Expose-Headers": "grpc-status, grpc-message, grpc-encoding, grpc-accept-encoding",
        "Access-Control-Max-Age": "86400",
    }


# 在模块加载时输出配置信息（仅用于调试）
if os.getenv("DEBUG_CORS", "").lower() == "true":
    logger.setLevel(logging.DEBUG)
    logger.debug(f"CORS 配置已加载: origins={get_allowed_origins()}")
