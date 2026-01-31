#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的 API 错误处理装饰器（向后兼容）
"""

from functools import wraps
import logging
import traceback

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def api_error_handler(func):
    """统一的 API 错误处理装饰器（向后兼容）"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error("API error: %s\n%s", e, error_trace)
            raise HTTPException(
                status_code=500,
                detail=f"计算失败: {str(e)}\n{error_trace}",
            ) from e

    return wrapper
