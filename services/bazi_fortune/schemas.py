#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pydantic schema definitions for bazi-fortune-service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class BaziFortuneRequest(BaseModel):
    solar_date: str = Field(..., description="阳历日期，格式 YYYY-MM-DD")
    solar_time: str = Field(..., description="阳历时间，格式 HH:MM")
    gender: str = Field('male', description="性别，male/female 或 男/女")
    current_time: Optional[str] = Field(
        None,
        description="当前时间，ISO 8601 格式，默认使用服务器当前时间"
    )

    @validator("gender")
    def _normalize_gender(cls, value: str) -> str:
        if value in ("男", "male"):
            return "male"
        if value in ("女", "female"):
            return "female"
        raise ValueError("gender must be male/female/男/女")

    def parse_current_time(self) -> Optional[datetime]:
        if not self.current_time:
            return None
        try:
            return datetime.fromisoformat(self.current_time)
        except ValueError as exc:
            raise ValueError("current_time must be ISO format, e.g. 2025-01-01T12:30") from exc


class BaziFortuneResponse(BaseModel):
    detail: Dict[str, Any]
    metadata: Dict[str, Any]

