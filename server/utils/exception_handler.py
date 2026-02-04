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
        except (BrokenPipeError, OSError) as e:
            # 客户端断开连接，这是正常情况，不需要记录为错误
            # 检查是否是 Broken pipe 错误（errno 32）
            if isinstance(e, BrokenPipeError) or (isinstance(e, OSError) and e.errno == 32):
                # 静默处理，不记录错误日志
                return JSONResponse(
                    status_code=200,  # 返回 200，因为这是客户端主动断开
                    content={
                        "success": False,
                        "error": "客户端连接已断开",
                        "error_type": "client_disconnected"
                    }
                )
            # 其他 OSError 继续抛出
            raise
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


# ==================== 自定义业务异常 ====================

class BusinessError(Exception):
    """
    业务异常基类
    
    用于表示业务逻辑错误，与系统错误区分开来。
    """
    def __init__(self, message: str, code: int = 400, error_type: str = "business_error"):
        self.message = message
        self.code = code
        self.error_type = error_type
        super().__init__(message)


class ValidationError(BusinessError):
    """参数验证错误"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        error_type = f"validation_error:{field}" if field else "validation_error"
        super().__init__(message, code=400, error_type=error_type)


class NotFoundError(BusinessError):
    """资源不存在错误"""
    def __init__(self, message: str = "资源不存在", resource: str = None):
        self.resource = resource
        super().__init__(message, code=404, error_type="not_found")


class AuthenticationError(BusinessError):
    """认证错误"""
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, code=401, error_type="authentication_error")


class AuthorizationError(BusinessError):
    """授权错误"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, code=403, error_type="authorization_error")


class ServiceUnavailableError(BusinessError):
    """服务不可用错误"""
    def __init__(self, message: str = "服务暂时不可用", service: str = None):
        self.service = service
        super().__init__(message, code=503, error_type="service_unavailable")


class RateLimitError(BusinessError):
    """请求频率限制错误"""
    def __init__(self, message: str = "请求过于频繁，请稍后重试"):
        super().__init__(message, code=429, error_type="rate_limit_exceeded")


# ==================== API 错误处理装饰器 ====================

import functools
from typing import Optional, Type, Tuple

def api_error_handler(
    func: Callable = None,
    *,
    catch: Tuple[Type[Exception], ...] = (Exception,),
    default_error: str = "服务器内部错误",
    log_errors: bool = True
):
    """
    API 错误处理装饰器
    
    用于统一处理 API 端点的异常。
    
    使用示例：
    ```python
    @router.post("/api/endpoint")
    @api_error_handler
    async def my_endpoint():
        ...
    
    # 或者指定捕获的异常类型
    @router.post("/api/endpoint")
    @api_error_handler(catch=(ValueError, KeyError), default_error="参数错误")
    async def my_endpoint():
        ...
    ```
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except BusinessError as e:
                # 业务异常，返回标准错误响应
                if log_errors:
                    logger.warning(f"业务异常 [{fn.__name__}]: {e.message}")
                return JSONResponse(
                    status_code=e.code,
                    content={
                        "success": False,
                        "error": e.message,
                        "error_type": e.error_type
                    }
                )
            except HTTPException:
                # FastAPI 的 HTTPException 直接抛出
                raise
            except catch as e:
                # 其他捕获的异常
                if log_errors:
                    logger.error(f"API 错误 [{fn.__name__}]: {e}", exc_info=True)
                
                error_msg = default_error if PRODUCTION_MODE else str(e)
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": error_msg,
                        "error_type": "internal_error"
                    }
                )
        
        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except BusinessError as e:
                if log_errors:
                    logger.warning(f"业务异常 [{fn.__name__}]: {e.message}")
                return JSONResponse(
                    status_code=e.code,
                    content={
                        "success": False,
                        "error": e.message,
                        "error_type": e.error_type
                    }
                )
            except HTTPException:
                raise
            except catch as e:
                if log_errors:
                    logger.error(f"API 错误 [{fn.__name__}]: {e}", exc_info=True)
                
                error_msg = default_error if PRODUCTION_MODE else str(e)
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": error_msg,
                        "error_type": "internal_error"
                    }
                )
        
        import asyncio
        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper
    
    # 支持 @api_error_handler 和 @api_error_handler(...) 两种用法
    if func is not None:
        return decorator(func)
    return decorator
