#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client helper for calling the bazi-core-service."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class BaziCoreClient:
    """Lightweight HTTP client for the bazi-core-service."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        self.base_url = (base_url or os.getenv("BAZI_CORE_SERVICE_URL", "")).rstrip("/")
        if not self.base_url:
            raise RuntimeError("BAZI_CORE_SERVICE_URL is not configured")
        self.timeout = timeout

    def calculate_bazi(self, solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        payload = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender,
        }

        url = f"{self.base_url}/core/calc-bazi"
        logger.debug("Calling bazi-core-service: %s payload=%s", url, payload)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("bazi-core-service returned %s: %s", exc.response.status_code, exc.response.text)
                raise

            data: Dict[str, Any] = response.json()
            # Remove metadata helper field to match local calculate() signature
            data.pop("metadata", None)
            return data

    def health_check(self) -> bool:
        url = f"{self.base_url}/healthz"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            logger.exception("bazi-core-service health check failed")
            return False

