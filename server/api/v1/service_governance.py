#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务治理 API

提供：
- 服务注册中心状态
- 熔断器状态
- 限流器状态
- 健康检查状态
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from server.core.service_registry import ServiceRegistry, get_registry
from server.core.circuit_breaker import get_all_breakers, get_breaker_stats, CircuitBreaker
from server.core.rate_limiter import get_all_limiters, get_limiter_stats
from server.core.health_checker import get_health_checker, HealthChecker

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 数据模型 ====================

class ServiceStatusResponse(BaseModel):
    """服务状态响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="状态数据")
    error: Optional[str] = Field(None, description="错误信息")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="健康状态")
    services: Dict[str, Any] = Field(default_factory=dict, description="服务状态")
    timestamp: float = Field(..., description="检查时间")


# ==================== 服务注册中心 API ====================

@router.get("/governance/registry", response_model=ServiceStatusResponse, summary="获取服务注册中心状态")
async def get_registry_status():
    """
    获取服务注册中心状态
    
    返回所有已注册服务的信息和状态
    """
    try:
        registry = get_registry()
        registry.initialize()
        stats = registry.get_stats()
        
        return ServiceStatusResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        logger.error(f"获取注册中心状态失败: {e}", exc_info=True)
        return ServiceStatusResponse(
            success=False,
            error=str(e)
        )


@router.get("/governance/registry/{service_name}", response_model=ServiceStatusResponse, summary="获取单个服务状态")
async def get_service_status(service_name: str):
    """
    获取单个服务的状态
    
    Args:
        service_name: 服务名称
    """
    try:
        registry = get_registry()
        registry.initialize()
        
        service = registry.discover(service_name)
        if not service:
            return ServiceStatusResponse(
                success=False,
                error=f"Service {service_name} not found"
            )
        
        return ServiceStatusResponse(
            success=True,
            data={
                "name": service.name,
                "address": service.address,
                "status": service.status.value,
                "version": service.version,
                "metadata": service.metadata
            }
        )
    except Exception as e:
        logger.error(f"获取服务状态失败: {e}", exc_info=True)
        return ServiceStatusResponse(
            success=False,
            error=str(e)
        )


# ==================== 熔断器 API ====================

@router.get("/governance/circuit-breakers", response_model=ServiceStatusResponse, summary="获取所有熔断器状态")
async def get_circuit_breakers_status():
    """
    获取所有熔断器的状态
    
    返回每个熔断器的状态、统计信息
    """
    try:
        stats = get_breaker_stats()
        
        return ServiceStatusResponse(
            success=True,
            data={
                "total": len(stats),
                "breakers": stats
            }
        )
    except Exception as e:
        logger.error(f"获取熔断器状态失败: {e}", exc_info=True)
        return ServiceStatusResponse(
            success=False,
            error=str(e)
        )


@router.post("/governance/circuit-breakers/{name}/reset", response_model=ServiceStatusResponse, summary="重置熔断器")
async def reset_circuit_breaker(name: str):
    """
    重置指定的熔断器
    
    Args:
        name: 熔断器名称
    """
    try:
        breakers = get_all_breakers()
        if name not in breakers:
            return ServiceStatusResponse(
                success=False,
                error=f"Circuit breaker {name} not found"
            )
        
        breakers[name].reset()
        
        return ServiceStatusResponse(
            success=True,
            data={"message": f"Circuit breaker {name} has been reset"}
        )
    except Exception as e:
        logger.error(f"重置熔断器失败: {e}", exc_info=True)
        return ServiceStatusResponse(
            success=False,
            error=str(e)
        )


# ==================== 限流器 API ====================

@router.get("/governance/rate-limiters", response_model=ServiceStatusResponse, summary="获取所有限流器状态")
async def get_rate_limiters_status():
    """
    获取所有限流器的状态
    
    返回每个限流器的配置和统计信息
    """
    try:
        stats = get_limiter_stats()
        
        return ServiceStatusResponse(
            success=True,
            data={
                "total": len(stats),
                "limiters": stats
            }
        )
    except Exception as e:
        logger.error(f"获取限流器状态失败: {e}", exc_info=True)
        return ServiceStatusResponse(
            success=False,
            error=str(e)
        )


# ==================== 健康检查 API ====================

@router.get("/governance/health", response_model=ServiceStatusResponse, summary="获取整体健康状态")
async def get_overall_health():
    """
    获取整体系统健康状态
    
    返回所有服务的健康检查结果
    """
    try:
        checker = get_health_checker()
        stats = checker.get_stats()
        
        # 判断整体状态
        if stats["unhealthy"] == 0:
            overall_status = "healthy"
        elif stats["healthy"] == 0:
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
        
        return ServiceStatusResponse(
            success=True,
            data={
                "status": overall_status,
                **stats
            }
        )
    except Exception as e:
        logger.error(f"获取健康状态失败: {e}", exc_info=True)
        return ServiceStatusResponse(
            success=False,
            error=str(e)
        )


@router.get("/governance/health/{service_name}", response_model=ServiceStatusResponse, summary="获取单个服务健康状态")
async def get_service_health(service_name: str):
    """
    获取单个服务的健康状态
    
    Args:
        service_name: 服务名称
    """
    try:
        checker = get_health_checker()
        result = checker.get_status(service_name)
        
        return ServiceStatusResponse(
            success=True,
            data={
                "service": service_name,
                "status": result.status.value,
                "latency_ms": result.latency,
                "message": result.message,
                "last_check": result.timestamp
            }
        )
    except Exception as e:
        logger.error(f"获取服务健康状态失败: {e}", exc_info=True)
        return ServiceStatusResponse(
            success=False,
            error=str(e)
        )


@router.post("/governance/health/{service_name}/check", response_model=ServiceStatusResponse, summary="立即检查服务健康")
async def check_service_health(service_name: str):
    """
    立即检查指定服务的健康状态
    
    Args:
        service_name: 服务名称
    """
    try:
        checker = get_health_checker()
        result = checker.check_service(service_name)
        
        return ServiceStatusResponse(
            success=True,
            data={
                "service": service_name,
                "status": result.status.value,
                "latency_ms": result.latency,
                "message": result.message
            }
        )
    except Exception as e:
        logger.error(f"检查服务健康状态失败: {e}", exc_info=True)
        return ServiceStatusResponse(
            success=False,
            error=str(e)
        )


# ==================== 性能统计 API ====================

class PerformanceStatsResponse(BaseModel):
    """性能统计响应模型"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="性能统计数据")
    error: Optional[str] = Field(None, description="错误信息")


