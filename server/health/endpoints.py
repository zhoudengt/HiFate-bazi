#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""健康检查端点 - 从 server/main.py 提取"""

import os
import time
import json
import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

health_router = APIRouter()

@health_router.get("/")
async def root():
    """根路径"""
    return {
        "message": "HiFateAPI服务",
        "version": "1.0.0",
        "docs": "/docs"
    }


@health_router.get("/health")
async def health_check():
    """
    增强的健康检查接口
    检查系统资源和服务状态
    """
    import psutil
    import platform
    
    try:
        # 获取系统资源信息
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "system": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                }
            },
            "cache": {
                "status": "enabled"
            }
        }
        
        # 检查缓存状态
        try:
            from server.utils import bazi_cache
            health_data["cache"].update(bazi_cache.stats())
        except Exception as e:
            health_data["cache"]["status"] = f"error: {str(e)}"
        
        # 检查MySQL连接池状态
        try:
            from shared.config.database import get_connection_pool_stats
            health_data["mysql_pool"] = get_connection_pool_stats()
        except Exception as e:
            health_data["mysql_pool"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 如果资源使用过高，返回警告状态
        if cpu_percent > 90 or memory.percent > 90:
            health_data["status"] = "warning"
            health_data["message"] = "系统资源使用率较高"
        
        return health_data
        
    except ImportError:
        # psutil 未安装时返回基础健康检查
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "message": "基础健康检查（psutil未安装，无法获取详细系统信息）"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


# 健康检查别名（部署脚本使用）
@health_router.get("/api/v1/health")
async def health_check_api():
    """健康检查 API 别名"""
    return await health_check()


# 生产诊断：流式问题排查用，立即返回，不经过流式逻辑
@health_router.get("/api/v1/diagnose-stream")
async def diagnose_stream():
    """
    流式问题诊断端点：立即返回 JSON，用于区分「直连 8001 可达」与「经 Nginx 无响应」。
    不写业务逻辑，仅返回当前环境信息。
    """
    return {
        "ok": True,
        "endpoint": "diagnose-stream",
        "message": "stream diagnostic endpoint reachable",
        "timestamp": time.time(),
    }


@health_router.get("/metrics")
async def prometheus_metrics():
    """Prometheus 指标导出端点"""
    from fastapi.responses import PlainTextResponse
    try:
        from server.observability.metrics_collector import get_metrics
        metrics = get_metrics()
        return PlainTextResponse(
            content=metrics.export_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.warning(f"指标导出失败: {e}")
        return PlainTextResponse(content="# no metrics available\n", media_type="text/plain")

