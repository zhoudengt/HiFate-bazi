#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可观测性 API

提供：
- 指标查询
- 追踪查询
- 告警管理
- 健康检查
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
import time

from server.observability.metrics_collector import get_metrics
from server.observability.tracer import get_tracer
from server.observability.alert_manager import get_alert_manager, Alert, AlertSeverity

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 数据模型 ====================

class ObservabilityResponse(BaseModel):
    """可观测性响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="数据")
    error: Optional[str] = Field(None, description="错误信息")


class FireAlertRequest(BaseModel):
    """触发告警请求"""
    name: str = Field(..., description="告警名称")
    severity: str = Field("warning", description="严重程度: info/warning/error/critical")
    message: str = Field(..., description="告警消息")
    labels: Dict[str, str] = Field(default_factory=dict, description="标签")


# ==================== 指标 API ====================

@router.get("/observability/metrics", response_model=ObservabilityResponse, summary="获取所有指标")
async def get_all_metrics():
    """
    获取所有指标数据
    
    返回计数器、仪表盘、直方图等指标
    """
    try:
        metrics = get_metrics()
        data = metrics.collect_all()
        
        return ObservabilityResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"获取指标失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


@router.get("/observability/metrics/prometheus", summary="Prometheus 格式指标")
async def get_prometheus_metrics():
    """
    获取 Prometheus 格式的指标
    
    可直接被 Prometheus 抓取
    """
    try:
        metrics = get_metrics()
        content = metrics.export_prometheus()
        
        return Response(
            content=content,
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"导出 Prometheus 指标失败: {e}", exc_info=True)
        return Response(
            content=f"# ERROR: {str(e)}",
            media_type="text/plain"
        )


# ==================== 追踪 API ====================

@router.get("/observability/traces", response_model=ObservabilityResponse, summary="获取追踪数据")
async def get_traces(trace_id: Optional[str] = None, limit: int = 100):
    """
    获取追踪数据
    
    Args:
        trace_id: 追踪 ID（可选，指定则只返回该追踪的数据）
        limit: 返回数量限制
    """
    try:
        tracer = get_tracer()
        traces = tracer.get_traces(trace_id, limit)
        
        return ObservabilityResponse(
            success=True,
            data={
                "count": len(traces),
                "traces": traces
            }
        )
    except Exception as e:
        logger.error(f"获取追踪数据失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


@router.get("/observability/traces/stats", response_model=ObservabilityResponse, summary="获取追踪统计")
async def get_trace_stats():
    """
    获取追踪统计信息
    """
    try:
        tracer = get_tracer()
        stats = tracer.get_stats()
        
        return ObservabilityResponse(success=True, data=stats)
    except Exception as e:
        logger.error(f"获取追踪统计失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


# ==================== 告警 API ====================

@router.get("/observability/alerts", response_model=ObservabilityResponse, summary="获取活跃告警")
async def get_active_alerts():
    """
    获取当前活跃的告警
    """
    try:
        alert_manager = get_alert_manager()
        alerts = alert_manager.get_active_alerts()
        
        return ObservabilityResponse(
            success=True,
            data={
                "count": len(alerts),
                "alerts": [a.to_dict() for a in alerts]
            }
        )
    except Exception as e:
        logger.error(f"获取告警失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


@router.get("/observability/alerts/history", response_model=ObservabilityResponse, summary="获取告警历史")
async def get_alert_history(limit: int = 100):
    """
    获取告警历史
    
    Args:
        limit: 返回数量限制
    """
    try:
        alert_manager = get_alert_manager()
        history = alert_manager.get_history(limit)
        
        return ObservabilityResponse(
            success=True,
            data={
                "count": len(history),
                "history": [a.to_dict() for a in history]
            }
        )
    except Exception as e:
        logger.error(f"获取告警历史失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


@router.get("/observability/alerts/stats", response_model=ObservabilityResponse, summary="获取告警统计")
async def get_alert_stats():
    """
    获取告警统计信息
    """
    try:
        alert_manager = get_alert_manager()
        stats = alert_manager.get_stats()
        
        return ObservabilityResponse(success=True, data=stats)
    except Exception as e:
        logger.error(f"获取告警统计失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


@router.post("/observability/alerts/fire", response_model=ObservabilityResponse, summary="触发告警")
async def fire_alert(request: FireAlertRequest):
    """
    手动触发告警
    """
    try:
        alert_manager = get_alert_manager()
        
        # 解析严重程度
        severity_map = {
            "info": AlertSeverity.INFO,
            "warning": AlertSeverity.WARNING,
            "error": AlertSeverity.ERROR,
            "critical": AlertSeverity.CRITICAL,
        }
        severity = severity_map.get(request.severity.lower(), AlertSeverity.WARNING)
        
        alert = Alert(
            name=request.name,
            severity=severity,
            message=request.message,
            labels=request.labels,
            source="api"
        )
        
        alert_manager.fire(alert)
        
        return ObservabilityResponse(
            success=True,
            data={"message": f"告警 {request.name} 已触发"}
        )
    except Exception as e:
        logger.error(f"触发告警失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


@router.post("/observability/alerts/{name}/resolve", response_model=ObservabilityResponse, summary="解除告警")
async def resolve_alert(name: str):
    """
    解除告警
    
    Args:
        name: 告警名称
    """
    try:
        alert_manager = get_alert_manager()
        alert_manager.resolve(name)
        
        return ObservabilityResponse(
            success=True,
            data={"message": f"告警 {name} 已解除"}
        )
    except Exception as e:
        logger.error(f"解除告警失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


@router.post("/observability/alerts/{name}/silence", response_model=ObservabilityResponse, summary="静默告警")
async def silence_alert(name: str, duration: int = 3600):
    """
    静默告警
    
    Args:
        name: 告警名称
        duration: 静默时长（秒）
    """
    try:
        alert_manager = get_alert_manager()
        alert_manager.silence(name, duration)
        
        return ObservabilityResponse(
            success=True,
            data={"message": f"告警 {name} 已静默 {duration} 秒"}
        )
    except Exception as e:
        logger.error(f"静默告警失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


# ==================== 综合 API ====================

@router.get("/observability/dashboard", response_model=ObservabilityResponse, summary="获取可观测性仪表板")
async def get_observability_dashboard():
    """
    获取可观测性仪表板数据
    
    包含指标、追踪、告警的综合信息
    """
    try:
        metrics = get_metrics()
        tracer = get_tracer()
        alert_manager = get_alert_manager()
        
        return ObservabilityResponse(
            success=True,
            data={
                "metrics": {
                    "uptime_seconds": metrics.collect_all().get("uptime_seconds", 0),
                    "counters_count": len(metrics._counters),
                    "gauges_count": len(metrics._gauges),
                    "histograms_count": len(metrics._histograms),
                },
                "traces": tracer.get_stats(),
                "alerts": alert_manager.get_stats(),
                "timestamp": time.time()
            }
        )
    except Exception as e:
        logger.error(f"获取仪表板数据失败: {e}", exc_info=True)
        return ObservabilityResponse(success=False, error=str(e))


# ==================== 健康检查 API ====================

@router.get("/health", summary="健康检查")
async def health_check():
    """
    简单健康检查
    """
    return {"status": "ok", "timestamp": time.time()}


@router.get("/health/live", summary="存活检查")
async def liveness_check():
    """
    存活检查（Kubernetes Liveness Probe）
    """
    return {"status": "ok"}


@router.get("/health/ready", summary="就绪检查")
async def readiness_check():
    """
    就绪检查（Kubernetes Readiness Probe）
    """
    # 这里可以添加依赖检查，如数据库连接等
    return {"status": "ok"}
