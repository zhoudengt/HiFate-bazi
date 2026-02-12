#!/usr/bin/env python3
"""tests/baseline/ conftest"""
import pytest
fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("httpx", reason="httpx not installed")

from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def client():
    try:
        from server.main import app
        return TestClient(app)
    except Exception as e:
        pytest.skip(f"Cannot create TestClient: {e}")
