#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helper utilities for fortune (dayun/liunian) calculations."""

from __future__ import annotations

import contextlib
import io
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from src.bazi_fortune.bazi_calculator_docs import BaziCalculator as DocsBaziCalculator

if TYPE_CHECKING:  # pragma: no cover
    from src.tool.BaziCalculator import BaziCalculator as ToolBaziCalculator


def format_detail_result(detail_result: Dict[str, Any], bazi_result: Dict[str, Any]) -> Dict[str, Any]:
    """Format detail result into response structure expected by API/clients."""
    basic_info = detail_result.get('basic_info', {})
    bazi_pillars = detail_result.get('bazi_pillars', {})
    details = detail_result.get('details', {})

    current_time = basic_info.get('current_time')
    if isinstance(current_time, datetime):
        current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    elif current_time:
        current_time_str = str(current_time)
    else:
        current_time_str = ''

    formatted_basic_info = {
        "solar_date": basic_info.get('solar_date', ''),
        "solar_time": basic_info.get('solar_time', ''),
        "lunar_date": basic_info.get('lunar_date', {}),
        "gender": basic_info.get('gender', ''),
        "current_time": current_time_str,
        "adjusted_solar_date": basic_info.get('adjusted_solar_date', ''),
        "adjusted_solar_time": basic_info.get('adjusted_solar_time', ''),
        "is_zi_shi_adjusted": basic_info.get('is_zi_shi_adjusted', False),
    }

    formatted_pillars = {}
    for pillar_type in ['year', 'month', 'day', 'hour']:
        pillar_details = details.get(pillar_type, {})
        formatted_pillars[pillar_type] = {
            "stem": bazi_pillars.get(pillar_type, {}).get('stem', ''),
            "branch": bazi_pillars.get(pillar_type, {}).get('branch', ''),
            "main_star": pillar_details.get('main_star', ''),
            "hidden_stars": pillar_details.get('hidden_stars', []),
            "sub_stars": pillar_details.get('sub_stars', pillar_details.get('hidden_stars', [])),
            "hidden_stems": pillar_details.get('hidden_stems', []),
            "star_fortune": pillar_details.get('star_fortune', ''),
            "self_sitting": pillar_details.get('self_sitting', ''),
            "kongwang": pillar_details.get('kongwang', ''),
            "nayin": pillar_details.get('nayin', ''),
            "deities": pillar_details.get('deities', []),
        }

    dayun_info = details.get('dayun', {})
    liunian_info = details.get('liunian', {})
    qiyun_info = details.get('qiyun', {})
    jiaoyun_info = details.get('jiaoyun', {})

    def _format_sequence(seq_key: str) -> list:
        return details.get(seq_key, [])

    return {
        "basic_info": formatted_basic_info,
        "bazi_pillars": formatted_pillars,
        "details": details,
        "ten_gods_stats": bazi_result.get('ten_gods_stats', {}),
        "elements": bazi_result.get('elements', {}),
        "element_counts": bazi_result.get('element_counts', {}),
        "relationships": bazi_result.get('relationships', {}),
        "dayun_info": {
            "current_dayun": dayun_info,
            "next_dayun": {},
            "qiyun_date": qiyun_info.get('date', ''),
            "qiyun_age": qiyun_info.get('age_display', ''),
            "qiyun": qiyun_info,
            "jiaoyun_date": jiaoyun_info.get('date', ''),
            "jiaoyun_age": jiaoyun_info.get('age_display', ''),
            "jiaoyun": jiaoyun_info,
        },
        "liunian_info": {
            "current_liunian": liunian_info,
            "next_liunian": {},
        },
        "dayun_sequence": _format_sequence('dayun_sequence'),
        "liunian_sequence": _format_sequence('liunian_sequence'),
        "liuyue_sequence": _format_sequence('liuyue_sequence'),
        "liuri_sequence": _format_sequence('liuri_sequence'),
        "liushi_sequence": _format_sequence('liushi_sequence'),
    }


def compute_local_detail(
    solar_date: str,
    solar_time: str,
    gender: str,
    current_time: Optional[datetime] = None,
    dayun_index: Optional[int] = None,
    target_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute fortune detail locally using legacy calculator."""
    from src.tool.BaziCalculator import BaziCalculator as ToolBaziCalculator  # 延迟导入避免循环依赖

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

