#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一 API 响应模型

提供标准化的 API 响应格式，确保所有接口返回一致的结构。
"""

from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

# 泛型类型，用于支持不同的数据类型
T = TypeVar('T')


class BaseAPIResponse(BaseModel):
    """
    基础 API 响应模型
    
    所有 API 响应都应该继承此模型或使用 APIResponse。
    
    标准响应格式：
    {
        "success": true/false,
        "data": {...},           # 成功时返回数据
        "error": "错误信息",      # 失败时返回错误
        "message": "附加信息",    # 可选的附加信息
        "timestamp": "2026-02-04T12:00:00"
    }
    """
    success: bool = Field(..., description="请求是否成功")
    data: Optional[Any] = Field(default=None, description="响应数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    message: Optional[str] = Field(default=None, description="附加消息")
    timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="响应时间戳"
    )
    
    class Config:
        # 允许额外字段（向后兼容）
        extra = "allow"


class APIResponse(BaseAPIResponse):
    """
    标准 API 响应（推荐使用）
    
    使用示例：
    ```python
    # 成功响应
    return APIResponse.success(data={"user_id": 123})
    
    # 失败响应
    return APIResponse.fail(error="用户不存在", code=404)
    
    # 带消息的成功响应
    return APIResponse.success(data={...}, message="操作成功")
    ```
    """
    code: int = Field(default=200, description="状态码")
    
    @classmethod
    def success(
        cls,
        data: Any = None,
        message: Optional[str] = None,
        code: int = 200
    ) -> "APIResponse":
        """创建成功响应"""
        return cls(
            success=True,
            data=data,
            message=message,
            code=code
        )
    
    @classmethod
    def fail(
        cls,
        error: str,
        code: int = 400,
        data: Any = None,
        message: Optional[str] = None
    ) -> "APIResponse":
        """创建失败响应"""
        return cls(
            success=False,
            error=error,
            code=code,
            data=data,
            message=message
        )
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        code: int = 500,
        include_traceback: bool = False
    ) -> "APIResponse":
        """从异常创建响应"""
        error_msg = str(exception)
        if include_traceback:
            import traceback
            error_msg = f"{error_msg}\n{traceback.format_exc()}"
        return cls.fail(error=error_msg, code=code)


class PaginatedResponse(BaseAPIResponse):
    """
    分页响应模型
    
    用于返回分页数据的 API。
    """
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
    total_pages: int = Field(default=0, description="总页数")
    
    @classmethod
    def create(
        cls,
        data: list,
        total: int,
        page: int = 1,
        page_size: int = 20
    ) -> "PaginatedResponse":
        """创建分页响应"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            success=True,
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


# ==================== 向后兼容的响应工厂函数 ====================

def success_response(
    data: Any = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建成功响应（字典格式，向后兼容）
    
    Args:
        data: 响应数据
        message: 附加消息
    
    Returns:
        标准格式的响应字典
    """
    response = {
        "success": True,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    if message:
        response["message"] = message
    return response


def error_response(
    error: str,
    code: int = 400,
    data: Any = None
) -> Dict[str, Any]:
    """
    创建错误响应（字典格式，向后兼容）
    
    Args:
        error: 错误信息
        code: 错误码
        data: 附加数据（可选）
    
    Returns:
        标准格式的错误响应字典
    """
    response = {
        "success": False,
        "error": error,
        "code": code,
        "timestamp": datetime.now().isoformat()
    }
    if data is not None:
        response["data"] = data
    return response


# ==================== 特定业务响应模型（可继承使用） ====================

class BaziBaseResponse(BaseAPIResponse):
    """八字相关 API 的基础响应"""
    pass


class FortuneBaseResponse(BaseAPIResponse):
    """运势相关 API 的基础响应"""
    pass


class PaymentBaseResponse(BaseAPIResponse):
    """支付相关 API 的基础响应"""
    pass
