"""
统一异常处理中间件

提供统一的异常处理机制，避免重复的错误处理代码
"""

import logging
import traceback
from typing import Callable, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 使用统一环境配置
from server.config.env_config import is_production

# 生产环境配置
PRODUCTION_MODE = is_production()  # 从统一环境配置读取
SHOW_DETAILED_ERRORS = not is_production()  # 生产环境不显示详细错误


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """异常处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            # FastAPI的HTTPException直接返回
            raise e
        except ValueError as e:
            # 参数验证错误
            logger.warning(f"参数验证错误: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": str(e),
                    "error_type": "validation_error"
                }
            )
        except Exception as e:
            # 其他未处理的异常
            error_trace = traceback.format_exc()
            logger.error(f"未处理的异常: {str(e)}\n{error_trace}")
            
            # 生产环境不暴露详细错误信息
            if PRODUCTION_MODE or not SHOW_DETAILED_ERRORS:
                error_detail = "服务器内部错误，请稍后重试"
            else:
                error_detail = f"错误: {str(e)}"
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": error_detail,
                    "error_type": "internal_error"
                }
            )


def safe_execute(func: Callable, *args, default_return=None, **kwargs):
    """
    安全执行函数，捕获异常并返回默认值
    
    Args:
        func: 要执行的函数
        *args: 位置参数
        default_return: 异常时的默认返回值
        **kwargs: 关键字参数
    
    Returns:
        函数执行结果或默认返回值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"函数执行失败: {func.__name__}: {e}")
        return default_return


def safe_get_nested(data: dict, *keys, default=None):
    """
    安全地获取嵌套字典中的值
    
    Args:
        data: 字典数据
        *keys: 键路径
        default: 默认值
    
    Returns:
        获取到的值或默认值
    """
    try:
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default
        return current
    except Exception as e:
        logger.debug(f"safe_get_nested 失败: {e}")
        return default
