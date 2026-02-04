#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest 全局配置

提供测试所需的公共 fixtures 和配置。
"""

import os
import sys
import pytest
from typing import Dict, Any, Generator

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置测试环境
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DEBUG", "True")


# ==================== 应用相关 Fixtures ====================

@pytest.fixture(scope="session")
def app():
    """创建 FastAPI 应用实例（用于测试）"""
    from server.main import app
    return app


@pytest.fixture(scope="session")
def client(app):
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client


# ==================== 八字测试数据 Fixtures ====================

@pytest.fixture
def sample_bazi_request() -> Dict[str, Any]:
    """标准八字计算请求数据"""
    return {
        "solar_date": "1990-01-15",
        "solar_time": "12:30",
        "gender": "male",
        "calendar_type": "solar"
    }


@pytest.fixture
def sample_bazi_result() -> Dict[str, Any]:
    """标准八字计算结果数据（用于 mock）"""
    return {
        "success": True,
        "data": {
            "basic_info": {
                "solar_date": "1990-01-15",
                "solar_time": "12:30",
                "gender": "male"
            },
            "bazi_pillars": {
                "year": {"stem": "己", "branch": "巳"},
                "month": {"stem": "丁", "branch": "丑"},
                "day": {"stem": "甲", "branch": "子"},
                "hour": {"stem": "庚", "branch": "午"}
            }
        }
    }


# ==================== Mock Fixtures ====================

@pytest.fixture
def mock_redis(mocker):
    """Mock Redis 客户端"""
    mock = mocker.patch("shared.config.redis.get_redis_client")
    mock.return_value = mocker.MagicMock()
    return mock


@pytest.fixture
def mock_mysql(mocker):
    """Mock MySQL 连接"""
    mock = mocker.patch("shared.config.database.get_connection")
    mock.return_value = mocker.MagicMock()
    return mock


# ==================== 测试标记 ====================

def pytest_configure(config):
    """配置自定义标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "api: API 测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
