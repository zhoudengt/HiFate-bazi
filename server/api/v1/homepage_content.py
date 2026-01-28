#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页内容管理API接口
提供首页图片与文字内容的查询和管理功能
"""

import sys
import os
import logging
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.db.homepage_content_dao import HomepageContentDAO

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 数据模型 ====================

class HomepageContentItem(BaseModel):
    """首页内容项"""
    id: int = Field(..., description="内容ID")
    title: str = Field(..., description="标题")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    description: str = Field(..., description="详细描述")
    image_url: Optional[str] = Field(None, description="图片OSS地址")
    sort_order: int = Field(0, description="排序字段")
    enabled: bool = Field(True, description="是否启用")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")


class HomepageContentResponse(BaseModel):
    """首页内容查询响应"""
    success: bool = Field(..., description="是否成功")
    data: List[HomepageContentItem] = Field(default_factory=list, description="内容列表")
    error: Optional[str] = Field(None, description="错误信息")


class HomepageContentDetailResponse(BaseModel):
    """首页内容详情响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[HomepageContentItem] = Field(None, description="内容详情")
    error: Optional[str] = Field(None, description="错误信息")


class HomepageContentRequest(BaseModel):
    """创建/更新首页内容请求"""
    title: str = Field(..., description="标题", min_length=1, max_length=200)
    tags: List[str] = Field(default_factory=list, description="标签列表")
    description: str = Field(..., description="详细描述")
    image_url: str = Field(..., description="图片OSS地址（如：https://destiny-ducket.oss-cn-hongkong.aliyuncs.com/xxx.jpeg）")
    sort_order: int = Field(0, description="排序字段（数字越小越靠前）")
    
    @validator('image_url')
    def validate_image_url(cls, v):
        """验证OSS URL格式"""
        if not v:
            raise ValueError('图片地址不能为空')
        # 验证是否为有效的HTTP/HTTPS URL
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if not url_pattern.match(v):
            raise ValueError('图片地址格式不正确，必须是有效的HTTP/HTTPS URL')
        return v


class SortOrderRequest(BaseModel):
    """更新排序请求"""
    sort_order: int = Field(..., description="排序字段（数字越小越靠前）")


class HomepageContentUpdateRequest(BaseModel):
    """更新首页内容请求（所有字段可选）"""
    title: Optional[str] = Field(None, description="标题", min_length=1, max_length=200)
    tags: Optional[List[str]] = Field(None, description="标签列表")
    description: Optional[str] = Field(None, description="详细描述")
    image_url: Optional[str] = Field(None, description="图片OSS地址（如：https://destiny-ducket.oss-cn-hongkong.aliyuncs.com/xxx.jpeg）")
    sort_order: Optional[int] = Field(None, description="排序字段")
    enabled: Optional[bool] = Field(None, description="是否启用")
    
    @validator('image_url')
    def validate_image_url(cls, v):
        """验证OSS URL格式（可选字段）"""
        if v is None:
            return v
        # 验证是否为有效的HTTP/HTTPS URL
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if not url_pattern.match(v):
            raise ValueError('图片地址格式不正确，必须是有效的HTTP/HTTPS URL')
        return v


# ==================== 查询接口（前端调用） ====================

@router.get("/homepage/contents", response_model=HomepageContentResponse, summary="获取首页内容列表")
async def get_homepage_contents(enabled_only: bool = True):
    """
    获取首页内容列表
    
    返回所有启用的首页内容，按sort_order排序
    
    - **enabled_only**: 是否只返回启用的内容（默认True）
    
    返回格式：
    ```json
    {
      "success": true,
      "data": [
        {
          "id": 1,
          "title": "AI守护神",
          "tags": ["科技", "精准"],
          "description": "详细描述...",
          "image_url": "https://destiny-ducket.oss-cn-hongkong.aliyuncs.com/xxx.jpeg",
          "sort_order": 1,
          "enabled": true
        }
      ]
    }
    ```
    """
    try:
        contents = HomepageContentDAO.get_all_contents(enabled_only=enabled_only)
        
        # 转换为响应模型
        content_items = []
        for content in contents:
            # 处理时间字段
            created_at = content.get('created_at')
            updated_at = content.get('updated_at')
            
            if created_at:
                created_at = str(created_at)
            if updated_at:
                updated_at = str(updated_at)
            
            content_items.append(HomepageContentItem(
                id=content['id'],
                title=content['title'],
                tags=content.get('tags', []),
                description=content.get('description', ''),
                image_url=content.get('image_url', ''),
                sort_order=content.get('sort_order', 0),
                enabled=bool(content.get('enabled', True)),
                created_at=created_at,
                updated_at=updated_at
            ))
        
        return HomepageContentResponse(
            success=True,
            data=content_items
        )
    except Exception as e:
        logger.error(f"获取首页内容列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取首页内容列表失败: {str(e)}"
        )


