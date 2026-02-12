#!/usr/bin/env python3
"""tests/features/ conftest"""
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
        pytest.skip("Feature tests require a running server at localhost:8001")
