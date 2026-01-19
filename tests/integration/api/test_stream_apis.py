"""
流式 API 集成测试
"""
import pytest
import httpx
from typing import Iterator


class TestStreamAPIs:
    """测试流式接口"""
    
    def test_wuxing_proportion_stream(self, api_base_url: str, test_bazi_data: dict):
        """测试五行比例流式接口"""
        with httpx.stream(
            "POST",
            f"{api_base_url}/bazi/wuxing-proportion/stream",
            json=test_bazi_data,
            timeout=100.0
        ) as response:
            assert response.status_code == 200
            chunks = []
            for chunk in response.iter_text():
                if chunk:
                    chunks.append(chunk)
            assert len(chunks) > 0
    
    def test_daily_fortune_calendar_stream(self, api_base_url: str, test_bazi_data: dict):
        """测试每日运势日历流式接口"""
        payload = {
            **test_bazi_data,
            "date": "2025-01-15"
        }
        with httpx.stream(
            "POST",
            f"{api_base_url}/daily-fortune-calendar/stream",
            json=payload,
            timeout=100.0
        ) as response:
            assert response.status_code == 200
            chunks = []
            for chunk in response.iter_text():
                if chunk:
                    chunks.append(chunk)
            assert len(chunks) > 0
    
    def test_marriage_analysis_stream(self, api_base_url: str, test_bazi_data: dict):
        """测试感情婚姻分析流式接口"""
        with httpx.stream(
            "POST",
            f"{api_base_url}/bazi/marriage-analysis/stream",
            json=test_bazi_data,
            timeout=100.0
        ) as response:
            assert response.status_code == 200
            chunks = []
            for chunk in response.iter_text():
                if chunk:
                    chunks.append(chunk)
            assert response.status_code == 200
    
    def test_career_wealth_stream(self, api_base_url: str, test_bazi_data: dict):
        """测试事业财富分析流式接口"""
        with httpx.stream(
            "POST",
            f"{api_base_url}/career-wealth/stream",
            json=test_bazi_data,
            timeout=100.0
        ) as response:
            assert response.status_code == 200
            chunks = []
            for chunk in response.iter_text():
                if chunk:
                    chunks.append(chunk)
            assert response.status_code == 200
    
    def test_children_study_stream(self, api_base_url: str, test_bazi_data: dict):
        """测试子女学习分析流式接口"""
        with httpx.stream(
            "POST",
            f"{api_base_url}/children-study/stream",
            json=test_bazi_data,
            timeout=100.0
        ) as response:
            assert response.status_code == 200
            chunks = []
            for chunk in response.iter_text():
                if chunk:
                    chunks.append(chunk)
            assert response.status_code == 200
    
    def test_health_stream(self, api_base_url: str, test_bazi_data: dict):
        """测试身体健康分析流式接口"""
        with httpx.stream(
            "POST",
            f"{api_base_url}/health/stream",
            json=test_bazi_data,
            timeout=100.0
        ) as response:
            assert response.status_code == 200
            chunks = []
            for chunk in response.iter_text():
                if chunk:
                    chunks.append(chunk)
            assert response.status_code == 200
    
    def test_general_review_stream(self, api_base_url: str, test_bazi_data: dict):
        """测试总评分析流式接口"""
        with httpx.stream(
            "POST",
            f"{api_base_url}/general-review/stream",
            json=test_bazi_data,
            timeout=100.0
        ) as response:
            assert response.status_code == 200
            chunks = []
            for chunk in response.iter_text():
                if chunk:
                    chunks.append(chunk)
            assert response.status_code == 200
    
    def test_annual_report_stream(self, api_base_url: str, test_bazi_data: dict):
        """测试年运报告流式接口"""
        with httpx.stream(
            "POST",
            f"{api_base_url}/annual-report/stream",
            json=test_bazi_data,
            timeout=100.0
        ) as response:
            assert response.status_code == 200
            chunks = []
            for chunk in response.iter_text():
                if chunk:
                    chunks.append(chunk)
            assert response.status_code == 200
    
    def test_smart_fortune_stream(self, api_base_url: str):
        """测试智能运势分析流式接口"""
        params = {
            "question": "我今年的事业运势如何？",
            "year": 1990,
            "month": 5,
            "day": 15,
            "hour": 14,
            "gender": "male",
            "user_id": "test_user_001"
        }
        with httpx.stream(
            "GET",
            f"{api_base_url}/smart-fortune/smart-analyze-stream",
            params=params,
            timeout=100.0
        ) as response:
            assert response.status_code == 200
            chunks = []
            for chunk in response.iter_text():
                if chunk:
                    chunks.append(chunk)
            assert response.status_code == 200
