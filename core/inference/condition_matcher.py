#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理引擎条件匹配框架（通用，所有领域共享）

提供：
- BaseMatchContext: BaZi 预计算数据，领域子类继承扩展
- register(): 装饰器注册条件检查函数
- InferenceConditionMatcher: 严格匹配入口（未知条件 = 不匹配）

设计原则：
- 新增条件键只需一步：写函数 + @register('key')
- 未知条件键严格拒绝（宁可漏不可错）
- BaseMatchContext 一次预计算，所有规则共享
"""

from __future__ import annotations
import logging
from collections import Counter
from typing import Dict, List, Set, Any, Optional, Callable

from core.inference.models import InferenceInput
from core.data.constants import (
    STEM_ELEMENTS, BRANCH_ELEMENTS, EARTHLY_BRANCHES, HIDDEN_STEMS,
)
from core.data.relations import (
    BRANCH_CHONG, BRANCH_LIUHE, BRANCH_XING, BRANCH_HAI,
    STEM_HE, STEM_KE,
)

logger = logging.getLogger(__name__)

# ═══ 五行关系 ═══════════════════════════════════════════

WUXING_SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
WUXING_KE = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}

BRANCH_TYPES = {
    '四正': {'子', '午', '卯', '酉'},
    '四库': {'辰', '戌', '丑', '未'},
    '四生': {'寅', '申', '巳', '亥'},
}

# ═══ 十二长生 ═══════════════════════════════════════════

TWELVE_STAGES = ['长生', '沐浴', '冠带', '临官', '帝旺', '衰', '病', '死', '墓', '绝', '胎', '养']
TWELVE_STAGE_START = {
    '甲': '亥', '乙': '午', '丙': '寅', '丁': '酉',
    '戊': '寅', '己': '酉', '庚': '巳', '辛': '子',
    '壬': '申', '癸': '卯',
}
STEM_YIN_YANG = {
    '甲': '阳', '乙': '阴', '丙': '阳', '丁': '阴',
    '戊': '阳', '己': '阴', '庚': '阳', '辛': '阴',
    '壬': '阳', '癸': '阴',
}


# ═══ Checker 注册表 ═════════════════════════════════════

ConditionChecker = Callable[[Any, 'BaseMatchContext', Dict[str, Any]], bool]

_REGISTRY: Dict[str, ConditionChecker] = {}


def register(key: str):
    """装饰器：注册条件检查函数到全局注册表"""
    def decorator(fn: ConditionChecker) -> ConditionChecker:
        if key in _REGISTRY:
            logger.warning(f"条件检查器重复注册: {key}")
        _REGISTRY[key] = fn
        return fn
    return decorator


class InferenceConditionMatcher:
    """
    推理引擎条件匹配器。
    
    严格模式：conditions 中任何未注册的 key → 整条规则不匹配。
    """

    @staticmethod
    def match(conditions: Dict[str, Any], ctx: 'BaseMatchContext') -> bool:
        if not conditions:
            return True
        for key, value in conditions.items():
            checker = _REGISTRY.get(key)
            if checker is None:
                logger.debug(f"未注册的条件键 '{key}'，规则跳过")
                return False
            if not checker(value, ctx, conditions):
                return False
        return True

    @staticmethod
    def get_registered_keys() -> List[str]:
        return sorted(_REGISTRY.keys())

    @staticmethod
    def is_registered(key: str) -> bool:
        return key in _REGISTRY


# ═══ BaseMatchContext ═══════════════════════════════════

class BaseMatchContext:
    """
    BaZi 数据预计算上下文（通用，所有领域共享）。
    
    从 InferenceInput 一次性构建，领域特有数据通过子类 _populate() 扩展。
    """

    def __init__(self):
        self.gender: str = ''
        self.wangshuai: str = ''

        self.stems: Dict[str, str] = {}
        self.branches: Dict[str, str] = {}
        self.all_stems: List[str] = []
        self.all_branches: List[str] = []
        self.all_stems_set: Set[str] = set()
        self.all_branches_set: Set[str] = set()

        self.day_stem: str = ''
        self.day_branch: str = ''
        self.day_stem_element: str = ''
        self.day_branch_element: str = ''
        self.day_branch_main_star: str = ''
        self.day_branch_all_stars: List[str] = []

        self.ten_gods_by_pillar: Dict[str, Dict[str, Any]] = {}
        self.main_stars_by_pillar: Dict[str, str] = {}
        self.all_shishen: List[str] = []
        self.all_shishen_set: Set[str] = set()
        self.shishen_counts: Dict[str, int] = {}
        self.main_stars_set: Set[str] = set()

        self.day_branch_has_chong: bool = False
        self.day_branch_has_he: bool = False
        self.day_branch_has_xing: bool = False
        self.day_branch_has_hai: bool = False
        self.day_branch_clash_count: int = 0
        self.day_branch_xing_count: int = 0

        self.deities_by_pillar: Dict[str, List[str]] = {}
        self.all_deities_set: Set[str] = set()

        self.xi_elements: Set[str] = set()
        self.ji_elements: Set[str] = set()

        self.twelve_stages: Dict[str, str] = {}

        self._inp: Optional[InferenceInput] = None

    def _populate(self, inp: InferenceInput):
        """从 InferenceInput 填充通用字段（子类应先调 super()._populate()）"""
        self._inp = inp
        self.gender = inp.gender
        self.wangshuai = inp.wangshuai
        self.day_stem = inp.day_stem
        self.day_branch = inp.day_branch
        self.day_stem_element = STEM_ELEMENTS.get(inp.day_stem, '')
        self.day_branch_element = BRANCH_ELEMENTS.get(inp.day_branch, '')

        for pillar in ('year', 'month', 'day', 'hour'):
            p = inp.bazi_pillars.get(pillar, {})
            self.stems[pillar] = p.get('stem', '')
            self.branches[pillar] = p.get('branch', '')

        self.all_stems = [self.stems[p] for p in ('year', 'month', 'day', 'hour') if self.stems.get(p)]
        self.all_branches = [self.branches[p] for p in ('year', 'month', 'day', 'hour') if self.branches.get(p)]
        self.all_stems_set = set(self.all_stems)
        self.all_branches_set = set(self.all_branches)

        self._build_ten_gods(inp)
        self._compute_day_branch_relations()
        self._build_deities(inp)
        self._build_xi_ji(inp)
        self._compute_twelve_stages()

    def _build_ten_gods(self, inp: InferenceInput):
        self.ten_gods_by_pillar = dict(inp.ten_gods)
        all_sh: List[str] = []
        for pillar in ('year', 'month', 'day', 'hour'):
            tg = inp.ten_gods.get(pillar, {})
            main = tg.get('main_star', '')
            if main:
                self.main_stars_by_pillar[pillar] = main
                self.main_stars_set.add(main)
                all_sh.append(main)
            for hs in tg.get('hidden_stars', []):
                if isinstance(hs, str) and hs:
                    all_sh.append(hs)
        self.all_shishen = all_sh
        self.all_shishen_set = set(all_sh)
        self.shishen_counts = dict(Counter(all_sh))

        day_tg = inp.ten_gods.get('day', {})
        self.day_branch_main_star = day_tg.get('main_star', '')
        self.day_branch_all_stars = []
        if self.day_branch_main_star:
            self.day_branch_all_stars.append(self.day_branch_main_star)
        for hs in day_tg.get('hidden_stars', []):
            if isinstance(hs, str) and hs:
                self.day_branch_all_stars.append(hs)

    def _compute_day_branch_relations(self):
        """从实际四柱地支计算日支的冲/合/刑/害关系"""
        db = self.day_branch
        if not db:
            return
        chong_cnt = 0
        xing_cnt = 0
        for pillar in ('year', 'month', 'hour'):
            b = self.branches.get(pillar, '')
            if not b:
                continue
            if BRANCH_CHONG.get(db) == b:
                self.day_branch_has_chong = True
                chong_cnt += 1
            if BRANCH_LIUHE.get(db) == b:
                self.day_branch_has_he = True
            xing_targets = BRANCH_XING.get(db, [])
            if b in xing_targets:
                self.day_branch_has_xing = True
                xing_cnt += 1
            hai_targets = BRANCH_HAI.get(db, [])
            if b in hai_targets:
                self.day_branch_has_hai = True
        self.day_branch_clash_count = chong_cnt
        self.day_branch_xing_count = xing_cnt

    def _build_deities(self, inp: InferenceInput):
        for pillar in ('year', 'month', 'day', 'hour'):
            dl = inp.deities.get(pillar, [])
            self.deities_by_pillar[pillar] = list(dl) if isinstance(dl, list) else []
        self.all_deities_set = set()
        for dl in self.deities_by_pillar.values():
            self.all_deities_set.update(dl)

    def _build_xi_ji(self, inp: InferenceInput):
        self.xi_elements = set(inp.xi_ji_elements.get('xi_shen', []))
        self.ji_elements = set(inp.xi_ji_elements.get('ji_shen', []))

    def _compute_twelve_stages(self):
        ds = self.day_stem
        if not ds or ds not in TWELVE_STAGE_START:
            return
        start_branch = TWELVE_STAGE_START[ds]
        if start_branch not in EARTHLY_BRANCHES:
            return
        start_idx = EARTHLY_BRANCHES.index(start_branch)
        is_yang = STEM_YIN_YANG.get(ds) == '阳'
        for i, stage in enumerate(TWELVE_STAGES):
            idx = (start_idx + i) % 12 if is_yang else (start_idx - i) % 12
            self.twelve_stages[EARTHLY_BRANCHES[idx]] = stage

    @classmethod
    def from_input(cls, inp: InferenceInput) -> 'BaseMatchContext':
        ctx = cls()
        ctx._populate(inp)
        return ctx

    # ─── 工具方法（供 checker 使用）─────────────────────

    def get_pillar_stems(self, pillar_a: str, pillar_b: str):
        return self.stems.get(pillar_a, ''), self.stems.get(pillar_b, '')

    def get_pillar_branches(self, pillar_a: str, pillar_b: str):
        return self.branches.get(pillar_a, ''), self.branches.get(pillar_b, '')

    def check_stem_he(self, a: str, b: str) -> bool:
        return bool(a and b and STEM_HE.get(a) == b)

    def check_stem_ke(self, a: str, b: str) -> bool:
        return bool(a and b and b in STEM_KE.get(a, []))

    def check_branch_liuhe(self, a: str, b: str) -> bool:
        return bool(a and b and BRANCH_LIUHE.get(a) == b)

    def check_branch_chong(self, a: str, b: str) -> bool:
        return bool(a and b and BRANCH_CHONG.get(a) == b)

    def check_branch_xing(self, a: str, b: str) -> bool:
        return bool(a and b and b in BRANCH_XING.get(a, []))

    def get_shishen_in_pillar(self, pillar: str) -> List[str]:
        """获取某柱的所有十神（主星 + 藏干十神）"""
        tg = self.ten_gods_by_pillar.get(pillar, {})
        result = []
        main = tg.get('main_star', '')
        if main:
            result.append(main)
        for hs in tg.get('hidden_stars', []):
            if isinstance(hs, str) and hs:
                result.append(hs)
        return result
