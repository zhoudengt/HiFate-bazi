#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pydantic schema definitions for bazi-core-service."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaziCoreRequest(BaseModel):
    solar_date: str = Field(..., description="阳历日期，格式 YYYY-MM-DD")
    solar_time: str = Field(..., description="阳历时间，格式 HH:MM")
    gender: str = Field('male', description="性别，male/female")


class BaziCoreResponse(BaseModel):
    basic_info: Dict[str, Any]
    bazi_pillars: Dict[str, Dict[str, str]]
    details: Dict[str, Dict[str, Any]]
    ten_gods_stats: Dict[str, Any]
    elements: Dict[str, Any]
    element_counts: Dict[str, int]
    relationships: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


