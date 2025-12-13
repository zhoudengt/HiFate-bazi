#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
身宫命宫 API 专项测试

测试身宫命宫计算功能的完整性和正确性
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
class TestShengongMinggong:
    """身宫命宫 API 测试类"""
    
    async def test_shengong_minggong_basic(self, client):
        """测试：基础身宫命宫计算"""
        request_data = {
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male"
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # 验证响应结构
        assert result["success"] == True
        assert "data" in result
        
        data = result["data"]
        assert isinstance(data, dict)
        
        # 验证身宫数据
        assert "shengong" in data
        shengong = data["shengong"]
        assert isinstance(shengong, dict)
        assert "stem" in shengong and "branch" in shengong
        assert "char" in shengong["stem"] and "char" in shengong["branch"]
        shengong_ganzhi = shengong["stem"]["char"] + shengong["branch"]["char"]
        assert len(shengong_ganzhi) == 2, f"身宫干支应为2个字符，实际: {shengong_ganzhi}"
        
        # 验证命宫数据
        assert "minggong" in data
        minggong = data["minggong"]
        assert isinstance(minggong, dict)
        assert "stem" in minggong and "branch" in minggong
        assert "char" in minggong["stem"] and "char" in minggong["branch"]
        minggong_ganzhi = minggong["stem"]["char"] + minggong["branch"]["char"]
        assert len(minggong_ganzhi) == 2, f"命宫干支应为2个字符，实际: {minggong_ganzhi}"
        
        # 验证四柱数据
        assert "pillars" in data
        pillars = data["pillars"]
        assert isinstance(pillars, dict)
        for pillar_type in ["year", "month", "day", "hour"]:
            assert pillar_type in pillars
    
    @pytest.mark.parametrize("solar_date,solar_time,gender,expected_shengong_pattern,expected_minggong_pattern", [
        ("1990-01-15", "12:00", "male", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$"),
        ("1995-05-20", "14:30", "female", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$"),
        ("1987-01-07", "09:00", "male", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$"),
        ("2000-12-31", "23:59", "female", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$"),
    ])
    async def test_shengong_minggong_different_inputs(
        self, 
        client, 
        solar_date, 
        solar_time, 
        gender,
        expected_shengong_pattern,
        expected_minggong_pattern
    ):
        """测试：不同输入的身宫命宫计算"""
        import re
        
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
        
        assert result["success"] == True
        assert "data" in result
        
        data = result["data"]
        
        # 验证身宫
        shengong_ganzhi = data["shengong"]["stem"]["char"] + data["shengong"]["branch"]["char"]
        assert re.match(expected_shengong_pattern, shengong_ganzhi), f"身宫干支格式错误: {shengong_ganzhi}"
        
        # 验证命宫
        minggong_ganzhi = data["minggong"]["stem"]["char"] + data["minggong"]["branch"]["char"]
        assert re.match(expected_minggong_pattern, minggong_ganzhi), f"命宫干支格式错误: {minggong_ganzhi}"
        
        # 验证数据完整性
        assert "main_star" in data["shengong"]
        assert "main_star" in data["minggong"]
        assert "hidden_stems" in data["shengong"]
        assert "hidden_stems" in data["minggong"]
        assert isinstance(data["shengong"]["hidden_stems"], list)
        assert isinstance(data["minggong"]["hidden_stems"], list)
    
    async def test_shengong_minggong_invalid_date(self, client):
        """测试：无效日期输入"""
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json={
                "solar_date": "1990-13-45",
                "solar_time": "12:00",
                "gender": "male"
            }
        )
        
        # 应该返回验证错误
        assert response.status_code in [400, 422]
    
    async def test_shengong_minggong_missing_params(self, client):
        """测试：缺少必需参数"""
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json={
                "solar_date": "1990-01-15"
                # 缺少 solar_time 和 gender
            }
        )
        
        # 应该返回验证错误
        assert response.status_code in [400, 422]
    
    async def test_shengong_minggong_data_structure(self, client):
        """测试：验证数据结构完整性"""
        request_data = {
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male"
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        data = result["data"]
        
        # 验证身宫数据结构
        shengong = data["shengong"]
        required_fields = ["stem", "branch", "main_star", "hidden_stems", "star_fortune", 
                          "self_sitting", "kongwang", "nayin", "deities"]
        for field in required_fields:
            assert field in shengong, f"身宫缺少字段: {field}"
        
        # 验证命宫数据结构
        minggong = data["minggong"]
        for field in required_fields:
            assert field in minggong, f"命宫缺少字段: {field}"
        
        # 验证四柱数据结构
        pillars = data["pillars"]
        for pillar_type in ["year", "month", "day", "hour"]:
            pillar = pillars[pillar_type]
            pillar_fields = ["stem", "branch", "main_star", "hidden_stems", "star_fortune",
                           "self_sitting", "kongwang", "nayin", "deities"]
            for field in pillar_fields:
                assert field in pillar, f"四柱 {pillar_type} 缺少字段: {field}"

