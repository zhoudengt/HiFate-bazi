#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
婚姻领域条件检查函数

12 个婚姻特有条件键 + MarriageMatchContext。
其他领域（健康/事业/子女等）复制此文件并替换「领域特有数据」即可。
"""

from __future__ import annotations
from typing import Dict, List, Set, Any, Optional

from core.inference.condition_matcher import (
    register, BaseMatchContext,
)
from core.inference.models import InferenceInput
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from core.data.relations import BRANCH_CHONG, BRANCH_LIUHE, BRANCH_XING

SHISHEN_MAP_MALE_SPOUSE = {'正财', '偏财'}
SHISHEN_MAP_FEMALE_SPOUSE = {'正官', '七杀'}


# ═══ MarriageMatchContext ══════════════════════════════

class MarriageMatchContext(BaseMatchContext):
    """
    婚姻领域扩展上下文。

    在 BaseMatchContext 基础上增加：
    - 配偶星列表 / 类型集 / 数量 / 喜忌
    - 婚姻宫（日支）冲合刑状态
    """

    def __init__(self):
        super().__init__()
        self.spouse_stars: List[Dict[str, Any]] = []
        self.spouse_star_types: Set[str] = set()
        self.spouse_star_count: int = 0
        self.zhengcai_count: int = 0
        self.piancai_count: int = 0
        self.zhengguan_count: int = 0
        self.qisha_count: int = 0
        self.spouse_star_has_xi: bool = False
        self.spouse_star_has_ji: bool = False
        self.spouse_star_positions: List[str] = []

        self.marriage_palace_chong: bool = False
        self.marriage_palace_he: bool = False
        self.marriage_palace_xing: bool = False
        self.marriage_palace_hai: bool = False
        self.marriage_palace_clash_count: int = 0

    def _populate(self, inp: InferenceInput):
        super()._populate(inp)
        self._build_spouse_stars(inp)
        self._build_marriage_palace_relations()

    def _build_spouse_stars(self, inp: InferenceInput):
        target_set = SHISHEN_MAP_MALE_SPOUSE if inp.gender == 'male' else SHISHEN_MAP_FEMALE_SPOUSE
        stars = []
        for pillar_name in ('year', 'month', 'day', 'hour'):
            tg = inp.ten_gods.get(pillar_name, {})
            main_star = tg.get('main_star', '')
            if main_star in target_set:
                stem = inp.bazi_pillars.get(pillar_name, {}).get('stem', '')
                element = STEM_ELEMENTS.get(stem, '')
                stars.append({
                    'shishen': main_star, 'pillar': pillar_name,
                    'stem': stem, 'element': element, 'hidden': False,
                })
            hidden_stars = tg.get('hidden_stars', [])
            hidden_stems = tg.get('hidden_stems', [])
            for idx, hs in enumerate(hidden_stars):
                if isinstance(hs, str) and hs in target_set:
                    stem_info = hidden_stems[idx] if idx < len(hidden_stems) else ''
                    stem = stem_info[0] if stem_info else ''
                    element = STEM_ELEMENTS.get(stem, '')
                    stars.append({
                        'shishen': hs, 'pillar': pillar_name,
                        'stem': stem, 'element': element, 'hidden': True,
                    })

        self.spouse_stars = stars
        self.spouse_star_types = {s['shishen'] for s in stars}
        self.spouse_star_count = len(stars)
        self.zhengcai_count = sum(1 for s in stars if s['shishen'] == '正财')
        self.piancai_count = sum(1 for s in stars if s['shishen'] == '偏财')
        self.zhengguan_count = sum(1 for s in stars if s['shishen'] == '正官')
        self.qisha_count = sum(1 for s in stars if s['shishen'] == '七杀')
        self.spouse_star_positions = [s['pillar'] for s in stars if not s.get('hidden')]

        xi_elements = self.xi_elements
        self.spouse_star_has_xi = any(
            s.get('element') in xi_elements for s in stars if s.get('element')
        )
        ji_elements = self.ji_elements
        self.spouse_star_has_ji = any(
            s.get('element') in ji_elements for s in stars if s.get('element')
        )

    def _build_marriage_palace_relations(self):
        """预计算婚姻宫（日支）的冲/合/刑/害"""
        self.marriage_palace_chong = self.day_branch_has_chong
        self.marriage_palace_he = self.day_branch_has_he
        self.marriage_palace_xing = self.day_branch_has_xing
        self.marriage_palace_hai = self.day_branch_has_hai
        self.marriage_palace_clash_count = self.day_branch_clash_count + self.day_branch_xing_count


# ═══ 婚姻特有条件检查器 ═══════════════════════════════

@register('spouse_star_type')
def check_spouse_star_type(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    if not isinstance(ctx, MarriageMatchContext):
        return False
    return value in ctx.spouse_star_types


@register('spouse_star_is_xi')
def check_spouse_star_is_xi(value: bool, ctx: BaseMatchContext, cond: Dict) -> bool:
    if not isinstance(ctx, MarriageMatchContext):
        return False
    if value is True:
        return ctx.spouse_star_has_xi
    return not ctx.spouse_star_has_xi


@register('spouse_star_count')
def check_spouse_star_count(value: int, ctx: BaseMatchContext, cond: Dict) -> bool:
    if not isinstance(ctx, MarriageMatchContext):
        return False
    return ctx.spouse_star_count == value


@register('spouse_star_count_min')
def check_spouse_star_count_min(value: int, ctx: BaseMatchContext, cond: Dict) -> bool:
    if not isinstance(ctx, MarriageMatchContext):
        return False
    return ctx.spouse_star_count >= value


@register('piancai_count_min')
def check_piancai_count_min(value: int, ctx: BaseMatchContext, cond: Dict) -> bool:
    """偏财数量 >= N（男命用）"""
    if not isinstance(ctx, MarriageMatchContext):
        return False
    return ctx.piancai_count >= value


@register('zhengcai_count_min')
def check_zhengcai_count_min(value: int, ctx: BaseMatchContext, cond: Dict) -> bool:
    """正财数量 >= N（男命用）"""
    if not isinstance(ctx, MarriageMatchContext):
        return False
    return ctx.zhengcai_count >= value


@register('qisha_count_min')
def check_qisha_count_min(value: int, ctx: BaseMatchContext, cond: Dict) -> bool:
    """七杀数量 >= N（女命用）"""
    if not isinstance(ctx, MarriageMatchContext):
        return False
    return ctx.qisha_count >= value


@register('zhengguan_count_min')
def check_zhengguan_count_min(value: int, ctx: BaseMatchContext, cond: Dict) -> bool:
    """正官数量 >= N（女命用）"""
    if not isinstance(ctx, MarriageMatchContext):
        return False
    return ctx.zhengguan_count >= value


@register('spouse_star_early')
def check_spouse_star_early(value: bool, ctx: BaseMatchContext, cond: Dict) -> bool:
    """配偶星是否在早位（年柱或月柱透出）"""
    if not isinstance(ctx, MarriageMatchContext):
        return False
    has_early = any(p in ('year', 'month') for p in ctx.spouse_star_positions)
    return has_early == value


@register('spouse_star_pattern')
def check_spouse_star_pattern(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """配偶星特殊格局"""
    if not isinstance(ctx, MarriageMatchContext):
        return False

    if value == 'kill_early_official_late':
        early_has_kill = False
        late_has_official = False
        for s in ctx.spouse_stars:
            if s['shishen'] == '七杀' and s['pillar'] in ('year', 'month'):
                early_has_kill = True
            if s['shishen'] == '正官' and s['pillar'] in ('day', 'hour'):
                late_has_official = True
        return early_has_kill and late_has_official

    if value == 'casual_early_proper_late':
        early_has_casual = False
        late_has_proper = False
        for s in ctx.spouse_stars:
            if s['shishen'] == '偏财' and s['pillar'] in ('year', 'month'):
                early_has_casual = True
            if s['shishen'] == '正财' and s['pillar'] in ('day', 'hour'):
                late_has_proper = True
        return early_has_casual and late_has_proper

    return False


@register('spouse_star_strength')
def check_spouse_star_strength(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    if not isinstance(ctx, MarriageMatchContext):
        return False
    if value == 'absent':
        return ctx.spouse_star_count == 0
    if value == 'strong':
        return ctx.spouse_star_count >= 2
    if value == 'weak':
        return ctx.spouse_star_count == 1
    return False


@register('wangshuai_vs_spouse')
def check_wangshuai_vs_spouse(value: str, ctx: BaseMatchContext, cond: Dict) -> bool:
    """身旺/身弱与配偶星的力量对比"""
    if not isinstance(ctx, MarriageMatchContext):
        return False
    if value == 'strong_vs_weak':
        return ctx.wangshuai in ('偏旺', '从旺') and ctx.spouse_star_count <= 1
    if value == 'weak_vs_strong':
        return ctx.wangshuai in ('偏弱', '从弱') and ctx.spouse_star_count >= 2
    if value == 'balanced':
        return ctx.wangshuai in ('中和', '偏旺', '偏弱') and ctx.spouse_star_count >= 1
    return False


@register('marriage_palace_chong')
def check_marriage_palace_chong(value: bool, ctx: BaseMatchContext, cond: Dict) -> bool:
    if not isinstance(ctx, MarriageMatchContext):
        return ctx.day_branch_has_chong == value
    return ctx.marriage_palace_chong == value


@register('marriage_palace_he')
def check_marriage_palace_he(value: bool, ctx: BaseMatchContext, cond: Dict) -> bool:
    if not isinstance(ctx, MarriageMatchContext):
        return ctx.day_branch_has_he == value
    return ctx.marriage_palace_he == value


@register('marriage_palace_xing')
def check_marriage_palace_xing(value: bool, ctx: BaseMatchContext, cond: Dict) -> bool:
    if not isinstance(ctx, MarriageMatchContext):
        return ctx.day_branch_has_xing == value
    return ctx.marriage_palace_xing == value


@register('marriage_palace_multi_clash')
def check_marriage_palace_multi_clash(value: bool, ctx: BaseMatchContext, cond: Dict) -> bool:
    """婚姻宫被多方冲刑（冲+刑总数 >= 2）"""
    if not isinstance(ctx, MarriageMatchContext):
        total = ctx.day_branch_clash_count + ctx.day_branch_xing_count
        return (total >= 2) == value
    return (ctx.marriage_palace_clash_count >= 2) == value


@register('marriage_palace_hai')
def check_marriage_palace_hai(value: bool, ctx: BaseMatchContext, cond: Dict) -> bool:
    """婚姻宫（日支）是否被其他柱地支所害"""
    return ctx.day_branch_has_hai == value
