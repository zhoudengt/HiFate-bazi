#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proto 文件服务 API
- 提供前端需要的 proto 文件
- 支持白名单控制（只暴露 frontend_gateway.proto）
- 支持版本管理
- 防止路径遍历攻击

注意：此服务提供静态文件内容，路径参数端点（/proto/{filename}）不适合通过 gRPC-Web 访问。
文件列表端点（/proto/list）已在 grpc_gateway.py 中注册为 /proto/list。
"""

import os
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, Response, JSONResponse
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PROTO_DIR = os.path.join(PROJECT_ROOT, 'proto')

# 允许前端访问的 proto 文件白名单（只暴露必要的文件）
ALLOWED_PROTO_FILES = {
    'frontend_gateway.proto',  # 前端网关协议（必须）
    # 不暴露内部微服务协议，确保安全性
}

# 文件 MIME 类型
PROTO_MIME_TYPE = "application/x-protobuf"


# 使用完全不同的路径避免与 /proto/{filename} 冲突
@router.get("/proto-files")
async def list_proto_files():
    """
    列出可用的 proto 文件（仅返回白名单中的文件）
    
    Returns:
        JSON 格式的文件列表
    """
    available_files = []
    
    for filename in ALLOWED_PROTO_FILES:
        proto_path = os.path.join(PROTO_DIR, filename)
        if os.path.exists(proto_path) and os.path.isfile(proto_path):
            # 获取文件信息
            stat = os.stat(proto_path)
            available_files.append({
                "filename": filename,
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
    
    return JSONResponse(
        content={
            "success": True,
            "files": available_files,
            "count": len(available_files)
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
        }
    )


@router.get("/proto/{filename}")
async def get_proto_file(
    filename: str,
    request: Request,
    version: Optional[str] = Query(None, description="协议版本（可选）")
):
    """
    获取 proto 文件（仅限白名单）
    
    Args:
        filename: proto 文件名（如 frontend_gateway.proto）
        version: 协议版本（可选，用于版本管理）
        request: FastAPI Request 对象（用于获取客户端IP）
    
    Returns:
        proto 文件内容（text/plain 格式）
    
    Raises:
        HTTPException: 文件不在白名单或不存在
    """
    # 获取客户端IP（用于日志记录）
    client_ip = None
    if request:
        client_ip = request.client.host if request.client else "unknown"
    
    # 1. 防止路径遍历攻击（确保文件名不包含路径分隔符）- 优先检查
    if '/' in filename or '\\' in filename or '..' in filename:
        logger.warning(f"检测到路径遍历攻击: {filename} (IP: {client_ip})")
        raise HTTPException(
            status_code=400,
            detail="文件名格式错误"
        )
    
    # 2. 安全检查：验证文件名是否在白名单中
    if filename not in ALLOWED_PROTO_FILES:
        logger.warning(f"禁止访问 proto 文件: {filename} (不在白名单中, IP: {client_ip})")
        raise HTTPException(
            status_code=403,
            detail=f"禁止访问此 proto 文件: {filename}"
        )
    
    # 3. 构建文件路径
    proto_path = os.path.join(PROTO_DIR, filename)
    
    # 4. 验证文件是否存在
    if not os.path.exists(proto_path):
        logger.warning(f"proto 文件不存在: {proto_path} (IP: {client_ip})")
        raise HTTPException(
            status_code=404,
            detail=f"proto 文件不存在: {filename}"
        )
    
    # 5. 验证是否为文件（防止目录遍历）
    if not os.path.isfile(proto_path):
        logger.warning(f"路径不是文件: {proto_path} (IP: {client_ip})")
        raise HTTPException(
            status_code=400,
            detail="路径不是文件"
        )
    
    # 6. 读取文件内容
    try:
        with open(proto_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 记录访问日志（用于安全审计）
        logger.info(f"proto 文件访问: {filename} (version: {version}, IP: {client_ip})")
        
        # 7. 返回文件内容
        return PlainTextResponse(
            content=content,
            media_type=PROTO_MIME_TYPE,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Access-Control-Allow-Origin": "*",  # 允许跨域（前端需要）
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Cache-Control": "public, max-age=3600",  # 缓存1小时
                "X-Content-Type-Options": "nosniff",
            }
        )
    except Exception as e:
        logger.error(f"读取 proto 文件失败: {proto_path}, 错误: {e} (IP: {client_ip})", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="读取文件失败"
        )


@router.options("/proto/{filename}")
async def options_proto_file(filename: str):
    """
    CORS 预检请求处理
    """
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
    )


@router.options("/proto-files")
async def options_proto_list():
    """
    CORS 预检请求处理（文件列表）
    """
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
    )
