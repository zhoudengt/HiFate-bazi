#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schemas for bazi-analyzer-service."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field, validator


class AnalyzerType(str):
    RIZHU_GENDER = "rizhu_gender"


class BaziAnalyzerRequest(BaseModel):
    solar_date: str = Field(..., description="阳历日期，格式 YYYY-MM-DD")
    solar_time: str = Field(..., description="阳历时间，格式 HH:MM")
    gender: str = Field('male', description="性别，male/female 或 男/女")
    analysis_types: List[str] = Field(
        default_factory=lambda: [AnalyzerType.RIZHU_GENDER],
        description="需要执行的分析类型列表"
    )

    @validator("gender")
    def _normalize_gender(cls, value: str) -> str:
        if value in ("男", "male"):
            return "male"
        if value in ("女", "female"):
            return "female"
        raise ValueError("gender must be male/female/男/女")


class BaziAnalyzerResponse(BaseModel):
    results: Dict[str, Any]
    metadata: Dict[str, Any]

