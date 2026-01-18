#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI entrypoint for bazi-core-service.

该服务负责八字排盘的纯计算逻辑，不包含规则匹配、聚合等扩展能力。
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

from core.calculators.bazi_core_calculator import BaziCoreCalculator  # noqa: E402

from .schemas import BaziCoreRequest, BaziCoreResponse  # noqa: E402


app = FastAPI(
    title="Bazi Core Service",
    version="1.0.0",
    description="提供八字排盘核心计算能力的微服务。",
)


@app.post("/core/calc-bazi", response_model=BaziCoreResponse)
def calc_bazi(payload: BaziCoreRequest) -> Dict[str, Any]:
    calculator = BaziCoreCalculator(
        solar_date=payload.solar_date,
        solar_time=payload.solar_time,
        gender=payload.gender,
    )
    result = calculator.calculate()
    if result is None:
        raise HTTPException(status_code=500, detail="八字排盘失败")

    return {
        **result,
        "metadata": {
            "service": "bazi-core-service",
            "version": "1.0.0",
        },
    }


@app.get("/healthz", tags=["health"])
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


