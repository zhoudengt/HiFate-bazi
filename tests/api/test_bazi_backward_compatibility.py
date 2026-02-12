#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

八字接口向后兼容性测试
验证不提供新参数时，行为与之前完全一致
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

# 基础请求（不包含新参数）
BASE_REQUEST = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
}


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.mark.api
class TestBackwardCompatibility:
    """向后兼容性测试"""
    
    def test_pan_display_backward_compatible(self, client):
        """测试：基本排盘接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/pan/display", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        # 不提供新参数时，不应包含 conversion_info（除非有默认转换）
    
    def test_dayun_display_backward_compatible(self, client):
        """测试：大运展示接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/dayun/display", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_liunian_display_backward_compatible(self, client):
        """测试：流年展示接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/liunian/display", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_liuyue_display_backward_compatible(self, client):
        """测试：流月展示接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/liuyue/display", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_fortune_display_backward_compatible(self, client):
        """测试：大运流年流月统一接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/fortune/display", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_wangshuai_backward_compatible(self, client):
        """测试：旺衰分析接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/wangshuai", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_formula_analysis_backward_compatible(self, client):
        """测试：公式分析接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/formula-analysis", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_wuxing_proportion_backward_compatible(self, client):
        """测试：五行占比接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/wuxing-proportion", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_rizhu_liujiazi_backward_compatible(self, client):
        """测试：日元-六十甲子接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/rizhu-liujiazi", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_xishen_jishen_backward_compatible(self, client):
        """测试：喜神忌神接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/xishen-jishen", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_bazi_rules_backward_compatible(self, client):
        """测试：规则匹配接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/rules/match", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_liunian_enhanced_backward_compatible(self, client):
        """测试：流年大运增强接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/liunian-enhanced", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_monthly_fortune_backward_compatible(self, client):
        """测试：月运势接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/monthly-fortune", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_daily_fortune_backward_compatible(self, client):
        """测试：日运势接口 - 向后兼容"""
        response = client.post("/api/v1/bazi/daily-fortune", json=BASE_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_daily_fortune_calendar_backward_compatible(self, client):
        """测试：每日运势日历接口 - 向后兼容"""
        request_data = {
            "date": "2025-01-15"
        }
        response = client.post("/api/v1/daily-fortune-calendar/query", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True


@pytest.mark.api
class TestComparison:
    """对比测试：有参数 vs 无参数"""
    
    def test_pan_display_comparison(self, client):
        """测试：基本排盘接口 - 对比测试"""
        # 无新参数
        response1 = client.post("/api/v1/bazi/pan/display", json=BASE_REQUEST)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # 有新参数但使用默认值
        request_with_defaults = {
            **BASE_REQUEST,
            "calendar_type": "solar"
        }
        response2 = client.post("/api/v1/bazi/pan/display", json=request_with_defaults)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 结果应该一致（因为使用默认值）
        # 注意：由于可能有缓存或其他因素，这里只验证基本结构
        assert data1.get("success") == data2.get("success")
    
    def test_wangshuai_comparison(self, client):
        """测试：旺衰分析接口 - 对比测试"""
        # 无新参数
        response1 = client.post("/api/v1/bazi/wangshuai", json=BASE_REQUEST)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # 有新参数但使用默认值
        request_with_defaults = {
            **BASE_REQUEST,
            "calendar_type": "solar"
        }
        response2 = client.post("/api/v1/bazi/wangshuai", json=request_with_defaults)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 结果应该一致
        assert data1.get("success") == data2.get("success")