@router.get("/homepage/contents/{content_id}", response_model=HomepageContentDetailResponse, summary="获取首页内容详情")
async def get_homepage_content_detail(content_id: int):
    """
    获取单个首页内容详情
    
    - **content_id**: 内容ID
    """
    try:
        content = HomepageContentDAO.get_content_by_id(content_id)
        
        if not content:
            raise HTTPException(status_code=404, detail=f"内容ID {content_id} 不存在")
        
        # 处理时间字段
        created_at = content.get('created_at')
        updated_at = content.get('updated_at')
        
        if created_at:
            created_at = str(created_at)
        if updated_at:
            updated_at = str(updated_at)
        
        content_item = HomepageContentItem(
            id=content['id'],
            title=content['title'],
            tags=content.get('tags', []),
            description=content.get('description', ''),
            image_url=content.get('image_url', ''),
            sort_order=content.get('sort_order', 0),
            enabled=bool(content.get('enabled', True)),
            created_at=created_at,
            updated_at=updated_at
        )
        
        return HomepageContentDetailResponse(
            success=True,
            data=content_item
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取首页内容详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取首页内容详情失败: {str(e)}"
        )


# ==================== 管理接口（管理员使用） ====================

@router.post("/admin/homepage/contents", summary="创建首页内容")
async def create_homepage_content(request: HomepageContentRequest):
    """
    创建新的首页内容
    
    - **title**: 标题
    - **tags**: 标签列表
    - **description**: 详细描述
    - **image_url**: 图片OSS地址（如：https://destiny-ducket.oss-cn-hongkong.aliyuncs.com/xxx.jpeg）
    - **sort_order**: 排序字段
    """
    try:
        content_id = HomepageContentDAO.create_content(
            title=request.title,
            tags=request.tags,
            description=request.description,
            image_url=request.image_url,
            sort_order=request.sort_order
        )
        
        if not content_id:
            raise HTTPException(status_code=500, detail="创建内容失败")
        
        return {
            "success": True,
            "message": "内容创建成功",
            "data": {
                "id": content_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建首页内容失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"创建首页内容失败: {str(e)}"
        )


@router.put("/admin/homepage/contents/{content_id}", summary="更新首页内容")
async def update_homepage_content(content_id: int, request: HomepageContentUpdateRequest):
    """
    更新首页内容
    
    - **content_id**: 内容ID
    - 所有字段都是可选的，只更新提供的字段
    """
    try:
        # 检查内容是否存在
        existing = HomepageContentDAO.get_content_by_id(content_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"内容ID {content_id} 不存在")
        
        # 更新内容
        success = HomepageContentDAO.update_content(
            content_id=content_id,
            title=request.title,
            tags=request.tags,
            description=request.description,
            image_url=request.image_url,
            sort_order=request.sort_order,
            enabled=request.enabled
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="更新内容失败")
        
        return {
            "success": True,
            "message": "内容更新成功",
            "data": {
                "id": content_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新首页内容失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新首页内容失败: {str(e)}"
        )


@router.delete("/admin/homepage/contents/{content_id}", summary="删除首页内容")
async def delete_homepage_content(content_id: int, hard_delete: bool = False):
    """
    删除首页内容（默认软删除）
    
    - **content_id**: 内容ID
    - **hard_delete**: 是否硬删除（物理删除），默认False（软删除）
    """
    try:
        # 检查内容是否存在
        existing = HomepageContentDAO.get_content_by_id(content_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"内容ID {content_id} 不存在")
        
        success = HomepageContentDAO.delete_content(content_id, hard_delete=hard_delete)
        
        if not success:
            raise HTTPException(status_code=500, detail="删除内容失败")
        
        return {
            "success": True,
            "message": "内容删除成功" if hard_delete else "内容已禁用（软删除）",
            "data": {
                "id": content_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除首页内容失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"删除首页内容失败: {str(e)}"
        )


@router.put("/admin/homepage/contents/{content_id}/sort", summary="更新内容排序")
async def update_content_sort_order(content_id: int, request: SortOrderRequest):
    """
    更新内容排序
    
    - **content_id**: 内容ID
    - **sort_order**: 新的排序值（数字越小越靠前）
    """
    try:
        # 检查内容是否存在
        existing = HomepageContentDAO.get_content_by_id(content_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"内容ID {content_id} 不存在")
        
        success = HomepageContentDAO.update_sort_order(content_id, request.sort_order)
        
        if not success:
            raise HTTPException(status_code=500, detail="更新排序失败")
        
        return {
            "success": True,
            "message": "排序更新成功",
            "data": {
                "id": content_id,
                "sort_order": request.sort_order
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新排序失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新排序失败: {str(e)}"
        )
