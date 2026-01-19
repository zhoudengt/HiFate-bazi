"""
API辅助函数 - 提取公共代码

提供统一的API响应格式、错误处理等公共功能
"""

import logging
import functools
from typing import Any, Dict, Optional, Callable, TypeVar, Union
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# 定义函数类型泛型
F = TypeVar('F', bound=Callable[..., Any])


def create_success_response(data: Any = None, message: Optional[str] = None) -> Dict[str, Any]:
    """
    创建成功响应
    
    Args:
        data: 响应数据
        message: 响应消息
    
    Returns:
        标准化的成功响应
    """
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    return response


def create_error_response(
    error: str,
    error_type: Optional[str] = None,
    status_code: int = 500
) -> Dict[str, Any]:
    """
    创建错误响应
    
    Args:
        error: 错误消息
        error_type: 错误类型
        status_code: HTTP状态码
    
    Returns:
        标准化的错误响应
    """
    response = {
        "success": False,
        "error": error
    }
    if error_type:
        response["error_type"] = error_type
    return response


def handle_api_exception(e: Exception, default_message: str = "操作失败") -> HTTPException:
    """
    统一处理API异常
    
    Args:
        e: 异常对象
        default_message: 默认错误消息
    
    Returns:
        HTTPException
    """
    if isinstance(e, HTTPException):
        return e
    
    if isinstance(e, ValueError):
        logger.warning(f"参数验证错误: {str(e)}")
        return HTTPException(status_code=400, detail=str(e))
    
    # 其他异常
    logger.error(f"未处理的异常: {str(e)}", exc_info=True)
    return HTTPException(status_code=500, detail=default_message)


def validate_bazi_request(solar_date: str, solar_time: str, gender: str) -> None:
    """
    验证八字请求参数
    
    Args:
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
    
    Raises:
        ValueError: 参数验证失败
    """
    from datetime import datetime
    
    # 验证日期格式
    try:
        datetime.strptime(solar_date, '%Y-%m-%d')
    except ValueError:
        raise ValueError('日期格式错误，应为 YYYY-MM-DD')
    
    # 验证时间格式
    try:
        datetime.strptime(solar_time, '%H:%M')
    except ValueError:
        raise ValueError('时间格式错误，应为 HH:MM')
    
    # 验证性别
    if gender not in ['male', 'female']:
        raise ValueError('性别必须为 male 或 female')


def api_error_handler(func: F) -> F:
    """
    API异常处理装饰器
    
    统一捕获异常并返回标准错误响应
    
    使用示例：
        @api_error_handler
        async def my_api_endpoint(request: MyRequest):
            # 业务逻辑
            return MyResponse(success=True, data=result)
    
    注意：
        - 如果函数返回的是 Response 对象（如 StreamingResponse），装饰器不会处理
        - 如果函数返回的是 Pydantic 模型，装饰器会将其转换为字典
        - 如果函数抛出 HTTPException，装饰器会直接抛出（不捕获）
        - 其他异常会被捕获并返回标准错误响应
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            
            # 如果返回的是 Response 对象（如 StreamingResponse），直接返回
            if isinstance(result, (JSONResponse,)):
                return result
            
            # 如果返回的是 Pydantic 模型，转换为字典
            if hasattr(result, 'model_dump'):
                return result.model_dump(exclude_none=True)
            elif hasattr(result, 'dict'):
                return result.dict(exclude_none=True)
            
            return result
            
        except HTTPException:
            # HTTPException 直接抛出，由 FastAPI 处理
            raise
        except ValueError as e:
            # 参数验证错误
            logger.warning(f"参数验证错误 [{func.__name__}]: {str(e)}")
            return create_error_response(
                error=str(e),
                error_type="validation_error"
            )
        except Exception as e:
            # 其他未处理的异常
            logger.error(f"未处理的异常 [{func.__name__}]: {str(e)}", exc_info=True)
            return create_error_response(
                error="服务器内部错误，请稍后重试",
                error_type="internal_error"
            )
    
    return wrapper  # type: ignore


def api_error_handler(func: F) -> F:
    """
    API异常处理装饰器
    
    自动捕获异常并返回标准错误响应，减少重复的异常处理代码
    
    使用示例：
        @router.post("/api/endpoint")
        @api_error_handler
        async def my_endpoint(request: MyRequest):
            # 业务逻辑
            return MyResponse(success=True, data=result)
    
    功能：
    1. 自动捕获所有异常
    2. 记录错误日志
    3. 返回标准错误响应格式
    4. 保留HTTPException的原始行为
    
    Args:
        func: 被装饰的API端点函数
    
    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 执行原始函数
            result = await func(*args, **kwargs)
            return result
        except HTTPException:
            # FastAPI的HTTPException直接抛出，保持原有行为
            raise
        except ValueError as e:
            # 参数验证错误
            logger.warning(f"参数验证错误 [{func.__name__}]: {str(e)}")
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    error=str(e),
                    error_type="validation_error"
                )
            )
        except Exception as e:
            # 其他未处理的异常
            logger.error(
                f"未处理的异常 [{func.__name__}]: {str(e)}",
                exc_info=True
            )
            return JSONResponse(
                status_code=500,
                content=create_error_response(
                    error="服务器内部错误，请稍后重试",
                    error_type="internal_error"
                )
            )
    
    return wrapper  # type: ignore
