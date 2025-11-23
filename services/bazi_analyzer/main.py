#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI entrypoint for the bazi analyzer microservice."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

from src.tool.BaziCalculator import BaziCalculator  # noqa: E402
from src.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer  # noqa: E402

from .schemas import AnalyzerType, BaziAnalyzerRequest, BaziAnalyzerResponse  # noqa: E402


app = FastAPI(
    title="Bazi Analyzer Service",
    version="1.0.0",
    description="提供八字相关分析能力的微服务（当前支持日柱性别分析）。",
)


@app.post("/analyzer/run", response_model=BaziAnalyzerResponse)
def run_analyzers(payload: BaziAnalyzerRequest) -> Dict[str, Any]:
    try:
        calculator = BaziCalculator(payload.solar_date, payload.solar_time, payload.gender)
        bazi_result = calculator.calculate()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"八字排盘失败: {exc}") from exc

    if not bazi_result:
        raise HTTPException(status_code=500, detail="八字排盘失败")

    results: Dict[str, Any] = {}

    for analyzer_type in payload.analysis_types:
        if analyzer_type == AnalyzerType.RIZHU_GENDER:
            analyzer = RizhuGenderAnalyzer(calculator.bazi_pillars, calculator.gender)
            analysis = analyzer.analyze_rizhu_gender()
            analysis["formatted_text"] = analyzer.get_formatted_output()
            results[analyzer_type] = analysis
        else:
            results[analyzer_type] = {
                "error": f"unsupported analyzer type: {analyzer_type}"
            }

    return {
        "results": results,
        "metadata": {
            "service": "bazi-analyzer-service",
            "version": "1.0.0",
        },
    }


@app.get("/healthz", tags=["health"])
def health_check() -> Dict[str, str]:
    return {"status": "ok"}

