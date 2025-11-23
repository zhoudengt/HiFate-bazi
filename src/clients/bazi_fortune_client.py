#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client helper for calling the bazi-fortune-service."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class BaziFortuneClient:
    """Lightweight HTTP client for the bazi-fortune-service."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 20.0) -> None:
        self.base_url = (base_url or os.getenv("BAZI_FORTUNE_SERVICE_URL", "")).rstrip("/")
        if not self.base_url:
            raise RuntimeError("BAZI_FORTUNE_SERVICE_URL is not configured")
        self.timeout = timeout

    def calculate_detail(self, solar_date: str, solar_time: str, gender: str, current_time: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender,
        }
        if current_time:
            payload["current_time"] = current_time

        url = f"{self.base_url}/fortune/dayun-liunian"
        logger.debug("Calling bazi-fortune-service: %s payload=%s", url, payload)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("bazi-fortune-service returned %s: %s", exc.response.status_code, exc.response.text)
                raise

            data: Dict[str, Any] = response.json()
            detail = data.get("detail")
            if detail is None:
                raise RuntimeError("bazi-fortune-service response missing 'detail'")
            return detail

    def health_check(self) -> bool:
        url = f"{self.base_url}/healthz"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            logger.exception("bazi-fortune-service health check failed")
            return False

