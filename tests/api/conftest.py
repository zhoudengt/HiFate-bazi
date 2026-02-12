#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/api/ 目录的 conftest —— 提供 client 和 sample_bazi_request fixtures

注意: 这些测试需要 fastapi 和 httpx (TestClient 依赖) 已安装
"""
import pytest

# 尝试导入 FastAPI, 本地开发环境可能没有
fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("httpx", reason="httpx not installed (required for TestClient)")

from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    """创建 FastAPI TestClient"""
    try:
        from server.main import app
        return TestClient(app)
    except Exception as e:
        pytest.skip(f"Cannot create FastAPI TestClient: {e}")


@pytest.fixture
def sample_bazi_request():
    """标准八字请求参数"""
    return {
        "solar_date": "1992-01-15",
        "solar_time": "12:00",
        "gender": "male",
    }
