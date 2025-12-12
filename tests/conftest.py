#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest 全局配置

提供：
- 共享 fixtures
- 测试钩子
- 全局配置
"""

import pytest
import sys
import os
from typing import Generator, Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


# ==================== 应用和客户端 Fixtures ====================

@pytest.fixture(scope="session")
def app():
    """
    创建 FastAPI 应用实例（整个测试会话共享）
    
    Returns:
        FastAPI 应用实例
    """
    from server.main import app
    return app


@pytest.fixture(scope="session")
def client(app):
    """
    创建测试客户端（整个测试会话共享）
    
    Args:
        app: FastAPI 应用实例
        
    Returns:
        TestClient 实例
    """
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(scope="function")
async def async_client(app):
    """
    创建异步测试客户端（每个测试函数独立）
    
    Args:
        app: FastAPI 应用实例
        
    Yields:
        AsyncClient 实例
    """
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ==================== 数据 Fixtures ====================

@pytest.fixture(scope="function")
def sample_date() -> str:
    """
    示例日期
    
    Returns:
        日期字符串 YYYY-MM-DD
    """
    return "2025-12-11"


@pytest.fixture(scope="function")
def sample_bazi_request() -> Dict[str, Any]:
    """
    示例八字请求
    
    Returns:
        八字请求字典
    """
    return {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male"
    }


@pytest.fixture(scope="function")
def sample_calendar_request() -> Dict[str, Any]:
    """
    示例万年历请求
    
    Returns:
        万年历请求字典
    """
    return {
        "date": "2025-12-11"
    }


@pytest.fixture(scope="function")
def expected_calendar_data() -> Dict[str, Any]:
    """
    预期万年历数据
    
    Returns:
        预期数据字典
    """
    return {
        "lunar_date": "农历十月廿二",
        "shengxiao": "蛇",
        "xingzuo": "射手",
        "ganzhi": {
            "year": "乙巳",
            "month": "戊子",
            "day": "甲寅"
        }
    }


# ==================== Mock Fixtures ====================

@pytest.fixture(scope="function")
def mock_db_connection():
    """
    Mock 数据库连接
    
    Yields:
        MagicMock 数据库连接对象
    """
    from unittest.mock import MagicMock
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    yield mock_conn


@pytest.fixture(scope="function")
def mock_redis_client():
    """
    Mock Redis 客户端
    
    Yields:
        MagicMock Redis 客户端对象
    """
    from unittest.mock import MagicMock
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    yield mock_redis


@pytest.fixture(scope="function")
def mock_external_api():
    """
    Mock 外部 API 响应
    
    Yields:
        MagicMock API 响应对象
    """
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "data": {}}
    yield mock_response


# ==================== Service Fixtures ====================

@pytest.fixture(scope="function")
def calendar_service():
    """
    万年历服务实例
    
    Returns:
        CalendarAPIService 实例
    """
    from server.services.calendar_api_service import CalendarAPIService
    return CalendarAPIService()


@pytest.fixture(scope="function")
def bazi_service():
    """
    八字服务实例
    
    Returns:
        BaziService 实例
    """
    from server.services.bazi_service import BaziService
    return BaziService()


# ==================== Pytest Hooks ====================

def pytest_configure(config):
    """
    pytest 配置钩子
    
    在 pytest 初始化时调用
    """
    # 添加自定义标记说明
    config.addinivalue_line("markers", "slow: 标记为慢速测试，可通过 -m 'not slow' 跳过")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "api: API 测试")


def pytest_collection_modifyitems(config, items):
    """
    修改测试收集
    
    自动为测试添加标记
    """
    for item in items:
        # 根据路径自动添加标记
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "api" in item.nodeid:
            item.add_marker(pytest.mark.api)


def pytest_runtest_setup(item):
    """
    测试运行前钩子
    
    可在此处添加测试前的准备工作
    """
    pass


def pytest_runtest_teardown(item):
    """
    测试运行后钩子
    
    可在此处添加测试后的清理工作
    """
    pass


# ==================== 辅助函数 ====================

def assert_response_success(response: Dict[str, Any]):
    """
    断言响应成功
    
    Args:
        response: API 响应字典
    """
    assert response.get("success") == True, f"Expected success=True, got {response}"
    assert response.get("error") is None, f"Unexpected error: {response.get('error')}"


def assert_response_failure(response: Dict[str, Any]):
    """
    断言响应失败
    
    Args:
        response: API 响应字典
    """
    assert response.get("success") == False, f"Expected success=False, got {response}"
    assert response.get("error") is not None, "Expected error message"
