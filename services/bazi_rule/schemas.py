#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schemas for bazi-rule-service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class BaziRuleMatchRequest(BaseModel):
    solar_date: str = Field(..., description="阳历日期，格式 YYYY-MM-DD")
    solar_time: str = Field(..., description="阳历时间，格式 HH:MM")
    gender: str = Field('male', description="性别，male/female 或 男/女")
    rule_types: Optional[List[str]] = Field(None, description="需要匹配的规则类型列表")
    use_cache: bool = Field(False, description="是否使用规则服务缓存")

    @validator("gender")
    def _normalize_gender(cls, value: str) -> str:
        if value in ("男", "male"):
            return "male"
        if value in ("女", "female"):
            return "female"
        raise ValueError("gender must be male/female/男/女")


class BaziRuleMatchResponse(BaseModel):
    matched: List[Dict[str, Any]]
    unmatched: List[Dict[str, Any]]
    context: Dict[str, Any]
    metadata: Dict[str, Any]

