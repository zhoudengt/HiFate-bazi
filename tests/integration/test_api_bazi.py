#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

八字 API 集成测试
"""

import pytest; pytest.importorskip("grpc", reason="grpc not installed")
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
@pytest.mark.integration
class TestBaziAPI:
    """八字 API 测试类"""
    
    async def test_health_check(self, client):
        """测试健康检查接口"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    async def test_monthly_fortune_success(self, client):
        """测试成功获取月运势"""
        response = await client.post(
            "/api/v1/bazi/monthly-fortune",
            json={
                "solar_date": "1990-01-15",
                "solar_time": "12:00",
                "gender": "male"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_monthly_fortune_missing_params(self, client):
        """测试缺少参数"""
        response = await client.post(
            "/api/v1/bazi/monthly-fortune",
            json={
                "solar_date": "1990-01-15"
                # 缺少 solar_time 和 gender
            }
        )
        
        # 应该返回验证错误
        assert response.status_code in [400, 422]
    
    async def test_formula_analysis_success(self, client):
        """测试算法公式分析接口"""
        response = await client.post(
            "/api/v1/bazi/formula-analysis",
            json={
                "solar_date": "1990-01-15",
                "solar_time": "12:00",
                "gender": "male"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data

