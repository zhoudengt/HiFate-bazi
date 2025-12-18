#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全监控 API
用途：提供安全监控数据的查询接口

功能：
1. 获取安全事件统计
2. 获取封禁 IP 列表
3. 解封 IP
4. 获取安全事件详情
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from server.observability.security_monitor import get_security_monitor, SecurityEventType

router = APIRouter()


class SecurityStatsResponse(BaseModel):
    """安全统计响应"""
    total_events: int = Field(..., description="总事件数")
    events_by_type: Dict[str, int] = Field(..., description="按类型统计")
    events_by_severity: Dict[str, int] = Field(..., description="按严重程度统计")
    blocked_ips_count: int = Field(..., description="封禁 IP 数量")
    blocked_ips: List[str] = Field(..., description="封禁 IP 列表")


class UnblockIPRequest(BaseModel):
    """解封 IP 请求"""
    ip: str = Field(..., description="要解封的 IP 地址")


@router.get("/security/stats", response_model=SecurityStatsResponse)
async def get_security_stats():
    """获取安全统计信息"""
    try:
        monitor = get_security_monitor()
        stats = monitor.get_stats()
        return SecurityStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取安全统计失败: {str(e)}")


@router.get("/security/blocked-ips")
async def get_blocked_ips():
    """获取封禁 IP 列表"""
    try:
        monitor = get_security_monitor()
        stats = monitor.get_stats()
        return {
            "blocked_ips": stats.get('blocked_ips', []),
            "count": len(stats.get('blocked_ips', []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取封禁 IP 列表失败: {str(e)}")


@router.post("/security/unblock-ip")
async def unblock_ip(request: UnblockIPRequest):
    """解封 IP"""
    try:
        monitor = get_security_monitor()
        monitor.unblock_ip(request.ip)
        return {"success": True, "message": f"IP {request.ip} 已解封"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解封 IP 失败: {str(e)}")


@router.get("/security/check-ip/{ip}")
async def check_ip_status(ip: str):
    """检查 IP 状态"""
    try:
        monitor = get_security_monitor()
        is_blocked = monitor.is_ip_blocked(ip)
        return {
            "ip": ip,
            "blocked": is_blocked,
            "status": "blocked" if is_blocked else "allowed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查 IP 状态失败: {str(e)}")

