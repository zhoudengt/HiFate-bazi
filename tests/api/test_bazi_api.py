#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API tests for bazi endpoints."""

import pytest


class TestBaziAPI:
    """Basic API tests for /api/v1/bazi/*."""

    def test_bazi_calculate_success(self, client, sample_bazi_request):
        """POST /api/v1/bazi/calculate returns 200 and valid structure."""
        response = client.post("/api/v1/bazi/calculate", json=sample_bazi_request)
        assert response.status_code == 200
        body = response.json()
        assert body.get("success") is True
        assert "data" in body

    def test_bazi_calculate_invalid_date(self, client):
        """POST /api/v1/bazi/calculate with invalid date returns 422 or 400."""
        response = client.post(
            "/api/v1/bazi/calculate",
            json={"solar_date": "invalid", "solar_time": "12:00", "gender": "male"},
        )
        assert response.status_code in (400, 422)

    def test_bazi_calculate_invalid_gender(self, client):
        """POST /api/v1/bazi/calculate with invalid gender returns 422 or 400."""
        response = client.post(
            "/api/v1/bazi/calculate",
            json={"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "invalid"},
        )
        assert response.status_code in (400, 422)
