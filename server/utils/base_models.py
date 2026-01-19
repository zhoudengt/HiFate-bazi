#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础API响应模型

提供统一的API响应格式，减少重复代码
"""

from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')


class BaseAPIResponse(BaseModel, Generic[T]):
    """
    基础API响应模型
    
    所有API响应都应该继承此模型，确保统一的响应格式
    
    使用示例：
        class MyResponse(BaseAPIResponse[dict]):
            custom_field: Optional[str] = None
    """
    success: bool = Field(..., description="是否成功")
    data: Optional[T] = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")
    message: Optional[str] = Field(None, description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {},
                "error": None,
                "message": "操作成功"
            }
        }


class BaseAPIResponseDict(BaseAPIResponse[dict]):
    """
    字典类型的基础响应模型（向后兼容）
    
    用于需要返回字典数据的API
    """
    pass
