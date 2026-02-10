#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校验：大运流年/关键年份 与 流式接口所用数据 一致
- 用本地计算拿到 detail（dayun_sequence + liunian_sequence 含 relations）
- 用同一数据调用 SpecialLiunianService.get_special_liunians_batch(完整 dayun_sequence)
- 对比：detail 中有 relations 的流年必须全部出现在 special_liunians 中，且 dayun_step 一致

运行（项目根、venv 已激活）：
  PYTHONPATH=. .venv/bin/python scripts/verify_dayun_liunian_consistency.py
"""
import asyncio
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from datetime import datetime


def _get_detail_locally(solar_date: str, solar_time: str, gender: str, current_time: datetime):
    """仅用 core 本地计算，不依赖 DB/编排。"""
    from core.calculators.helpers import compute_local_detail
    result = compute_local_detail(
        solar_date, solar_time, gender,
        current_time=current_time,
        dayun_index=None,
        target_year=None,
    )
    details = result.get("details") or {}
    dayun_sequence = details.get("dayun_sequence") or []
    liunian_sequence = details.get("liunian_sequence") or []
    return dayun_sequence, liunian_sequence


def _expected_key_years(dayun_sequence, liunian_sequence):
    """从 detail 的流年里筛出有 relations 的 (year, dayun_step)。"""
    def year_to_step(year):
        for d in dayun_sequence:
            if d.get("stem") == "小运":
                continue
            ys, ye = d.get("year_start"), d.get("year_end")
            if ys is not None and ye is not None and ys <= year <= ye:
                return d.get("step")
        return None

    out = set()
    for li in liunian_sequence:
        if not (li.get("relations")):
            continue
        y = li.get("year")
        if y is None:
            continue
        step = year_to_step(y)
        out.add((y, step))
    return out


async def _get_special_liunians(solar_date, solar_time, gender, dayun_sequence, liunian_sequence, current_time):
    """调用 service：传完整 dayun_sequence 做匹配（与修复后编排一致）。"""
    from server.services.special_liunian_service import SpecialLiunianService
    return await SpecialLiunianService.get_special_liunians_batch(
        solar_date, solar_time, gender,
        dayun_sequence,  # 完整大运，不截断
        13,
        current_time,
        liunian_sequence=liunian_sequence,
    )


def main():
    solar_date = "1990-05-20"
    solar_time = "14:30"
    gender = "male"
    current_time = datetime(2025, 6, 1)

    # 1) 本地拿 detail
    dayun_sequence, liunian_sequence = _get_detail_locally(solar_date, solar_time, gender, current_time)
    if not dayun_sequence or not liunian_sequence:
        print("FAIL: 本地计算未返回大运或流年")
        return 1

    expected = _expected_key_years(dayun_sequence, liunian_sequence)

    # 2) 拿 special_liunians（与流式接口同源）
    special_list = asyncio.run(_get_special_liunians(
        solar_date, solar_time, gender,
        dayun_sequence, liunian_sequence, current_time,
    ))
    actual = set()
    for li in special_list:
        y = li.get("year")
        if y is not None:
            actual.add((y, li.get("dayun_step")))

    # 3) 对比
    missing = expected - actual
    wrong_step = []
    for (y, estep) in expected:
        asteps = [s for (ay, s) in actual if ay == y]
        if not asteps:
            continue
        if estep not in asteps:
            wrong_step.append((y, "expected_step", estep, "actual_steps", asteps))

    ok = not missing and not wrong_step
    print("【大运流年/关键年份一致性】")
    print(f"  detail 中有 relations 的流年 (year, dayun_step) 数量: {len(expected)}")
    print(f"  special_liunians.list 数量: {len(special_list)}")
    print(f"  special_liunians 中 (year, dayun_step) 数量: {len(actual)}")
    if expected:
        print(f"  detail 关键年份样例: {sorted(expected)[:10]}")
    if actual:
        print(f"  special_liunians 样例: {sorted(actual)[:10]}")
    if missing:
        print(f"  缺失（应在 special_liunians 中但未出现）: {sorted(missing)}")
    if wrong_step:
        print(f"  大运步数不一致: {wrong_step}")
    print("  结果:", "通过" if ok else "失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
