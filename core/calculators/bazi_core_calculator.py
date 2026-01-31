#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心八字排盘计算逻辑，供微服务与本地调用共享使用。

该模块仅负责基础排盘（四柱、十神、藏干、星运/自坐、空亡、纳音、神煞、五行统计等），
不包含任何规则匹配、接口聚合等扩展逻辑。

注意：所有计算公式与历史实现保持一致，严禁在此模块内调整算法或输出结构。
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

import os
import sys
from typing import Any, Dict

# 添加模块路径，保持与旧实现兼容
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data.constants import NAYIN_MAP, STEM_ELEMENTS, BRANCH_ELEMENTS, HIDDEN_STEMS  # noqa: E402
from core.data.relations import (  # noqa: E402
    STEM_HE,
    BRANCH_LIUHE,
    BRANCH_CHONG,
    BRANCH_XING,
    BRANCH_HAI,
    BRANCH_PO,
    BRANCH_SANHE_GROUPS,
    BRANCH_SANHUI_GROUPS,
)
from core.data.stems_branches import STEM_YINYANG  # noqa: E402
from core.config.deities_config import DeitiesCalculator  # noqa: E402
from core.config.star_fortune_config import StarFortuneCalculator  # noqa: E402
from core.calculators.LunarConverter import LunarConverter  # noqa: E402


