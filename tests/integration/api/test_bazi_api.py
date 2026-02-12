"""

八字 API 集成测试
"""
import pytest; pytest.importorskip("grpc", reason="grpc not installed")
import pytest
import httpx
from typing import Dict, Any


class TestBaziInterface:
    """测试 /api/v1/bazi/interface 接口"""
    
    def test_bazi_interface_basic(self, api_base_url: str, test_bazi_data: dict):
        """测试基础八字接口"""
        response = httpx.post(
            f"{api_base_url}/bazi/interface",
            json=test_bazi_data,
            timeout=30.0
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
        assert data.get("success", True)


class TestBaziPanDisplay:
    """测试 /api/v1/bazi/pan/display 接口"""
    
    def test_bazi_pan_display(self, api_base_url: str, test_bazi_data: dict):
        """测试八字排盘显示"""
        response = httpx.post(
            f"{api_base_url}/bazi/pan/display",
            json=test_bazi_data,
            timeout=30.0
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data


class TestBaziFortuneDisplay:
    """测试 /api/v1/bazi/fortune/display 接口"""
    
    def test_bazi_fortune_display(self, api_base_url: str, test_bazi_data: dict):
        """测试运势显示"""
        response = httpx.post(
            f"{api_base_url}/bazi/fortune/display",
            json=test_bazi_data,
            timeout=30.0
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data


class TestBaziShengongMinggong:
    """测试 /api/v1/bazi/shengong-minggong 接口"""
    
    def test_shengong_minggong(self, api_base_url: str, test_bazi_data: dict):
        """测试身宫命宫"""
        response = httpx.post(
            f"{api_base_url}/bazi/shengong-minggong",
            json=test_bazi_data,
            timeout=30.0
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data


class TestBaziRizhuLiujiazi:
    """测试 /api/v1/bazi/rizhu-liujiazi 接口"""
    
    def test_rizhu_liujiazi(self, api_base_url: str, test_bazi_data: dict):
        """测试日柱六甲子"""
        response = httpx.post(
            f"{api_base_url}/bazi/rizhu-liujiazi",
            json=test_bazi_data,
            timeout=30.0
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "data" in data
