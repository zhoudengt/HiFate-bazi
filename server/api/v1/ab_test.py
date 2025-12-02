#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A/B 测试 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from server.utils.ab_test import (
    get_ab_test_manager,
    Experiment,
    ExperimentStatus
)

router = APIRouter()
logger = logging.getLogger(__name__)


class ExperimentCreateRequest(BaseModel):
    """创建实验请求"""
    name: str
    description: str
    traffic_percent: float = 100.0
    variants: Dict[str, float]  # {"A": 50, "B": 50}


class ExperimentStatusRequest(BaseModel):
    """更新实验状态请求"""
    status: str  # "running", "paused", "completed"


class AssignVariantRequest(BaseModel):
    """分配变体请求"""
    experiment_name: str
    user_id: str


class RecordEventRequest(BaseModel):
    """记录事件请求"""
    experiment_name: str
    user_id: str
    event_name: str
    event_data: Optional[Dict[str, Any]] = None


@router.post("/ab-test/experiments")
async def create_experiment(request: ExperimentCreateRequest):
    """创建 A/B 测试实验"""
    try:
        manager = get_ab_test_manager()
        
        experiment = Experiment(
            name=request.name,
            description=request.description,
            status=ExperimentStatus.DRAFT,
            traffic_percent=request.traffic_percent,
            variants=request.variants
        )
        
        success = manager.create_experiment(experiment)
        if not success:
            raise HTTPException(status_code=400, detail="创建实验失败")
        
        return {
            "success": True,
            "experiment": {
                "name": experiment.name,
                "status": experiment.status.value,
                "traffic_percent": experiment.traffic_percent,
                "variants": experiment.variants
            }
        }
    except Exception as e:
        logger.error(f"创建实验失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ab-test/experiments/{experiment_name}")
async def get_experiment(experiment_name: str):
    """获取实验配置"""
    manager = get_ab_test_manager()
    experiment = manager.get_experiment(experiment_name)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="实验不存在")
    
    return {
        "success": True,
        "experiment": {
            "name": experiment.name,
            "description": experiment.description,
            "status": experiment.status.value,
            "traffic_percent": experiment.traffic_percent,
            "variants": experiment.variants
        }
    }


@router.post("/ab-test/experiments/{experiment_name}/status")
async def update_experiment_status(experiment_name: str, request: ExperimentStatusRequest):
    """更新实验状态"""
    try:
        manager = get_ab_test_manager()
        status = ExperimentStatus(request.status)
        
        manager.update_experiment_status(experiment_name, status)
        
        return {
            "success": True,
            "message": f"实验状态已更新为 {status.value}"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的状态值")
    except Exception as e:
        logger.error(f"更新实验状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ab-test/assign")
async def assign_variant(request: AssignVariantRequest):
    """为用户分配变体"""
    manager = get_ab_test_manager()
    variant = manager.assign_variant(request.experiment_name, request.user_id)
    
    return {
        "success": True,
        "experiment": request.experiment_name,
        "user_id": request.user_id,
        "variant": variant
    }


@router.post("/ab-test/events")
async def record_event(request: RecordEventRequest):
    """记录事件"""
    manager = get_ab_test_manager()
    manager.record_event(
        request.experiment_name,
        request.user_id,
        request.event_name,
        request.event_data
    )
    
    return {
        "success": True,
        "message": "事件已记录"
    }


@router.get("/ab-test/experiments/{experiment_name}/stats")
async def get_experiment_stats(experiment_name: str):
    """获取实验统计"""
    manager = get_ab_test_manager()
    stats = manager.get_experiment_stats(experiment_name)
    
    return {
        "success": True,
        "stats": stats
    }

