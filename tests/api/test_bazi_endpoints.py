#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字 API 端点测试
测试所有八字相关的 API 端点
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


@pytest.fixture
def sample_bazi_data():
    """示例八字数据"""
    return {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male"
    }


@pytest.mark.asyncio
@pytest.mark.api
class TestBaziEndpoints:
    """八字 API 端点测试类"""
    
    async def test_calculate_bazi(self, client, sample_bazi_data):
        """测试：计算八字 API"""
        response = await client.post(
            "/api/v1/bazi/calculate",
            json=sample_bazi_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
        if "data" in data:
            assert "bazi" in data["data"]
    
    async def test_bazi_interface(self, client, sample_bazi_data):
        """测试：生成八字界面信息 API"""
        response = await client.post(
            "/api/v1/bazi/interface",
            json=sample_bazi_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_bazi_detail(self, client, sample_bazi_data):
        """测试：计算详细八字信息 API"""
        data = {
            **sample_bazi_data,
            "current_time": "2025-01-21 10:00"
        }
        response = await client.post(
            "/api/v1/bazi/detail",
            json=data
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "success" in result or "data" in result
    
    async def test_shengong_minggong(self, client, sample_bazi_data):
        """测试：获取身宫命宫信息 API"""
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=sample_bazi_data
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # 验证响应结构
        assert "success" in result, "响应应包含 success 字段"
        assert result["success"] == True, "success 应为 True"
        assert "data" in result, "响应应包含 data 字段"
        
        # 验证数据结构
        data = result["data"]
        assert isinstance(data, dict), "data 应为字典类型"
        
        # 验证身宫数据
        assert "shengong" in data, "data 应包含 shengong 字段"
        shengong = data["shengong"]
        assert isinstance(shengong, dict), "shengong 应为字典类型"
        assert "stem" in shengong, "shengong 应包含 stem 字段"
        assert "branch" in shengong, "shengong 应包含 branch 字段"
        assert "char" in shengong["stem"], "shengong.stem 应包含 char 字段"
        assert "char" in shengong["branch"], "shengong.branch 应包含 char 字段"
        assert len(shengong["stem"]["char"]) == 1, "身宫天干应为1个字符"
        assert len(shengong["branch"]["char"]) == 1, "身宫地支应为1个字符"
        assert "main_star" in shengong, "shengong 应包含 main_star 字段"
        
        # 验证命宫数据
        assert "minggong" in data, "data 应包含 minggong 字段"
        minggong = data["minggong"]
        assert isinstance(minggong, dict), "minggong 应为字典类型"
        assert "stem" in minggong, "minggong 应包含 stem 字段"
        assert "branch" in minggong, "minggong 应包含 branch 字段"
        assert "char" in minggong["stem"], "minggong.stem 应包含 char 字段"
        assert "char" in minggong["branch"], "minggong.branch 应包含 char 字段"
        assert len(minggong["stem"]["char"]) == 1, "命宫天干应为1个字符"
        assert len(minggong["branch"]["char"]) == 1, "命宫地支应为1个字符"
        assert "main_star" in minggong, "minggong 应包含 main_star 字段"
        
        # 验证四柱数据
        assert "pillars" in data, "data 应包含 pillars 字段"
        pillars = data["pillars"]
        assert isinstance(pillars, dict), "pillars 应为字典类型"
        
        for pillar_type in ["year", "month", "day", "hour"]:
            assert pillar_type in pillars, f"pillars 应包含 {pillar_type} 字段"
            pillar = pillars[pillar_type]
            assert isinstance(pillar, dict), f"pillars.{pillar_type} 应为字典类型"
            assert "stem" in pillar, f"pillars.{pillar_type} 应包含 stem 字段"
            assert "branch" in pillar, f"pillars.{pillar_type} 应包含 branch 字段"
            assert "char" in pillar["stem"], f"pillars.{pillar_type}.stem 应包含 char 字段"
            assert "char" in pillar["branch"], f"pillars.{pillar_type}.branch 应包含 char 字段"
    
    @pytest.mark.parametrize("solar_date,solar_time,gender", [
        ("1990-01-15", "12:00", "male"),
        ("1995-05-20", "14:30", "female"),
        ("1987-01-07", "09:00", "male"),
        ("2000-12-31", "23:59", "female"),
    ])
    async def test_shengong_minggong_different_inputs(self, client, solar_date, solar_time, gender):
        """测试：不同输入的身宫命宫计算"""
        request_data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # 验证响应结构
        assert result["success"] == True, f"测试用例失败: {solar_date} {solar_time} {gender}"
        assert "data" in result, "响应应包含 data 字段"
        
        data = result["data"]
        
        # 验证身宫和命宫都有数据
        assert "shengong" in data and data["shengong"], "身宫数据不应为空"
        assert "minggong" in data and data["minggong"], "命宫数据不应为空"
        
        # 验证干支格式
        shengong_ganzhi = data["shengong"]["stem"]["char"] + data["shengong"]["branch"]["char"]
        minggong_ganzhi = data["minggong"]["stem"]["char"] + data["minggong"]["branch"]["char"]
        
        assert len(shengong_ganzhi) == 2, f"身宫干支应为2个字符，实际: {shengong_ganzhi}"
        assert len(minggong_ganzhi) == 2, f"命宫干支应为2个字符，实际: {minggong_ganzhi}"
        
        # 验证四柱数据
        assert "pillars" in data, "应包含四柱数据"
        for pillar_type in ["year", "month", "day", "hour"]:
            assert pillar_type in data["pillars"], f"应包含 {pillar_type} 柱数据"
    
    @pytest.mark.parametrize("solar_date,solar_time,gender", [
        ("1990-01-15", "12:00", "male"),
        ("1995-05-20", "14:30", "female"),
        ("1980-12-31", "23:59", "male"),
    ])
    async def test_calculate_bazi_different_inputs(self, client, solar_date, solar_time, gender):
        """测试：不同输入的八字计算"""
        response = await client.post(
            "/api/v1/bazi/calculate",
            json={
                "solar_date": solar_date,
                "solar_time": solar_time,
                "gender": gender
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
    
    async def test_calculate_bazi_invalid_date(self, client):
        """测试：无效日期输入"""
        response = await client.post(
            "/api/v1/bazi/calculate",
            json={
                "solar_date": "1990-13-45",
                "solar_time": "12:00",
                "gender": "male"
            }
        )
        
        # 应该返回验证错误
        assert response.status_code in [400, 422]
    
    async def test_calculate_bazi_missing_params(self, client):
        """测试：缺少必需参数"""
        response = await client.post(
            "/api/v1/bazi/calculate",
            json={
                "solar_date": "1990-01-15"
                # 缺少 solar_time 和 gender
            }
        )
        
        # 应该返回验证错误
        assert response.status_code in [400, 422]

