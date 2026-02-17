# -*- coding: utf-8 -*-
"""
首页内容 gRPC-Web 端点处理器
"""

from typing import Any, Dict

from fastapi import HTTPException

from server.api.grpc_gateway.endpoints import _register


@_register("/homepage/contents")
async def _handle_homepage_contents(payload: Dict[str, Any]):
    """获取首页内容列表（gRPC-Web 转发）"""
    from server.api.v1.homepage_content import get_homepage_contents
    enabled_only = payload.get("enabled_only", True)
    return await get_homepage_contents(enabled_only=enabled_only)


@_register("/homepage/contents/detail")
async def _handle_homepage_content_detail(payload: Dict[str, Any]):
    """获取首页内容详情（gRPC-Web 转发）"""
    from server.api.v1.homepage_content import get_homepage_content_detail
    content_id = payload.get("id")
    if not content_id:
        raise HTTPException(status_code=400, detail="缺少内容ID")
    return await get_homepage_content_detail(int(content_id))


@_register("/admin/homepage/contents")
async def _handle_create_homepage_content(payload: Dict[str, Any]):
    """创建首页内容（gRPC-Web 转发）"""
    from server.api.v1.homepage_content import create_homepage_content, HomepageContentRequest
    request = HomepageContentRequest(**payload)
    return await create_homepage_content(request)


@_register("/admin/homepage/contents/update")
async def _handle_update_homepage_content(payload: Dict[str, Any]):
    """更新首页内容（gRPC-Web 转发）"""
    from server.api.v1.homepage_content import update_homepage_content, HomepageContentUpdateRequest
    content_id = payload.get("id")
    if not content_id:
        raise HTTPException(status_code=400, detail="缺少内容ID")
    update_data = {k: v for k, v in payload.items() if k != "id"}
    request = HomepageContentUpdateRequest(**update_data)
    return await update_homepage_content(int(content_id), request)


@_register("/admin/homepage/contents/delete")
async def _handle_delete_homepage_content(payload: Dict[str, Any]):
    """删除首页内容（gRPC-Web 转发）"""
    from server.api.v1.homepage_content import delete_homepage_content
    content_id = payload.get("id")
    if not content_id:
        raise HTTPException(status_code=400, detail="缺少内容ID")
    hard_delete = payload.get("hard_delete", False)
    return await delete_homepage_content(int(content_id), hard_delete=hard_delete)


@_register("/admin/homepage/contents/sort")
async def _handle_update_content_sort(payload: Dict[str, Any]):
    """更新内容排序（gRPC-Web 转发）"""
    from server.api.v1.homepage_content import update_content_sort_order, SortOrderRequest
    content_id = payload.get("id")
    sort_order = payload.get("sort_order")
    if not content_id or sort_order is None:
        raise HTTPException(status_code=400, detail="缺少内容ID或排序值")
    request = SortOrderRequest(sort_order=int(sort_order))
    return await update_content_sort_order(int(content_id), request)
