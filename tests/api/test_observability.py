#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可观测性 API 测试
测试所有可观测性相关的 API 端点
"""

import pytest
import httpx
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

BASE_URL = "http://localhost:8001"


@pytest.fixture
def client():
    """创建 HTTP 客户端"""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)


@pytest.mark.asyncio
@pytest.mark.api
class TestObservabilityAPI:
    """可观测性 API 测试类"""
    
    async def test_get_all_metrics(self, client):
        """测试：获取所有指标"""
        response = await client.get("/api/v1/observability/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_get_prometheus_metrics(self, client):
        """测试：获取 Prometheus 格式指标"""
        response = await client.get("/api/v1/observability/metrics/prometheus")
        
        assert response.status_code == 200
        # Prometheus 格式通常是文本
        assert response.headers.get("content-type", "").startswith("text/")
    
    async def test_get_traces(self, client):
        """测试：获取追踪数据"""
        response = await client.get("/api/v1/observability/traces")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_get_traces_with_trace_id(self, client):
        """测试：根据 trace_id 获取追踪数据"""
        response = await client.get(
            "/api/v1/observability/traces",
            params={"trace_id": "test_trace_id"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_get_trace_stats(self, client):
        """测试：获取追踪统计"""
        response = await client.get("/api/v1/observability/traces/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_get_active_alerts(self, client):
        """测试：获取活跃告警"""
        response = await client.get("/api/v1/observability/alerts")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_get_alert_history(self, client):
        """测试：获取告警历史"""
        response = await client.get("/api/v1/observability/alerts/history")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_get_alert_stats(self, client):
        """测试：获取告警统计"""
        response = await client.get("/api/v1/observability/alerts/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_fire_alert(self, client):
        """测试：触发告警"""
        response = await client.post(
            "/api/v1/observability/alerts/fire",
            json={
                "name": "test_alert",
                "severity": "warning",
                "message": "测试告警"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_resolve_alert(self, client):
        """测试：解除告警"""
        response = await client.post(
            "/api/v1/observability/alerts/test_alert/resolve"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_silence_alert(self, client):
        """测试：静默告警"""
        response = await client.post(
            "/api/v1/observability/alerts/test_alert/silence",
            params={"duration": 3600}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_get_observability_dashboard(self, client):
        """测试：获取可观测性仪表板"""
        response = await client.get("/api/v1/observability/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data

