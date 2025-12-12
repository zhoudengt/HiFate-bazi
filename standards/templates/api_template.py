#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 模板文件

复制此文件并修改 {name}、{ClassName}、{description} 占位符
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

# from server.services.{name}_service import {ClassName}Service

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 数据模型 ====================

class TemplateRequest(BaseModel):
    """请求模型模板"""
    # 示例字段
    param1: str = Field(..., description="必填参数1")
    param2: Optional[str] = Field(None, description="可选参数2")
    param3: int = Field(default=10, ge=1, le=100, description="数值参数，范围1-100")


class TemplateResponse(BaseModel):
    """响应模型模板"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== API 路由 ====================

@router.post("/template/query", response_model=TemplateResponse, summary="模板查询接口")
async def query_template(request: TemplateRequest):
    """
    模板查询接口
    
    功能描述：
    - 这是一个模板接口
    - 用于演示标准的 API 结构
    
    Args:
        request: 请求参数
        
    Returns:
        TemplateResponse: 响应结果
        
    Raises:
        HTTPException: 当处理失败时抛出
    """
    try:
        # 1. 参数验证（Pydantic 已自动验证基本类型）
        # 可以添加额外的业务验证逻辑
        
        # 2. 调用服务层处理业务逻辑
        # service = TemplateService()
        # result = service.process(request.param1, request.param2)
        
        # 3. 返回成功响应
        result = {
            "param1": request.param1,
            "param2": request.param2,
            "param3": request.param3,
            "message": "处理成功"
        }
        return TemplateResponse(success=True, data=result)
        
    except ValueError as e:
        # 业务逻辑错误
        logger.warning(f"参数验证失败: {e}")
        return TemplateResponse(success=False, error=f"参数错误: {str(e)}")
        
    except Exception as e:
        # 未知错误
        logger.error(f"处理失败: {e}", exc_info=True)
        return TemplateResponse(success=False, error="服务器内部错误")


@router.get("/template/info", summary="模板信息接口")
async def get_template_info():
    """
    获取模板信息
    
    Returns:
        dict: 模板信息
    """
    return {
        "name": "API Template",
        "version": "1.0.0",
        "description": "这是一个 API 模板"
    }
