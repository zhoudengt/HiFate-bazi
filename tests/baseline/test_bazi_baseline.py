#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baseline tests - ensure refactoring does not change API output.
Run tests/baseline/record_baseline.py to populate baseline_data.json, then these tests compare against it.
"""

import json
import os
import pytest


def _baseline_path():
    return os.path.join(os.path.dirname(__file__), "baseline_data.json")


def load_baseline():
    """Load baseline data from JSON file."""
    path = _baseline_path()
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _required_bazi_data_keys():
    """Required top-level keys in bazi calculate response data."""
    return ["year_pillar", "month_pillar", "day_pillar", "hour_pillar"]


class TestBaziBaseline:
    """Baseline tests - ensure refactoring does not change bazi calculate output."""

    def test_bazi_calculate_returns_success(self, client):
        """Verify /api/v1/bazi/calculate returns 200 and success=True."""
        response = client.post(
            "/api/v1/bazi/calculate",
            json={"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("success") is True
        assert "data" in body

    def test_bazi_calculate_data_has_required_keys(self, client):
        """Verify response data contains required pillar keys."""
        response = client.post(
            "/api/v1/bazi/calculate",
            json={"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
        )
        assert response.status_code == 200
        data = response.json().get("data")
        assert data is not None
        for key in _required_bazi_data_keys():
            assert key in data, f"Missing key: {key}"

    def test_bazi_calculate_consistency_with_baseline(self, client):
        """Verify bazi calculate output matches baseline when baseline is recorded."""
        baseline = load_baseline()
        if not baseline or "bazi_calculate" not in baseline:
            pytest.skip("No baseline_data.json or bazi_calculate section")
        for case in baseline["bazi_calculate"]:
            request_body = case.get("request")
            expected = case.get("expected_data")
            if not request_body:
                continue
            if expected is None:
                # No baseline recorded for this case: only check success and structure
                response = client.post("/api/v1/bazi/calculate", json=request_body)
                assert response.status_code == 200
                body = response.json()
                assert body.get("success") is True
                data = body.get("data")
                assert data is not None
                for key in _required_bazi_data_keys():
                    assert key in data
                continue
            response = client.post("/api/v1/bazi/calculate", json=request_body)
            assert response.status_code == 200, f"Request {request_body} failed: {response.text}"
            body = response.json()
            assert body.get("success") is True
            assert body.get("data") == expected, (
                f"Output changed for {request_body}. Re-run record_baseline.py to update baseline."
            )
