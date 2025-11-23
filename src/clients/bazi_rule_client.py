#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client helper for calling the bazi-rule-service."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class BaziRuleClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        self.base_url = (base_url or os.getenv("BAZI_RULE_SERVICE_URL", "")).rstrip("/")
        if not self.base_url:
            raise RuntimeError("BAZI_RULE_SERVICE_URL is not configured")
        self.timeout = timeout

    def match_rules(
        self,
        solar_date: str,
        solar_time: str,
        gender: str,
        rule_types: Optional[List[str]] = None,
        use_cache: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender,
            "rule_types": rule_types,
            "use_cache": use_cache,
        }

        url = f"{self.base_url}/rule/match"
        logger.debug("Calling bazi-rule-service: %s payload=%s", url, payload)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("bazi-rule-service returned %s: %s", exc.response.status_code, exc.response.text)
                raise

            data = response.json()
            return {
                "matched": data.get("matched", []),
                "unmatched": data.get("unmatched", []),
                "context": data.get("context", {}),
            }

    def health_check(self) -> bool:
        url = f"{self.base_url}/healthz"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            logger.exception("bazi-rule-service health check failed")
            return False

