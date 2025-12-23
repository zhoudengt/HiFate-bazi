#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字接口农历和时区转换测试
测试所有更新后的接口的新功能（农历输入、时区转换）
"""

import pytest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from fastapi.testclient import TestClient
from server.main import app

# 测试数据
BASE_REQUEST = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
}

LUNAR_REQUEST = {
    "solar_date": "2024年正月初一",
    "solar_time": "12:00",
    "gender": "male",
    "calendar_type": "lunar"
}

TIMEZONE_REQUEST = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "location": "德国"
}

COORDINATES_REQUEST = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "latitude": 52.52,
    "longitude": 13.40
}

COMBINED_REQUEST = {
    "solar_date": "2024年正月初一",
    "solar_time": "12:00",
    "gender": "male",
    "calendar_type": "lunar",
    "location": "德国"
}

CROSS_DAY_REQUEST = {
    "solar_date": "1990-05-15",
    "solar_time": "23:30",
    "gender": "male",
    "longitude": 150.0  # 东经150度，时差+2小时，可能跨日
}

PRIORITY_REQUEST = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "location": "德国",
    "latitude": 39.90,  # 北京纬度
    "longitude": 116.40  # 北京经度
}


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.mark.api
class TestLunarConversion:
    """农历转换测试"""
    
    def test_pan_display_lunar(self, client):
        """测试：基本排盘接口 - 农历输入"""
        response = client.post("/api/v1/bazi/pan/display", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        # 验证转换信息
        if "conversion_info" in data:
            assert data["conversion_info"].get("converted") == True
            assert "lunar_to_solar" in data["conversion_info"]
    
    def test_fortune_display_lunar(self, client):
        """测试：大运流年流月接口 - 农历输入"""
        response = client.post("/api/v1/bazi/fortune/display", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_wangshuai_lunar(self, client):
        """测试：旺衰分析接口 - 农历输入"""
        response = client.post("/api/v1/bazi/wangshuai", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_formula_analysis_lunar(self, client):
        """测试：公式分析接口 - 农历输入"""
        response = client.post("/api/v1/bazi/formula-analysis", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_wuxing_proportion_lunar(self, client):
        """测试：五行占比接口 - 农历输入"""
        response = client.post("/api/v1/bazi/wuxing-proportion", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_rizhu_liujiazi_lunar(self, client):
        """测试：日元-六十甲子接口 - 农历输入"""
        response = client.post("/api/v1/bazi/rizhu-liujiazi", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_xishen_jishen_lunar(self, client):
        """测试：喜神忌神接口 - 农历输入"""
        response = client.post("/api/v1/bazi/xishen-jishen", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_bazi_rules_lunar(self, client):
        """测试：规则匹配接口 - 农历输入"""
        response = client.post("/api/v1/bazi/rules/match", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_liunian_enhanced_lunar(self, client):
        """测试：流年大运增强接口 - 农历输入"""
        response = client.post("/api/v1/bazi/liunian-enhanced", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_monthly_fortune_lunar(self, client):
        """测试：月运势接口 - 农历输入"""
        response = client.post("/api/v1/bazi/monthly-fortune", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_daily_fortune_lunar(self, client):
        """测试：日运势接口 - 农历输入"""
        response = client.post("/api/v1/bazi/daily-fortune", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True


@pytest.mark.api
class TestTimezoneConversion:
    """时区转换测试"""
    
    def test_pan_display_timezone(self, client):
        """测试：基本排盘接口 - 时区转换"""
        response = client.post("/api/v1/bazi/pan/display", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        # 验证转换信息
        if "conversion_info" in data:
            assert "timezone_info" in data["conversion_info"]
    
    def test_fortune_display_timezone(self, client):
        """测试：大运流年流月接口 - 时区转换"""
        response = client.post("/api/v1/bazi/fortune/display", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_wangshuai_timezone(self, client):
        """测试：旺衰分析接口 - 时区转换"""
        response = client.post("/api/v1/bazi/wangshuai", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_formula_analysis_timezone(self, client):
        """测试：公式分析接口 - 时区转换"""
        response = client.post("/api/v1/bazi/formula-analysis", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_wuxing_proportion_timezone(self, client):
        """测试：五行占比接口 - 时区转换"""
        response = client.post("/api/v1/bazi/wuxing-proportion", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_rizhu_liujiazi_timezone(self, client):
        """测试：日元-六十甲子接口 - 时区转换"""
        response = client.post("/api/v1/bazi/rizhu-liujiazi", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_xishen_jishen_timezone(self, client):
        """测试：喜神忌神接口 - 时区转换"""
        response = client.post("/api/v1/bazi/xishen-jishen", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_bazi_rules_timezone(self, client):
        """测试：规则匹配接口 - 时区转换"""
        response = client.post("/api/v1/bazi/rules/match", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_liunian_enhanced_timezone(self, client):
        """测试：流年大运增强接口 - 时区转换"""
        response = client.post("/api/v1/bazi/liunian-enhanced", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_monthly_fortune_timezone(self, client):
        """测试：月运势接口 - 时区转换"""
        response = client.post("/api/v1/bazi/monthly-fortune", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_daily_fortune_timezone(self, client):
        """测试：日运势接口 - 时区转换"""
        response = client.post("/api/v1/bazi/daily-fortune", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_coordinates_timezone(self, client):
        """测试：使用经纬度的时区转换"""
        response = client.post("/api/v1/bazi/pan/display", json=COORDINATES_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_location_priority(self, client):
        """测试：location 优先级高于经纬度"""
        response = client.post("/api/v1/bazi/pan/display", json=PRIORITY_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        # 验证使用德国的时区（而不是北京的）
        if "conversion_info" in data and "timezone_info" in data["conversion_info"]:
            tz_info = data["conversion_info"]["timezone_info"]
            if isinstance(tz_info, dict) and "original_timezone" in tz_info:
                # 应该使用德国的时区
                assert "Berlin" in tz_info["original_timezone"] or "Europe" in tz_info["original_timezone"]


@pytest.mark.api
class TestCombinedScenarios:
    """组合场景测试"""
    
    def test_lunar_and_timezone(self, client):
        """测试：农历输入 + 时区转换"""
        response = client.post("/api/v1/bazi/pan/display", json=COMBINED_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        # 验证同时包含农历转换和时区转换信息
        if "conversion_info" in data:
            assert data["conversion_info"].get("converted") == True
            assert "timezone_info" in data["conversion_info"]
    
    def test_cross_day_scenario(self, client):
        """测试：跨日场景"""
        response = client.post("/api/v1/bazi/pan/display", json=CROSS_DAY_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        # 如果跨日，应该包含转换信息
        if "conversion_info" in data:
            assert "timezone_info" in data["conversion_info"]


@pytest.mark.api
class TestResponseFormat:
    """响应格式测试"""
    
    def test_conversion_info_lunar(self, client):
        """测试：验证农历转换的 conversion_info"""
        response = client.post("/api/v1/bazi/pan/display", json=LUNAR_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "conversion_info" in data
        assert data["conversion_info"].get("converted") == True
        assert "lunar_to_solar" in data["conversion_info"]
    
    def test_conversion_info_timezone(self, client):
        """测试：验证时区转换的 conversion_info"""
        response = client.post("/api/v1/bazi/pan/display", json=TIMEZONE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "conversion_info" in data
        assert "timezone_info" in data["conversion_info"]
        assert "true_solar_time" in data["conversion_info"]
    
    def test_conversion_info_combined(self, client):
        """测试：验证组合场景的 conversion_info"""
        response = client.post("/api/v1/bazi/pan/display", json=COMBINED_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "conversion_info" in data
        assert data["conversion_info"].get("converted") == True
        assert "timezone_info" in data["conversion_info"]

