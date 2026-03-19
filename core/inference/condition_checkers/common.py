#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用条件检查函数（所有领域共享）

按 8 组分类，覆盖：基础、日支、十神、神煞、地支、天干、格局、日柱。
每个函数签名：(value, ctx: BaseMatchContext, conditions: Dict) -> bool
"""

from __future__ import annotations
from typing import Any, Dict, List

from core.inference.condition_matcher import (
    register, BaseMatchContext, BRANCH_TYPES, WUXING_SHENG, WUXING_KE,
)
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from core.data.relations import BRANCH_CHONG, BRANCH_LIUHE, BRANCH_XING, STEM_HE


# ═══ 第1组：基础条件 ═══════════════════════════════════

@register('gender')
def check_gender(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    return ctx.gender == value


@register('wangshuai')
def check_wangshuai(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    if isinstance(value, list):
        return ctx.wangshuai in value
    return ctx.wangshuai == value


# ═══ 第2组：日支条件 ═══════════════════════════════════

@register('day_branch_star')
def check_day_branch_star(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """日支主十神是否为指定值"""
    return ctx.day_branch_main_star == value


@register('day_branch_stars')
def check_day_branch_stars(value: list, ctx: BaseMatchContext, cond: Dict) -> bool:
    """日支主十神是否在指定列表中"""
    return ctx.day_branch_main_star in value


@register('day_branch_element')
def check_day_branch_element(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    return ctx.day_branch_element == value


@register('day_branch_type')
def check_day_branch_type(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """日支是否属于四正/四库/四生"""
    target_set = BRANCH_TYPES.get(value, set())
    return ctx.day_branch in target_set


# ═══ 第3组：十神条件 ═══════════════════════════════════

@register('has_shishen')
def check_has_shishen(value, ctx: BaseMatchContext, cond: Dict) -> bool:
    """八字中存在指定十神。value 可为 str 或 list（全部存在才通过）"""
    if isinstance(value, str):
        return value in ctx.all_shishen_set
    if isinstance(value, list):
        return all(v in ctx.all_shishen_set for v in value)
    return False


@register('no_shishen')
def check_no_shishen(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """八字中不存在指定十神"""
    return value not in ctx.all_shishen_set


@register('has_shishen_in_month')
def check_has_shishen_in_month(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """月柱存在指定十神（主星或藏干）"""
    return value in ctx.get_shishen_in_pillar('month')


@register('has_shishen_in_hour')
def check_has_shishen_in_hour(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """时柱存在指定十神"""
    return value in ctx.get_shishen_in_pillar('hour')


@register('has_shishen_year_hour')
def check_has_shishen_year_hour(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """年柱和时柱都存在指定十神"""
    return (value in ctx.get_shishen_in_pillar('year') and
            value in ctx.get_shishen_in_pillar('hour'))


@register('has_shishen_count_min')
def check_has_shishen_count_min(value: dict, ctx: BaseMatchContext, cond: Dict) -> bool:
    """指定十神数量 >= N。value: {"正印": 3}"""
    for name, min_count in value.items():
        actual = ctx.shishen_counts.get(name, 0)
        if actual < min_count:
            return False
    return True


@register('no_shishen_main')
def check_no_shishen_main(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """天干主星中不存在指定十神"""
    return value not in ctx.main_stars_set


@register('has_shishen_main')
def check_has_shishen_main(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """天干主星中存在指定十神"""
    return value in ctx.main_stars_set


# ═══ 第4组：神煞条件 ═══════════════════════════════════

@register('has_deity')
def check_has_deity(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """存在指定神煞。若 conditions 含 deity_pillar 则限定到该柱"""
    pillar = cond.get('deity_pillar')
    if pillar:
        return value in ctx.deities_by_pillar.get(pillar, [])
    return value in ctx.all_deities_set


@register('deity_pillar')
def check_deity_pillar(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """修饰键，由 has_deity 消费。单独出现时始终通过。"""
    return True


@register('has_deity_count')
def check_has_deity_count(value: dict, ctx: BaseMatchContext, cond: Dict) -> bool:
    """指定神煞数量 >= min。value: {"name": "羊刃", "min": 2}"""
    name = value.get('name', '')
    min_count = value.get('min', 1)
    count = sum(1 for dl in ctx.deities_by_pillar.values() if name in dl)
    return count >= min_count


@register('has_deity_combo')
def check_has_deity_combo(value: list, ctx: BaseMatchContext, cond: Dict) -> bool:
    """多个神煞全部存在于八字中"""
    return all(d in ctx.all_deities_set for d in value)


@register('has_deity_combo_pillar')
def check_has_deity_combo_pillar(value: list, ctx: BaseMatchContext, cond: Dict) -> bool:
    """多个神煞存在于同一柱"""
    for pillar, deities in ctx.deities_by_pillar.items():
        if all(d in deities for d in value):
            return True
    return False


@register('has_star_fortune')
def check_has_star_fortune(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """十二长生状态。配合 fortune_pillar 限定柱位"""
    pillar = cond.get('fortune_pillar', 'day')
    branch = ctx.branches.get(pillar, '')
    if not branch:
        return False
    actual_stage = ctx.twelve_stages.get(branch, '')
    return actual_stage == value


@register('fortune_pillar')
def check_fortune_pillar(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """修饰键，由 has_star_fortune 消费。"""
    return True


@register('liunian_deity')
def check_liunian_deity(value: list, ctx: BaseMatchContext, cond: Dict) -> bool:
    """流年神煞（数据有限时降级为 False）"""
    if not ctx._inp or not ctx._inp.special_liunians:
        return False
    for ly in ctx._inp.special_liunians:
        ly_deities = ly.get('deities', [])
        if all(d in ly_deities for d in value):
            return True
    return False


# ═══ 第5组：地支条件 ═══════════════════════════════════

@register('branch_pattern')
def check_branch_pattern(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """地支特殊格局"""
    bs = ctx.all_branches_set
    if value in ('si_ku_full', 'chen_xu_chou_wei_full'):
        return {'辰', '戌', '丑', '未'}.issubset(bs)
    return False


@register('branch_relation')
def check_branch_relation(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """柱间地支关系，如 day_hour_liuhe"""
    parts = value.split('_')
    if len(parts) < 3:
        return False
    pillar_a, pillar_b = parts[0], parts[1]
    relation = '_'.join(parts[2:])
    ba, bb = ctx.get_pillar_branches(pillar_a, pillar_b)
    if not ba or not bb:
        return False
    if relation == 'liuhe':
        return ctx.check_branch_liuhe(ba, bb)
    if relation == 'chong':
        return ctx.check_branch_chong(ba, bb)
    if relation == 'xing':
        return ctx.check_branch_xing(ba, bb)
    return False


@register('branch_pair')
def check_branch_pair(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """指定地支对是否存在于四柱中"""
    if len(value) >= 2:
        return value[0] in ctx.all_branches_set and value[1] in ctx.all_branches_set
    return False


@register('branch_unique_count')
def check_branch_unique_count(value: int, ctx: BaseMatchContext, cond: Dict) -> bool:
    return len(ctx.all_branches_set) == value


@register('stem_combo')
def check_stem_combo(value: list, ctx: BaseMatchContext, cond: Dict) -> bool:
    """天干组合是否存在于四柱天干中"""
    required = set(value) if isinstance(value, list) else {value}
    return required.issubset(ctx.all_stems_set)


@register('stem_unique_count')
def check_stem_unique_count(value: int, ctx: BaseMatchContext, cond: Dict) -> bool:
    return len(ctx.all_stems_set) == value


# ═══ 第6组：格局条件 ═══════════════════════════════════

@register('pillar_relation')
def check_pillar_relation(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """柱间复合关系：天合地合、天克地冲、地支同等"""
    mapping = _parse_pillar_relation(value)
    if not mapping:
        return False
    pillar_a = mapping['pillar_a']
    pillar_b = mapping['pillar_b']
    sa, sb = ctx.get_pillar_stems(pillar_a, pillar_b)
    ba, bb = ctx.get_pillar_branches(pillar_a, pillar_b)
    if not all((sa, sb, ba, bb)):
        return False

    rel_type = mapping['type']
    if rel_type == 'tianhe_dihe':
        return ctx.check_stem_he(sa, sb) and ctx.check_branch_liuhe(ba, bb)
    if rel_type == 'tianke_dichong':
        return ctx.check_stem_ke(sa, sb) and ctx.check_branch_chong(ba, bb)
    if rel_type == 'branch_equal':
        return ba == bb
    if rel_type == 'liuhe':
        return ctx.check_branch_liuhe(ba, bb)
    if rel_type == 'branch_chong':
        return ctx.check_branch_chong(ba, bb)
    if rel_type == 'branch_xing':
        return ctx.check_branch_xing(ba, bb)

    if rel_type == 'compound':
        return _check_compound_pillar_relation(value, ctx)

    return False


def _parse_pillar_relation(value: str) -> dict:
    """解析 pillar_relation 值为结构化数据"""
    parts = value.split('_')
    if len(parts) < 3:
        return {}
    pillar_a, pillar_b = parts[0], parts[1]
    rel = '_'.join(parts[2:])

    if rel in ('tianhe_dihe', 'tianke_dichong', 'liuhe', 'branch_chong', 'branch_xing'):
        return {'pillar_a': pillar_a, 'pillar_b': pillar_b, 'type': rel}
    if rel == 'branch_equal':
        return {'pillar_a': pillar_a, 'pillar_b': pillar_b, 'type': 'branch_equal'}

    if 'liuhe' in value and 'chong' in value:
        return {'pillar_a': pillar_a, 'pillar_b': pillar_b, 'type': 'compound'}

    return {}


def _check_compound_pillar_relation(value: str, ctx: BaseMatchContext) -> bool:
    """处理复合关系，如 day_hour_liuhe_day_month_chong"""
    segments = value.split('_')
    checks = []
    i = 0
    while i < len(segments) - 2:
        pa, pb = segments[i], segments[i + 1]
        if pa in ('year', 'month', 'day', 'hour') and pb in ('year', 'month', 'day', 'hour'):
            rel_parts = []
            j = i + 2
            while j < len(segments) and segments[j] not in ('year', 'month', 'day', 'hour'):
                rel_parts.append(segments[j])
                j += 1
            if rel_parts:
                rel = '_'.join(rel_parts)
                checks.append((pa, pb, rel))
            i = j
        else:
            i += 1

    for pa, pb, rel in checks:
        ba, bb = ctx.get_pillar_branches(pa, pb)
        if not ba or not bb:
            return False
        if rel == 'liuhe' and not ctx.check_branch_liuhe(ba, bb):
            return False
        if rel == 'chong' and not ctx.check_branch_chong(ba, bb):
            return False
    return bool(checks)


@register('day_pillar_type')
def check_day_pillar_type(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """日柱干支关系类型"""
    ds_elem = ctx.day_stem_element
    db_elem = ctx.day_branch_element
    if not ds_elem or not db_elem:
        return False
    if value == 'same_element':
        return ds_elem == db_elem
    if value == 'stem_ke_branch':
        return WUXING_KE.get(ds_elem) == db_elem
    if value == 'stem_sheng_branch':
        return WUXING_SHENG.get(ds_elem) == db_elem
    if value == 'branch_sheng_stem':
        return WUXING_SHENG.get(db_elem) == ds_elem
    return False


@register('day_has')
def check_day_has(value: list, ctx: BaseMatchContext, cond: Dict) -> bool:
    """日支同时包含指定十神和神煞"""
    day_stars = set(ctx.day_branch_all_stars)
    day_deities = set(ctx.deities_by_pillar.get('day', []))
    combined = day_stars | day_deities
    return all(v in combined for v in value)


@register('day_branch_hai')
def check_day_branch_hai(value: bool, ctx: BaseMatchContext, cond: Dict) -> bool:
    """日支是否被其他柱地支所害"""
    return ctx.day_branch_has_hai == value


@register('branch_hai')
def check_branch_hai(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """指定两柱之间是否存在害关系，如 month_day"""
    parts = value.split('_')
    if len(parts) < 2:
        return False
    ba = ctx.branches.get(parts[0], '')
    bb = ctx.branches.get(parts[1], '')
    if not ba or not bb:
        return False
    from core.data.relations import BRANCH_HAI
    return bb in BRANCH_HAI.get(ba, [])
