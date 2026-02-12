#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

身宫命宫 API 端到端测试

测试身宫命宫计算功能的完整数据流，包括：
- 基本功能验证
- 大运流年流月数据验证
- 农历输入验证
- 时区转换验证
- 组合场景验证
- 数据一致性验证（与 /bazi/fortune/display 对比）
"""

import pytest; pytest.importorskip("fastapi", reason="fastapi not installed")
import pytest
import httpx
import sys
import os
from typing import Dict, Any

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
@pytest.mark.e2e
class TestShengongMinggongE2E:
    """身宫命宫 API 端到端测试类"""
    
    async def test_basic_functionality(self, client):
        """测试：基本功能 - 验证身宫、命宫、胎元数据正确返回"""
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
        assert result["success"] == True
        data = result["data"]
        
        # 验证身宫数据
        assert "shengong" in data
        shengong = data["shengong"]
        assert "stem" in shengong and "branch" in shengong
        assert "char" in shengong["stem"] and "char" in shengong["branch"]
        assert "main_star" in shengong
        assert "hidden_stems" in shengong
        assert isinstance(shengong["hidden_stems"], list)
        
        # 验证命宫数据
        assert "minggong" in data
        minggong = data["minggong"]
        assert "stem" in minggong and "branch" in minggong
        assert "char" in minggong["stem"] and "char" in minggong["branch"]
        assert "main_star" in minggong
        assert "hidden_stems" in minggong
        assert isinstance(minggong["hidden_stems"], list)
        
        # 验证胎元数据
        assert "taiyuan" in data
        taiyuan = data["taiyuan"]
        assert "stem" in taiyuan and "branch" in taiyuan
        assert "char" in taiyuan["stem"] and "char" in taiyuan["branch"]
        
        # 验证四柱数据
        assert "pillars" in data
        pillars = data["pillars"]
        for pillar_type in ["year", "month", "day", "hour"]:
            assert pillar_type in pillars
    
    async def test_fortune_data_completeness(self, client):
        """测试：大运流年流月数据 - 验证完整的数据结构和内容"""
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
        assert result["success"] == True
        data = result["data"]
        
        # 验证大运数据完整性
        assert "dayun" in data
        dayun = data["dayun"]
        assert "current" in dayun
        assert "list" in dayun
        assert "qiyun" in dayun
        assert "jiaoyun" in dayun
        
        # 验证起运信息结构
        qiyun = dayun["qiyun"]
        if qiyun:  # 如果数据不为空
            assert isinstance(qiyun, dict)
            # 验证可能存在的字段
            if "date" in qiyun:
                assert isinstance(qiyun["date"], str)
            if "age_display" in qiyun:
                assert isinstance(qiyun["age_display"], str)
            if "description" in qiyun:
                assert isinstance(qiyun["description"], str)
        
        # 验证交运信息结构
        jiaoyun = dayun["jiaoyun"]
        if jiaoyun:  # 如果数据不为空
            assert isinstance(jiaoyun, dict)
            # 验证可能存在的字段
            if "date" in jiaoyun:
                assert isinstance(jiaoyun["date"], str)
            if "age_display" in jiaoyun:
                assert isinstance(jiaoyun["age_display"], str)
            if "description" in jiaoyun:
                assert isinstance(jiaoyun["description"], str)
        
        # 验证流年数据完整性
        assert "liunian" in data
        liunian = data["liunian"]
        assert "current" in liunian
        assert "list" in liunian
        assert isinstance(liunian["list"], list)
        
        # 验证流月数据完整性
        assert "liuyue" in data
        liuyue = data["liuyue"]
        assert "current" in liuyue
        assert "list" in liuyue
        assert "target_year" in liuyue
        assert isinstance(liuyue["list"], list)
        
        # 验证 target_year
        if liuyue["target_year"] is not None:
            assert isinstance(liuyue["target_year"], int)
            assert 1900 <= liuyue["target_year"] <= 2100
    
    async def test_lunar_input(self, client):
        """测试：农历输入 - 验证农历日期转换后数据正确"""
        request_data = {
            "solar_date": "2024年正月初一",
            "solar_time": "12:00",
            "gender": "male",
            "calendar_type": "lunar"
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        data = result["data"]
        
        # 验证转换信息
        if "conversion_info" in data:
            conversion_info = data["conversion_info"]
            assert conversion_info.get("calendar_type") == "lunar"
            assert conversion_info.get("converted") == True
            assert "lunar_to_solar" in conversion_info
        
        # 验证身宫命宫数据仍然正确返回
        assert "shengong" in data
        assert "minggong" in data
        assert "taiyuan" in data
        
        # 验证大运流年流月数据仍然正确返回
        assert "dayun" in data
        assert "liunian" in data
        assert "liuyue" in data
    
    async def test_timezone_conversion(self, client):
        """测试：时区转换 - 验证时区转换后数据正确"""
        request_data = {
            "solar_date": "1990-01-15",
            "solar_time": "14:30",
            "gender": "male",
            "location": "德国"
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        data = result["data"]
        
        # 验证转换信息
        if "conversion_info" in data:
            conversion_info = data["conversion_info"]
            assert "timezone_info" in conversion_info
            timezone_info = conversion_info["timezone_info"]
            if timezone_info:
                assert "timezone" in timezone_info
                assert "true_solar_time" in timezone_info
        
        # 验证身宫命宫数据仍然正确返回
        assert "shengong" in data
        assert "minggong" in data
        assert "taiyuan" in data
        
        # 验证大运流年流月数据仍然正确返回
        assert "dayun" in data
        assert "liunian" in data
        assert "liuyue" in data
    
    async def test_combined_scenario(self, client):
        """测试：组合场景 - 农历输入 + 时区转换"""
        request_data = {
            "solar_date": "2024年正月初一",
            "solar_time": "14:30",
            "gender": "male",
            "calendar_type": "lunar",
            "location": "德国"
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        data = result["data"]
        
        # 验证转换信息包含农历转换和时区转换
        if "conversion_info" in data:
            conversion_info = data["conversion_info"]
            assert conversion_info.get("calendar_type") == "lunar"
            assert conversion_info.get("converted") == True
            assert "lunar_to_solar" in conversion_info
            assert "timezone_info" in conversion_info
        
        # 验证所有数据正确返回
        assert "shengong" in data
        assert "minggong" in data
        assert "taiyuan" in data
        assert "dayun" in data
        assert "liunian" in data
        assert "liuyue" in data
    
    async def test_data_consistency_with_fortune_display(self, client):
        """测试：数据一致性 - 与 /bazi/fortune/display 接口返回的大运流年流月数据对比验证"""
        request_data = {
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male"
        }
        
        # 调用身宫命宫接口
        response_shengong = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        # 调用大运流年流月接口
        response_fortune = await client.post(
            "/api/v1/bazi/fortune/display",
            json=request_data
        )
        
        assert response_shengong.status_code == 200
        assert response_fortune.status_code == 200
        
        result_shengong = response_shengong.json()
        result_fortune = response_fortune.json()
        
        assert result_shengong["success"] == True
        assert result_fortune["success"] == True
        
        data_shengong = result_shengong["data"]
        data_fortune = result_fortune["data"]
        
        # 对比大运数据格式
        dayun_shengong = data_shengong.get("dayun", {})
        dayun_fortune = data_fortune.get("dayun", {})
        
        # 验证字段结构一致
        assert "current" in dayun_shengong == ("current" in dayun_fortune)
        assert "list" in dayun_shengong == ("list" in dayun_fortune)
        assert "qiyun" in dayun_shengong == ("qiyun" in dayun_fortune)
        assert "jiaoyun" in dayun_shengong == ("jiaoyun" in dayun_fortune)
        
        # 对比流年数据格式
        liunian_shengong = data_shengong.get("liunian", {})
        liunian_fortune = data_fortune.get("liunian", {})
        
        assert "current" in liunian_shengong == ("current" in liunian_fortune)
        assert "list" in liunian_shengong == ("list" in liunian_fortune)
        
        # 对比流月数据格式
        liuyue_shengong = data_shengong.get("liuyue", {})
        liuyue_fortune = data_fortune.get("liuyue", {})
        
        assert "current" in liuyue_shengong == ("current" in liuyue_fortune)
        assert "list" in liuyue_shengong == ("list" in liuyue_fortune)
        assert "target_year" in liuyue_shengong == ("target_year" in liuyue_fortune)
        
        # 如果数据都不为空，验证数据内容一致性（可选，因为可能因为时间差异导致数据不同）
        # 这里只验证格式一致性，不验证具体数值