@router.get("/governance/performance/stats", response_model=PerformanceStatsResponse, summary="获取性能统计信息")
async def get_performance_stats():
    """
    获取性能统计信息
    
    包括：
    - 数据库连接池统计
    - Redis连接池统计
    - 缓存统计（命中率等）
    """
    try:
        stats = {}
        
        # 1. MySQL连接池统计
        try:
            from shared.config.database import get_connection_pool_stats
            stats["mysql_pool"] = get_connection_pool_stats()
        except Exception as e:
            logger.warning(f"获取MySQL连接池统计失败: {e}")
            stats["mysql_pool"] = {"error": str(e)}
        
        # 2. Redis连接池统计
        try:
            from shared.config.redis import get_redis_pool_stats
            stats["redis_pool"] = get_redis_pool_stats()
        except Exception as e:
            logger.warning(f"获取Redis连接池统计失败: {e}")
            stats["redis_pool"] = {"error": str(e)}
        
        # 3. 多级缓存统计
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            stats["cache"] = cache.stats()
        except Exception as e:
            logger.warning(f"获取缓存统计失败: {e}")
            stats["cache"] = {"error": str(e)}
        
        return PerformanceStatsResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        logger.error(f"获取性能统计失败: {e}", exc_info=True)
        return PerformanceStatsResponse(
            success=False,
            error=str(e)
        )


# ==================== 综合状态 API ====================

@router.get("/governance/dashboard", response_model=ServiceStatusResponse, summary="获取治理仪表板数据")
async def get_governance_dashboard():
    """
    获取服务治理仪表板数据
    
    包含：
    - 服务注册中心状态
    - 熔断器状态
    - 限流器状态
    - 健康检查状态
    """
    try:
        # 服务注册中心
        registry = get_registry()
        registry.initialize()
        registry_stats = registry.get_stats()
        
        # 熔断器
        breaker_stats = get_breaker_stats()
        
        # 限流器
        limiter_stats = get_limiter_stats()
        
        # 健康检查
        checker = get_health_checker()
        health_stats = checker.get_stats()
        
        return ServiceStatusResponse(
            success=True,
            data={
                "registry": registry_stats,
                "circuit_breakers": {
                    "total": len(breaker_stats),
                    "breakers": breaker_stats
                },
                "rate_limiters": {
                    "total": len(limiter_stats),
                    "limiters": limiter_stats
                },
                "health": health_stats
            }
        )
    except Exception as e:
        logger.error(f"获取仪表板数据失败: {e}", exc_info=True)
        return ServiceStatusResponse(
            success=False,
            error=str(e)
        )
