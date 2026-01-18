#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helper utilities for fortune (dayun/liunian) calculations."""

from __future__ import annotations

import contextlib
import io
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from core.calculators.bazi_calculator_docs import BaziCalculator as DocsBaziCalculator

# 导入格式化工具类
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "server", "utils"))
from bazi_formatters import BaziResultFormatter

if TYPE_CHECKING:  # pragma: no cover
    from core.calculators.BaziCalculator import BaziCalculator as ToolBaziCalculator


def format_detail_result(detail_result: Dict[str, Any], bazi_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format detail result into response structure expected by API/clients.
    
    使用统一的格式化工具类，确保格式一致性
    """
    return BaziResultFormatter.format_detail_result(detail_result, bazi_result)


def compute_local_detail(
    solar_date: str,
    solar_time: str,
    gender: str,
    current_time: Optional[datetime] = None,
    dayun_index: Optional[int] = None,
    target_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute fortune detail locally using legacy calculator."""
    from core.calculators.BaziCalculator import BaziCalculator as ToolBaziCalculator  # 延迟导入避免循环依赖

    calculator = ToolBaziCalculator(solar_date, solar_time, gender)
    bazi_result = calculator.calculate()
    if not bazi_result:
        raise ValueError("八字计算失败，请检查输入参数")

    fortune_calc = DocsBaziCalculator(solar_date, solar_time, gender=gender)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        detail_raw = fortune_calc.calculate_dayun_liunian(
            current_time=current_time, 
            dayun_index=dayun_index,
            target_year=target_year
        )
    if not detail_raw:
        raise ValueError("大运流年计算失败")

    return format_detail_result(detail_raw, bazi_result)

