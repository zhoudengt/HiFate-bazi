"""
API辅助函数 - 提取公共代码

提供统一的API响应格式、错误处理等公共功能
"""

import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


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