class BaziCoreCalculator:
    """核心八字排盘计算器 - 仅包含纯计算逻辑"""

    def __init__(self, solar_date: str, solar_time: str, gender: str = 'male') -> None:
        self.solar_date = solar_date
        self.solar_time = solar_time
        self.gender = gender
        self.lunar_date: Dict[str, Any] | None = None
        self.bazi_pillars: Dict[str, Dict[str, str]] = {}
        self.details: Dict[str, Dict[str, Any]] = {}
        self.adjusted_solar_date = solar_date
        self.adjusted_solar_time = solar_time
        self.is_zi_shi_adjusted = False
        self.last_result: Dict[str, Any] | None = None

        # 五行生克关系
        self.element_relations = {
            '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
            '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
            '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
            '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
            '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
        }

    # === 公开方法 ==================================================================================

    def calculate(self) -> Dict[str, Any] | None:
        """执行八字排盘计算"""
        try:
            self._calculate_with_lunar_converter()
            self._calculate_ten_gods()
            self._calculate_hidden_stems()
            self._calculate_star_fortune()
            self._calculate_kongwang()
            self._calculate_nayin()
            self._calculate_deities()

            result = self._format_result()
            self.last_result = result
            return result
        except Exception as exc:  # pragma: no cover - 调试输出
            logger.info(f"计算错误: {exc}")
            import traceback
            traceback.print_exc()
            return None

    # === 内部计算步骤 ===============================================================================

    def _calculate_with_lunar_converter(self) -> None:
        lunar_result = LunarConverter.solar_to_lunar(self.solar_date, self.solar_time)
        self.lunar_date = lunar_result['lunar_date']
        self.bazi_pillars = lunar_result['bazi_pillars']
        self.adjusted_solar_date = lunar_result['adjusted_solar_date']
        self.adjusted_solar_time = lunar_result['adjusted_solar_time']
        self.is_zi_shi_adjusted = lunar_result['is_zi_shi_adjusted']

        if self.is_zi_shi_adjusted:
            logger.debug(  # pragma: no cover - 调试输出
                f"注意：23点以后，日期调整为: {self.adjusted_solar_date} {self.adjusted_solar_time}"
            )
            logger.debug(  # pragma: no cover
                f"年柱保持为: {self.bazi_pillars['year']['stem']}{self.bazi_pillars['year']['branch']}"
            )

    def _calculate_ten_gods(self) -> None:
        day_stem = self.bazi_pillars['day']['stem']
        for pillar_type, pillar in self.bazi_pillars.items():
            main_star = self.get_main_star(day_stem, pillar['stem'], pillar_type)
            branch_gods = self.get_branch_ten_gods(day_stem, pillar['branch'])

            if pillar_type == 'hour' and pillar['branch'] == '亥':
                if branch_gods == ['正印', '劫财']:
                    branch_gods = ['劫财', '正印']

            if pillar_type not in self.details:
                self.details[pillar_type] = {}

            self.details[pillar_type].update({
                'main_star': main_star,
                'hidden_stars': list(branch_gods),
                'sub_stars': list(branch_gods),
            })

    def _calculate_hidden_stems(self) -> None:
        for pillar_type, pillar in self.bazi_pillars.items():
            branch = pillar['branch']
            hidden_stems = HIDDEN_STEMS.get(branch, [])
            self.details[pillar_type]['hidden_stems'] = hidden_stems

    def _calculate_star_fortune(self) -> None:
        calculator = StarFortuneCalculator()
        day_stem = self.bazi_pillars['day']['stem']

        for pillar_type, pillar in self.bazi_pillars.items():
            star_fortune = calculator.get_stem_fortune(day_stem, pillar['branch'])
            self_sitting = calculator.get_stem_fortune(pillar['stem'], pillar['branch'])

            self.details[pillar_type].update({
                'star_fortune': star_fortune,
                'self_sitting': self_sitting,
            })

    def _calculate_kongwang(self) -> None:
        calculator = StarFortuneCalculator()
        for pillar_type, pillar in self.bazi_pillars.items():
            pillar_ganzhi = f"{pillar['stem']}{pillar['branch']}"
            kongwang = calculator.get_kongwang(pillar_ganzhi)

            if pillar_type not in self.details:
                self.details[pillar_type] = {}

            self.details[pillar_type]['kongwang'] = kongwang

    def _calculate_nayin(self) -> None:
        for pillar_type, pillar in self.bazi_pillars.items():
            nayin = NAYIN_MAP.get((pillar['stem'], pillar['branch']), '')
            self.details[pillar_type]['nayin'] = nayin

    def _calculate_deities(self) -> None:
        calculator = DeitiesCalculator()

        year_stem = self.bazi_pillars['year']['stem']
        year_branch = self.bazi_pillars['year']['branch']
        month_stem = self.bazi_pillars['month']['stem']
        month_branch = self.bazi_pillars['month']['branch']
        day_stem = self.bazi_pillars['day']['stem']
        day_branch = self.bazi_pillars['day']['branch']
        hour_stem = self.bazi_pillars['hour']['stem']
        hour_branch = self.bazi_pillars['hour']['branch']

        self.details['year']['deities'] = calculator.calculate_year_deities(year_stem, year_branch, self.bazi_pillars)
        self.details['month']['deities'] = calculator.calculate_month_deities(month_stem, month_branch, self.bazi_pillars)
        self.details['day']['deities'] = calculator.calculate_day_deities(day_stem, day_branch, self.bazi_pillars)
        self.details['hour']['deities'] = calculator.calculate_hour_deities(hour_stem, hour_branch, self.bazi_pillars)

    # === 基础工具方法 ================================================================================

    def get_main_star(self, day_stem: str, target_stem: str, pillar_type: str) -> str:
        if pillar_type == 'day':
            return '元男' if self.gender == 'male' else '元女'

        day_element = STEM_ELEMENTS[day_stem]
        target_element = STEM_ELEMENTS[target_stem]
        day_yinyang = STEM_YINYANG[day_stem]
        target_yinyang = STEM_YINYANG[target_stem]

        relation_type = self._get_element_relation(day_element, target_element)
        is_same_yinyang = (day_yinyang == target_yinyang)

        if relation_type == 'same':
            return '比肩' if is_same_yinyang else '劫财'
        elif relation_type == 'me_producing':
            return '食神' if is_same_yinyang else '伤官'
        elif relation_type == 'me_controlling':
            return '偏财' if is_same_yinyang else '正财'
        elif relation_type == 'controlling_me':
            return '七杀' if is_same_yinyang else '正官'
        elif relation_type == 'producing_me':
            return '偏印' if is_same_yinyang else '正印'
        return '未知'

    def _get_element_relation(self, day_element: str, target_element: str) -> str:
        if day_element == target_element:
            return 'same'

        relations = self.element_relations[day_element]
        if target_element == relations['produces']:
            return 'me_producing'
        if target_element == relations['controls']:
            return 'me_controlling'
        if target_element == relations['produced_by']:
            return 'producing_me'
        if target_element == relations['controlled_by']:
            return 'controlling_me'
        return 'unknown'

    def get_branch_ten_gods(self, day_stem: str, branch: str) -> list[str]:
        hidden_stems = HIDDEN_STEMS.get(branch, [])
        branch_gods: list[str] = []

        for hidden_stem in hidden_stems:
            stem_char = hidden_stem[0] if len(hidden_stem) > 0 else hidden_stem
            ten_god = self.get_main_star(day_stem, stem_char, 'hidden')
            branch_gods.append(ten_god)

        return branch_gods

    # === 结果格式化 ==================================================================================

    def _build_ten_gods_stats(self) -> Dict[str, Any]:
        stats = {'main': {}, 'sub': {}, 'totals': {}}

        def record(group: str, star_name: str, pillar: str) -> None:
            if not star_name:
                return

            group_map = stats[group]
            entry = group_map.setdefault(star_name, {'count': 0, 'pillars': {}})
            entry['count'] += 1
            entry['pillars'][pillar] = entry['pillars'].get(pillar, 0) + 1

            total_entry = stats['totals'].setdefault(star_name, {'count': 0, 'pillars': {}})
            total_entry['count'] += 1
            total_entry['pillars'][pillar] = total_entry['pillars'].get(pillar, 0) + 1

        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_detail = self.details.get(pillar_type, {})
            record('main', pillar_detail.get('main_star'), pillar_type)

            sub_stars = pillar_detail.get('sub_stars') or pillar_detail.get('hidden_stars', [])
            for star in sub_stars:
                record('sub', star, pillar_type)

        stats['ten_gods_main'] = stats['main']
        stats['ten_gods_sub'] = stats['sub']
        stats['ten_gods_total'] = stats['totals']
        return stats

    def _build_elements_info(self) -> Dict[str, Any]:
        elements = {}
        for pillar in ['year', 'month', 'day', 'hour']:
            pillar_data = self.bazi_pillars.get(pillar, {})
            stem = pillar_data.get('stem')
            branch = pillar_data.get('branch')
            elements[pillar] = {
                'stem': stem,
                'stem_element': STEM_ELEMENTS.get(stem),
                'branch': branch,
                'branch_element': BRANCH_ELEMENTS.get(branch),
            }
        return elements

    def _build_element_counts(self, elements: Dict[str, Any]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for info in elements.values():
            stem_element = info.get('stem_element')
            branch_element = info.get('branch_element')
            if stem_element:
                counts[stem_element] = counts.get(stem_element, 0) + 1
            if branch_element:
                counts[branch_element] = counts.get(branch_element, 0) + 1
        return counts

    def _describe_element_relation(self, source_element: str | None, target_element: str | None) -> str:
        if not source_element or not target_element:
            return 'unknown'
        if source_element == target_element:
            return 'same'
        relations = self.element_relations.get(source_element, {})
        if target_element == relations.get('produces'):
            return 'generate'
        if target_element == relations.get('controls'):
            return 'control'
        if target_element == relations.get('produced_by'):
            return 'generated_by'
        if target_element == relations.get('controlled_by'):
            return 'controlled_by'
        return 'unknown'

    def _build_element_relationships(self, elements: Dict[str, Any]) -> Dict[str, Any]:
        relationships = {'element_relations': {}}
        day_stem_element = elements.get('day', {}).get('stem_element')
        day_branch_element = elements.get('day', {}).get('branch_element')
        relationships['element_relations']['day_stem->day_branch'] = self._describe_element_relation(
            day_stem_element, day_branch_element
        )
        relationships['element_relations']['day_branch->day_stem'] = self._describe_element_relation(
            day_branch_element, day_stem_element
        )
        return relationships

    def _build_ganzhi_relationships(self) -> Dict[str, Any]:
        pillars = ['year', 'month', 'day', 'hour']
        stem_map = {pillar: self.bazi_pillars.get(pillar, {}).get('stem') for pillar in pillars}
        branch_map = {pillar: self.bazi_pillars.get(pillar, {}).get('branch') for pillar in pillars}

        stem_relations = {
            'he': [],
            'map': {pillar: [] for pillar in pillars},
        }

        branch_relations = {
            'liuhe': [],
            'chong': [],
            'xing': [],
            'hai': [],
            'po': [],
            'map': {
                'liuhe': {pillar: [] for pillar in pillars},
                'chong': {pillar: [] for pillar in pillars},
                'xing': {pillar: [] for pillar in pillars},
                'hai': {pillar: [] for pillar in pillars},
                'po': {pillar: [] for pillar in pillars},
            },
            'sanhe': [],
            'sanhui': [],
        }

        for i in range(len(pillars)):
            for j in range(i + 1, len(pillars)):
                pillar_a = pillars[i]
                pillar_b = pillars[j]
                stem_a = stem_map.get(pillar_a)
                stem_b = stem_map.get(pillar_b)
                branch_a = branch_map.get(pillar_a)
                branch_b = branch_map.get(pillar_b)

                if stem_a and stem_b and STEM_HE.get(stem_a) == stem_b:
                    entry = {'pillars': [pillar_a, pillar_b], 'stems': [stem_a, stem_b]}
                    stem_relations['he'].append(entry)
                    stem_relations['map'][pillar_a].append(pillar_b)
                    stem_relations['map'][pillar_b].append(pillar_a)

                if branch_a and branch_b:
                    if BRANCH_LIUHE.get(branch_a) == branch_b:
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['liuhe'].append(entry)
                        branch_relations['map']['liuhe'][pillar_a].append(pillar_b)
                        branch_relations['map']['liuhe'][pillar_b].append(pillar_a)
                    if BRANCH_CHONG.get(branch_a) == branch_b:
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['chong'].append(entry)
                        branch_relations['map']['chong'][pillar_a].append(pillar_b)
                        branch_relations['map']['chong'][pillar_b].append(pillar_a)
                    if branch_b in BRANCH_XING.get(branch_a, []):
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['xing'].append(entry)
                        branch_relations['map']['xing'][pillar_a].append(pillar_b)
                    if branch_a in BRANCH_XING.get(branch_b, []):
                        branch_relations['map']['xing'][pillar_b].append(pillar_a)
                    if branch_b in BRANCH_HAI.get(branch_a, []):
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['hai'].append(entry)
                        branch_relations['map']['hai'][pillar_a].append(pillar_b)
                    if branch_a in BRANCH_HAI.get(branch_b, []):
                        branch_relations['map']['hai'][pillar_b].append(pillar_a)
                    if BRANCH_PO.get(branch_a) == branch_b:
                        entry = {'pillars': [pillar_a, pillar_b], 'branches': [branch_a, branch_b]}
                        branch_relations['po'].append(entry)
                        branch_relations['map']['po'][pillar_a].append(pillar_b)
                        branch_relations['map']['po'][pillar_b].append(pillar_a)

        # 三合局
        branch_values = {pillar: branch for pillar, branch in branch_map.items() if branch}
        for group in BRANCH_SANHE_GROUPS:
            group_set = set(group)
            matched_pillars = [pillar for pillar, branch in branch_values.items() if branch in group_set]
            matched_branches = {branch_values[p] for p in matched_pillars}
            if len(matched_branches) == len(group_set):
                branch_relations['sanhe'].append({
                    'group': list(group),
                    'pillars': matched_pillars,
                })

        for group in BRANCH_SANHUI_GROUPS:
            group_set = set(group)
            matched_pillars = [pillar for pillar, branch in branch_values.items() if branch in group_set]
            matched_branches = {branch_values[p] for p in matched_pillars}
            if len(matched_branches) == len(group_set):
                branch_relations['sanhui'].append({
                    'group': list(group),
                    'pillars': matched_pillars,
                })

        return {
            'stem_relations': stem_relations,
            'branch_relations': branch_relations,
        }

    def _format_result(self) -> Dict[str, Any]:
        elements = self._build_elements_info()
        element_counts = self._build_element_counts(elements)
        element_relationships = self._build_element_relationships(elements)
        ganzhi_relationships = self._build_ganzhi_relationships()

        relationships = element_relationships
        relationships.update(ganzhi_relationships)

        return {
            'basic_info': {
                'solar_date': self.solar_date,
                'solar_time': self.solar_time,
                'adjusted_solar_date': self.adjusted_solar_date,
                'adjusted_solar_time': self.adjusted_solar_time,
                'lunar_date': self.lunar_date,
                'gender': self.gender,
                'is_zi_shi_adjusted': self.is_zi_shi_adjusted,
            },
            'bazi_pillars': self.bazi_pillars,
            'details': self.details,
            'ten_gods_stats': self._build_ten_gods_stats(),
            'elements': elements,
            'element_counts': element_counts,
            'relationships': relationships,
        }


__all__ = ["BaziCoreCalculator"]

