"""
pytest 配置和共享 fixtures
"""
import pytest
import os
import sys
from typing import Generator

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 测试配置
TEST_BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8001")
TEST_API_BASE = f"{TEST_BASE_URL}/api/v1"


@pytest.fixture
def api_base_url() -> str:
    """API 基础 URL"""
    return TEST_API_BASE


@pytest.fixture
def test_bazi_data() -> dict:
    """标准测试八字数据"""
    return {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male"
    }


@pytest.fixture
def test_bazi_data_female() -> dict:
    """女性测试八字数据"""
    return {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "female"
    }
