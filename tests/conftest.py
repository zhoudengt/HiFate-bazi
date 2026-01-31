#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest fixtures for HiFate-bazi tests.
"""

import os
import sys
import pytest

# Ensure project root is on path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture
def client():
    """FastAPI TestClient for API tests."""
    from fastapi.testclient import TestClient
    from server.main import app
    return TestClient(app)


@pytest.fixture
def sample_bazi_request():
    """Sample request body for /api/v1/bazi/calculate."""
    return {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male",
    }


@pytest.fixture
def sample_bazi_requests():
    """Multiple sample requests for baseline tests."""
    return [
        {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
        {"solar_date": "1985-06-20", "solar_time": "08:30", "gender": "female"},
    ]
