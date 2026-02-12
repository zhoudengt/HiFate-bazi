#!/usr/bin/env python3
"""tests/e2e/ conftest - E2E 测试需要实际运行的服务"""
import pytest
import requests

def _server_running():
    try:
        r = requests.get("http://localhost:8001/api/v1/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False

@pytest.fixture(autouse=True)
def require_server():
    if not _server_running():
        pytest.skip("E2E tests require a running server at localhost:8001")
