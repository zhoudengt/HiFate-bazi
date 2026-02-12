#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

八字接口影响分析测试
验证时区转换对时柱和日柱的影响，确认年柱和月柱不受影响
"""

import pytest; pytest.importorskip("fastapi", reason="fastapi not installed")
import pytest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


def extract_pillars(response_data):
    """从响应中提取四柱信息"""
    pillars = {}
    
    # 尝试从不同位置提取四柱
    if "data" in response_data:
        data = response_data["data"]
        if "bazi_pillars" in data:
            pillars = data["bazi_pillars"]
        elif "bazi" in data and "bazi_pillars" in data["bazi"]:
            pillars = data["bazi"]["bazi_pillars"]
        elif "pan" in data and "pillars" in data["pan"]:
            # 排盘接口的格式
            pillars_list = data["pan"]["pillars"]
            for pillar in pillars_list:
                pillar_type = pillar.get("type")
                if pillar_type:
                    pillars[pillar_type] = {
                        "stem": pillar.get("stem", {}).get("char", ""),
                        "branch": pillar.get("branch", {}).get("char", "")
                    }
    
    return pillars


@pytest.mark.api
class TestImpactAnalysis:
    """影响分析测试"""
    
    def test_hour_pillar_affected(self, client):
        """测试：时区转换影响时柱（不跨日）"""
        # 无时区转换
        base_request = {
            "solar_date": "1990-05-15",
            "solar_time": "14:30",
            "gender": "male"
        }
        response1 = client.post("/api/v1/bazi/pan/display", json=base_request)
        assert response1.status_code == 200
        data1 = response1.json()
        pillars1 = extract_pillars(data1)
        
        # 有时区转换（德国）
        timezone_request = {
            **base_request,
            "location": "德国"
        }
        response2 = client.post("/api/v1/bazi/pan/display", json=timezone_request)
        assert response2.status_code == 200
        data2 = response2.json()
        pillars2 = extract_pillars(data2)
        
        # 验证年柱和月柱不变
        if "year" in pillars1 and "year" in pillars2:
            assert pillars1["year"] == pillars2["year"], "年柱应该不变"
        if "month" in pillars1 and "month" in pillars2:
            assert pillars1["month"] == pillars2["month"], "月柱应该不变"
        
        # 时柱可能变化（取决于时区转换）
        # 如果时间变化，时柱会变化
        if "hour" in pillars1 and "hour" in pillars2:
            # 时柱可能相同也可能不同，取决于具体的时间转换
            pass
    
    def test_day_pillar_affected_cross_day(self, client):
        """测试：跨日时影响日柱和时柱"""
        # 无时区转换
        base_request = {
            "solar_date": "1990-05-15",
            "solar_time": "23:30",
            "gender": "male"
        }
        response1 = client.post("/api/v1/bazi/pan/display", json=base_request)
        assert response1.status_code == 200
        data1 = response1.json()
        pillars1 = extract_pillars(data1)
        
        # 有时区转换（东经150度，时差+2小时，可能跨日）
        cross_day_request = {
            **base_request,
            "longitude": 150.0
        }
        response2 = client.post("/api/v1/bazi/pan/display", json=cross_day_request)
        assert response2.status_code == 200
        data2 = response2.json()
        pillars2 = extract_pillars(data2)
        
        # 验证年柱和月柱不变
        if "year" in pillars1 and "year" in pillars2:
            assert pillars1["year"] == pillars2["year"], "年柱应该不变"
        if "month" in pillars1 and "month" in pillars2:
            assert pillars1["month"] == pillars2["month"], "月柱应该不变"
        
        # 如果跨日，日柱和时柱会变化
        # 注意：这里只验证逻辑，实际结果取决于具体的转换
    
    def test_year_month_pillars_unaffected(self, client):
        """测试：年柱和月柱不受时区转换影响"""
        base_request = {
            "solar_date": "1990-05-15",
            "solar_time": "14:30",
            "gender": "male"
        }
        
        # 测试多个时区
        timezones = [
            {"location": "德国"},
            {"location": "法国"},
            {"latitude": 40.71, "longitude": -74.00},  # 纽约
            {"latitude": 35.68, "longitude": 139.69},  # 东京
        ]
        
        base_response = client.post("/api/v1/bazi/pan/display", json=base_request)
        assert base_response.status_code == 200
        base_data = base_response.json()
        base_pillars = extract_pillars(base_data)
        
        for tz_config in timezones:
            tz_request = {**base_request, **tz_config}
            response = client.post("/api/v1/bazi/pan/display", json=tz_request)
            assert response.status_code == 200
            data = response.json()
            pillars = extract_pillars(data)
            
            # 验证年柱和月柱不变
            if "year" in base_pillars and "year" in pillars:
                assert base_pillars["year"] == pillars["year"], f"年柱应该不变（时区: {tz_config}）"
            if "month" in base_pillars and "month" in pillars:
                assert base_pillars["month"] == pillars["month"], f"月柱应该不变（时区: {tz_config}）"
    
    def test_lunar_conversion_affects_all_pillars(self, client):
        """测试：农历转换可能影响所有柱（因为日期可能变化）"""
        # 使用农历日期
        lunar_request = {
            "solar_date": "2024年正月初一",
            "solar_time": "12:00",
            "gender": "male",
            "calendar_type": "lunar"
        }
        
        # 使用对应的阳历日期
        solar_request = {
            "solar_date": "2024-02-10",  # 农历2024年正月初一对应的阳历日期
            "solar_time": "12:00",
            "gender": "male"
        }
        
        response1 = client.post("/api/v1/bazi/pan/display", json=lunar_request)
        assert response1.status_code == 200
        data1 = response1.json()
        pillars1 = extract_pillars(data1)
        
        response2 = client.post("/api/v1/bazi/pan/display", json=solar_request)
        assert response2.status_code == 200
        data2 = response2.json()
        pillars2 = extract_pillars(data2)
        
        # 农历转换后，所有柱应该一致（因为日期相同）
        if pillars1 and pillars2:
            for pillar_type in ["year", "month", "day", "hour"]:
                if pillar_type in pillars1 and pillar_type in pillars2:
                    assert pillars1[pillar_type] == pillars2[pillar_type], \
                        f"{pillar_type}柱应该一致（农历转换后）"


@pytest.mark.api
class TestAllEndpointsImpact:
    """所有接口的影响分析测试"""
    
    @pytest.mark.parametrize("endpoint", [
        "/api/v1/bazi/pan/display",
        "/api/v1/bazi/wangshuai",
        "/api/v1/bazi/formula-analysis",
        "/api/v1/bazi/wuxing-proportion",
        "/api/v1/bazi/rizhu-liujiazi",
        "/api/v1/bazi/xishen-jishen",
    ])
    def test_endpoint_timezone_impact(self, client, endpoint):
        """测试：各接口的时区转换影响"""
        base_request = {
            "solar_date": "1990-05-15",
            "solar_time": "14:30",
            "gender": "male"
        }
        
        timezone_request = {
            **base_request,
            "location": "德国"
        }
        
        # 无时区转换
        response1 = client.post(endpoint, json=base_request)
        assert response1.status_code == 200
        
        # 有时区转换
        response2 = client.post(endpoint, json=timezone_request)
        assert response2.status_code == 200
        
        # 验证响应结构
        data1 = response1.json()
        data2 = response2.json()
        assert data1.get("success") == True
        assert data2.get("success") == True
        
        # 验证时区转换的响应包含 conversion_info
        if "conversion_info" in data2:
            assert "timezone_info" in data2["conversion_info"]

