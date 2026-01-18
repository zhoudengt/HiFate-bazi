#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI entrypoint for the bazi rule microservice."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

from core.calculators.BaziCalculator import BaziCalculator  # noqa: E402

from .schemas import BaziRuleMatchRequest, BaziRuleMatchResponse  # noqa: E402


app = FastAPI(
    title="Bazi Rule Service",
    version="1.0.0",
    description="提供规则匹配能力的微服务，复用现有 RuleService 逻辑。",
)


@app.post("/rule/match", response_model=BaziRuleMatchResponse)
def match_rules(payload: BaziRuleMatchRequest) -> Dict[str, Any]:
    try:
        calculator = BaziCalculator(payload.solar_date, payload.solar_time, payload.gender)
        calculator.calculate()
        matched, unmatched = calculator.match_rules(
            rule_types=payload.rule_types,
            use_cache=payload.use_cache,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"规则匹配失败: {exc}") from exc

    # 将对象转换为可序列化的 dict
    matched_serializable: List[Dict[str, Any]] = [dict(rule) for rule in matched]
    unmatched_serializable: List[Dict[str, Any]] = [dict(item) for item in unmatched]

    return {
        "matched": matched_serializable,
        "unmatched": unmatched_serializable,
        "context": calculator.last_rule_context,
        "metadata": {
            "service": "bazi-rule-service",
            "version": "1.0.0",
        },
    }


@app.get("/healthz", tags=["health"])
def health_check() -> Dict[str, str]:
    return {"status": "ok"}

