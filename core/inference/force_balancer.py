#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态力场平衡器

在原局五行力量基础上，将大运干支加入后重算五行力量分布。
这是推理引擎的物理引擎——所有领域都需要用它来计算
各大运期间的实际五行强弱变化。
"""

from __future__ import annotations
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS, HIDDEN_STEMS
from core.data.relations import (
    BRANCH_CHONG, BRANCH_LIUHE, BRANCH_XING, BRANCH_HAI,
    STEM_HE, BRANCH_SANHE_GROUPS, BRANCH_SANHUI_GROUPS,
)

logger = logging.getLogger(__name__)

WUXING_SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
WUXING_KE = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}

STEM_HE_TRANSFORM = {
    ('甲', '己'): '土', ('己', '甲'): '土',
    ('乙', '庚'): '金', ('庚', '乙'): '金',
    ('丙', '辛'): '水', ('辛', '丙'): '水',
    ('丁', '壬'): '木', ('壬', '丁'): '木',
    ('戊', '癸'): '火', ('癸', '戊'): '火',
}

BRANCH_LIUHE_TRANSFORM = {
    ('子', '丑'): '土', ('丑', '子'): '土',
    ('寅', '亥'): '木', ('亥', '寅'): '木',
    ('卯', '戌'): '火', ('戌', '卯'): '火',
    ('辰', '酉'): '金', ('酉', '辰'): '金',
    ('巳', '申'): '水', ('申', '巳'): '水',
    ('午', '未'): '火', ('未', '午'): '火',
}


@dataclass
class PeriodBalance:
    """某个大运期间的力场快照"""
    dayun_ganzhi: str = ''
    dayun_step: int = 0
    age_display: str = ''
    wuxing_power: Dict[str, float] = field(default_factory=dict)
    wuxing_delta: Dict[str, float] = field(default_factory=dict)
    activated_relations: List[Dict[str, Any]] = field(default_factory=list)
    spouse_star_power_change: float = 0.0
    marriage_palace_activated: bool = False
    summary: str = ''


class DynamicForceBalancer:
    """动态力场平衡器"""

    STEM_POWER = 1.5
    BRANCH_MAIN_POWER = 1.5
    BRANCH_HIDDEN_POWER = 0.5

    @classmethod
    def calculate_natal_wuxing_power(cls, bazi_pillars: Dict[str, Dict[str, str]]) -> Dict[str, float]:
        """计算原局五行力量（基于天干地支及藏干）"""
        power = {'木': 0.0, '火': 0.0, '土': 0.0, '金': 0.0, '水': 0.0}
        for pillar_name in ['year', 'month', 'day', 'hour']:
            p = bazi_pillars.get(pillar_name, {})
            stem = p.get('stem', '')
            branch = p.get('branch', '')
            if stem and stem in STEM_ELEMENTS:
                power[STEM_ELEMENTS[stem]] += cls.STEM_POWER
            if branch and branch in BRANCH_ELEMENTS:
                power[BRANCH_ELEMENTS[branch]] += cls.BRANCH_MAIN_POWER
                for hidden in HIDDEN_STEMS.get(branch, []):
                    elem_char = hidden[-1] if len(hidden) >= 2 else ''
                    elem_map = {'木': '木', '火': '火', '土': '土', '金': '金', '水': '水'}
                    if elem_char in elem_map:
                        power[elem_map[elem_char]] += cls.BRANCH_HIDDEN_POWER
        return power

    @classmethod
    def calculate_period_balance(
        cls,
        natal_power: Dict[str, float],
        natal_branches: List[str],
        dayun_stem: str,
        dayun_branch: str,
        day_branch: str = '',
        spouse_star_element: str = '',
        natal_stems: Optional[List[str]] = None,
    ) -> PeriodBalance:
        """
        将大运干支加入原局，计算该大运期间的五行力量变化。
        包含合化增益和冲散减损。
        """
        delta = {'木': 0.0, '火': 0.0, '土': 0.0, '金': 0.0, '水': 0.0}

        if dayun_stem and dayun_stem in STEM_ELEMENTS:
            delta[STEM_ELEMENTS[dayun_stem]] += cls.STEM_POWER
        if dayun_branch and dayun_branch in BRANCH_ELEMENTS:
            delta[BRANCH_ELEMENTS[dayun_branch]] += cls.BRANCH_MAIN_POWER
            for hidden in HIDDEN_STEMS.get(dayun_branch, []):
                elem_char = hidden[-1] if len(hidden) >= 2 else ''
                if elem_char in delta:
                    delta[elem_char] += cls.BRANCH_HIDDEN_POWER

        activated = []
        for nb in natal_branches:
            if dayun_branch and nb:
                if BRANCH_CHONG.get(dayun_branch) == nb:
                    activated.append({'type': '冲', 'branches': f'{dayun_branch}{nb}', 'severity': 'high'})
                    nb_elem = BRANCH_ELEMENTS.get(nb, '')
                    if nb_elem:
                        delta[nb_elem] -= 0.8
                if BRANCH_LIUHE.get(dayun_branch) == nb:
                    activated.append({'type': '合', 'branches': f'{dayun_branch}{nb}', 'severity': 'medium'})
                    transform_elem = BRANCH_LIUHE_TRANSFORM.get((dayun_branch, nb))
                    if transform_elem:
                        delta[transform_elem] += 0.6
                xing_targets = BRANCH_XING.get(dayun_branch, [])
                if nb in xing_targets:
                    activated.append({'type': '刑', 'branches': f'{dayun_branch}{nb}', 'severity': 'high'})
                    nb_elem = BRANCH_ELEMENTS.get(nb, '')
                    if nb_elem:
                        delta[nb_elem] -= 0.5
                hai_targets = BRANCH_HAI.get(dayun_branch, [])
                if nb in hai_targets:
                    activated.append({'type': '害', 'branches': f'{dayun_branch}{nb}', 'severity': 'medium'})

        if natal_stems and dayun_stem:
            for ns in natal_stems:
                transform_elem = STEM_HE_TRANSFORM.get((dayun_stem, ns))
                if transform_elem:
                    delta[transform_elem] += 0.5
                    activated.append({
                        'type': '天干合',
                        'branches': f'{dayun_stem}{ns}→{transform_elem}',
                        'severity': 'medium'
                    })

        new_power = {e: max(0, natal_power.get(e, 0) + delta.get(e, 0)) for e in delta}

        marriage_palace_activated = False
        if day_branch and dayun_branch:
            if BRANCH_CHONG.get(dayun_branch) == day_branch:
                marriage_palace_activated = True
            if BRANCH_LIUHE.get(dayun_branch) == day_branch:
                marriage_palace_activated = True

        spouse_power_change = 0.0
        if spouse_star_element and spouse_star_element in delta:
            spouse_power_change = delta[spouse_star_element]

        return PeriodBalance(
            wuxing_power=new_power,
            wuxing_delta=delta,
            activated_relations=activated,
            spouse_star_power_change=spouse_power_change,
            marriage_palace_activated=marriage_palace_activated,
        )

    @classmethod
    def calculate_all_dayun_balances(
        cls,
        natal_power: Dict[str, float],
        natal_branches: List[str],
        dayun_sequence: List[Dict[str, Any]],
        day_branch: str = '',
        spouse_star_element: str = '',
        age_range: tuple = (20, 45),
        natal_stems: Optional[List[str]] = None,
    ) -> List[PeriodBalance]:
        """为指定年龄范围内的所有大运计算力场快照"""
        results = []
        for dayun in dayun_sequence:
            ganzhi = dayun.get('ganzhi', '')
            if not ganzhi or len(ganzhi) < 2:
                stem_str = dayun.get('gan', dayun.get('stem', ''))
                branch_str = dayun.get('zhi', dayun.get('branch', ''))
            else:
                stem_str = ganzhi[0]
                branch_str = ganzhi[1]

            age_display = dayun.get('age_display', dayun.get('age_range', ''))
            start_age = cls._parse_start_age(age_display, dayun)
            if start_age is not None and age_range:
                end_age = start_age + 9
                if start_age > age_range[1] or end_age < age_range[0]:
                    continue

            balance = cls.calculate_period_balance(
                natal_power=natal_power,
                natal_branches=natal_branches,
                dayun_stem=stem_str,
                dayun_branch=branch_str,
                day_branch=day_branch,
                spouse_star_element=spouse_star_element,
                natal_stems=natal_stems,
            )
            balance.dayun_ganzhi = f"{stem_str}{branch_str}"
            balance.dayun_step = dayun.get('step', 0)
            balance.age_display = age_display
            results.append(balance)

        return results

    @staticmethod
    def _parse_start_age(age_display: str, dayun: Dict) -> Optional[int]:
        if not age_display:
            return dayun.get('start_age')
        try:
            parts = age_display.replace('岁', '').replace('(', '').replace(')', '')
            nums = parts.split('-')
            return int(nums[0])
        except (ValueError, IndexError):
            return None
