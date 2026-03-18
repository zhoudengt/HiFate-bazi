#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理结论格式化器（所有领域共用）

将 InferenceResult 转为 LLM 可读的中文文本，
追加到原有格式化数据之后。
"""

from __future__ import annotations
from typing import Optional
from core.inference.models import InferenceResult


CATEGORY_LABELS = {
    'spouse_star': '配偶星推理',
    'marriage_palace': '婚姻宫推理',
    'dynamic_balance': '大运力场推理',
    'marriage_timing': '婚恋时机推理',
    'health_organ': '脏腑推理',
    'health_timing': '健康时机推理',
    'career_star': '事业星推理',
    'career_timing': '事业时机推理',
    'wealth_star': '财富星推理',
    'db_rule': '综合推理',
    'day_pillar_judgment': '日柱断语',
    'day_branch_judgment': '日支断语',
    'spouse_appearance': '配偶外貌特征',
    'ten_gods_judgment': '十神断语',
    'stem_pattern_judgment': '天干组合断语',
    'branch_pattern_judgment': '地支组合断语',
    'deity_judgment': '神煞断语',
    'general_judgment': '综合断语',
    'bazi_pattern_judgment': '八字格局断语',
    'month_branch_judgment': '月支断语',
    'year_branch_judgment': '年支断语',
    'year_stem_judgment': '年干断语',
    'element_judgment': '五行断语',
    'hour_pillar_judgment': '时柱断语',
    'year_pillar_judgment': '年柱断语',
    'nayin_judgment': '纳音断语',
    'lunar_birthday_judgment': '农历生日断语',
    'luck_cycle_judgment': '运程断语',
    'year_event_judgment': '流年事件断语',
    'formula_judgment': '命理公式断语',
}


def format_inference_conclusions(result: InferenceResult) -> str:
    """将推理结论格式化为 LLM 可读文本"""
    if not result or not result.has_conclusions():
        return ''

    lines = ['【推理结论】（由推理引擎计算得出，请直接采用）']

    categories_seen = []
    for chain in result.chains:
        if chain.category not in categories_seen:
            categories_seen.append(chain.category)

    for cat in categories_seen:
        cat_chains = result.get_chains_by_category(cat)
        if not cat_chains:
            continue

        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"〔{label}〕")

        for chain in cat_chains:
            parts = []
            if chain.condition:
                parts.append(chain.condition)
            if chain.conclusion:
                parts.append(f"→ {chain.conclusion}")

            suffix_parts = []
            if chain.time_range:
                suffix_parts.append(chain.time_range)
            if chain.source:
                suffix_parts.append(f"据{chain.source}")
            if chain.confidence >= 0.85:
                suffix_parts.append("可信度高")
            elif chain.confidence < 0.7:
                suffix_parts.append("仅供参考")

            line = '  ' + '，'.join(parts[:2])
            if suffix_parts:
                line += f"（{'，'.join(suffix_parts)}）"
            lines.append(line)

    return '\n'.join(lines)


def format_with_inference(
    original_formatted: str,
    inference_result: Optional[InferenceResult]
) -> str:
    """
    将推理结论追加到原有格式化文本之后。
    
    如果推理结果为空，返回原文不变。
    所有领域通用：原格式化文本 + 推理结论。
    """
    if not inference_result or not inference_result.has_conclusions():
        return original_formatted

    conclusions_text = format_inference_conclusions(inference_result)
    if not conclusions_text:
        return original_formatted

    return original_formatted + '\n' + conclusions_text
