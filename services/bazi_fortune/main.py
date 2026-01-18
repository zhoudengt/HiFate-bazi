#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI entrypoint for the bazi fortune (dayun/liunian) microservice."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

from core.calculators.helpers import compute_local_detail  # noqa: E402

from .schemas import BaziFortuneRequest, BaziFortuneResponse  # noqa: E402


app = FastAPI(
    title="Bazi Fortune Service",
    version="1.0.0",
    description="提供大运、流年等详细运势计算能力的微服务。",
)


@app.post("/fortune/dayun-liunian", response_model=BaziFortuneResponse)
def calc_dayun_liunian(payload: BaziFortuneRequest) -> Dict[str, Any]:
    try:
        detail = compute_local_detail(
            solar_date=payload.solar_date,
            solar_time=payload.solar_time,
            gender=payload.gender,
            current_time=payload.parse_current_time(),
        )
    except ValueError as exc:  # 参数或计算错误
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # 其他未捕获错误
        raise HTTPException(status_code=500, detail=f"运势计算失败: {exc}") from exc

    return {
        "detail": detail,
        "metadata": {
            "service": "bazi-fortune-service",
            "version": "1.0.0",
        },
    }


@app.get("/healthz", tags=["health"])
def health_check() -> Dict[str, str]:
    return {"status": "ok"}

