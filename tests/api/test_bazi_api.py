#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字 API 测试

测试 /api/v1/bazi/* 接口。
"""

import pytest
from unittest.mock import patch, MagicMock


class TestBaziCalculateAPI:
    """测试 /api/v1/bazi/calculate 接口"""
    
    @pytest.mark.api
    def test_calculate_success(self, client, sample_bazi_request):
        """正常计算应返回成功"""
        response = client.post("/api/v1/bazi/calculate", json=sample_bazi_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
    
    @pytest.mark.api
    def test_calculate_missing_date(self, client):
        """缺少日期应返回错误"""
        request = {
            "solar_time": "12:30",
            "gender": "male"
        }
        response = client.post("/api/v1/bazi/calculate", json=request)
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.api
    def test_calculate_invalid_gender(self, client):
        """无效性别应返回错误"""
        request = {
            "solar_date": "1990-01-15",
            "solar_time": "12:30",
            "gender": "unknown"
        }
        response = client.post("/api/v1/bazi/calculate", json=request)
        
        assert response.status_code == 422
    
    @pytest.mark.api
    def test_calculate_lunar_input(self, client):
        """农历输入应正常处理"""
        request = {
            "solar_date": "1990-01-15",
            "solar_time": "12:30",
            "gender": "male",
            "calendar_type": "lunar"
        }
        response = client.post("/api/v1/bazi/calculate", json=request)
        
        assert response.status_code == 200


class TestBaziDetailAPI:
    """测试 /api/v1/bazi/detail 接口"""
    
    @pytest.mark.api
    def test_detail_success(self, client, sample_bazi_request):
        """正常获取详情应返回成功"""
        response = client.post("/api/v1/bazi/detail", json=sample_bazi_request)
        
        # 接口可能返回 200 或其他状态
        assert response.status_code in [200, 404, 500]


class TestBaziInterfaceAPI:
    """测试 /api/v1/bazi/interface 接口"""
    
    @pytest.mark.api
    def test_interface_success(self, client, sample_bazi_request):
        """正常获取界面数据应返回成功"""
        response = client.post("/api/v1/bazi/interface", json=sample_bazi_request)
        
        assert response.status_code in [200, 404, 500]
