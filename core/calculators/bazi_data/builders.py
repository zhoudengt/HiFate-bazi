#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据构建与显示 Mixin

从 bazi_calculator.py 提取的数据构建、格式化和打印方法。
包含十神统计、五行信息、干支关系、排盘结果打印等。
"""

import logging

from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from core.data.relations import (
    STEM_HE,
    BRANCH_LIUHE,
    BRANCH_CHONG,
    BRANCH_XING,
    BRANCH_HAI,
    BRANCH_PO,
    BRANCH_SANHE_GROUPS,
    BRANCH_SANHUI_GROUPS,
)

logger = logging.getLogger("core.calculators.bazi_calculator")


class BaziDataBuilderMixin:
    """数据构建与显示方法，以 Mixin 方式注入 WenZhenBazi"""

    def _format_result(self):
        """格式化输出结果"""
        ten_gods_stats = self._build_ten_gods_stats()
        elements = self._build_elements_info()
        element_counts = self._build_element_counts(elements)
        relationships = self._build_element_relationships(elements)
        relationships.update(self._build_ganzhi_relationships())

        result = {
            'basic_info': {
                'solar_date': self.solar_date,
                'solar_time': self.solar_time,
                'adjusted_solar_date': self.adjusted_solar_date,
                'adjusted_solar_time': self.adjusted_solar_time,
                'lunar_date': self.lunar_date,
                'gender': self.gender,
                'is_zi_shi_adjusted': self.is_zi_shi_adjusted
            },
            'bazi_pillars': self.bazi_pillars,
            'details': self.details,
            'ten_gods_stats': ten_gods_stats,
            'elements': elements,
            'element_counts': element_counts,
            'relationships': relationships
        }
        return result

    def _build_ten_gods_stats(self):
        """构建十神统计信息，仅统计主星与副星"""
        stats = {'main': {}, 'sub': {}, 'totals': {}}

        def record(group, star, pillar):
            if not star:
                return
            entry = stats[group].setdefault(star, {'count': 0, 'pillars': {}})
            entry['count'] += 1
            entry['pillars'][pillar] = entry['pillars'].get(pillar, 0) + 1

            total_entry = stats['totals'].setdefault(star, {'count': 0, 'pillars': {}})
            total_entry['count'] += 1
            total_entry['pillars'][pillar] = total_entry['pillars'].get(pillar, 0) + 1

        for pillar in ['year', 'month', 'day', 'hour']:
            detail = self.details.get(pillar, {})
            record('main', detail.get('main_star'), pillar)
            for star in detail.get('hidden_stars', []):
                record('sub', star, pillar)

        stats['ten_gods_main'] = stats['main']
        stats['ten_gods_sub'] = stats['sub']
        stats['ten_gods_total'] = stats['totals']
        return stats

    def _build_elements_info(self):
        """构建四柱五行信息"""
        elements = {}
        for pillar in ['year', 'month', 'day', 'hour']:
            pillar_data = self.bazi_pillars.get(pillar, {})
            stem = pillar_data.get('stem')
            branch = pillar_data.get('branch')
            elements[pillar] = {
                'stem': stem,
                'branch': branch,
                'stem_element': STEM_ELEMENTS.get(stem, ''),
                'branch_element': BRANCH_ELEMENTS.get(branch, '')
            }
        return elements

    def _build_element_counts(self, elements):
        """统计五行数量"""
        counts = {}
        for info in elements.values():
            stem_element = info.get('stem_element')
            branch_element = info.get('branch_element')
            if stem_element:
                counts[stem_element] = counts.get(stem_element, 0) + 1
            if branch_element:
                counts[branch_element] = counts.get(branch_element, 0) + 1
        return counts

    def _build_element_relationships(self, elements):
        """构建常用五行关系"""
        relationships = {'element_relations': {}}

        def describe(src, dst):
            if not src or not dst:
                return 'unknown'
            if src == dst:
                return 'same'
            rel = self.element_relations.get(src, {})
            if dst == rel.get('produces'):
                return 'generate'
            if dst == rel.get('controls'):
                return 'control'
            if dst == rel.get('produced_by'):
                return 'generated_by'
            if dst == rel.get('controlled_by'):
                return 'controlled_by'
            return 'unknown'

        day_stem_el = elements.get('day', {}).get('stem_element')
        day_branch_el = elements.get('day', {}).get('branch_element')
        relationships['element_relations']['day_stem->day_branch'] = describe(day_stem_el, day_branch_el)
        relationships['element_relations']['day_branch->day_stem'] = describe(day_branch_el, day_stem_el)
        return relationships

    def _build_ganzhi_relationships(self):
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

    def print_result(self):
        """打印排盘结果"""
        result = self.calculate()
        if not result:
            logger.info("排盘失败，请检查输入参数")
            return

        logger.info("=" * 60)
        logger.info("HiFate排盘 - 最完整版本")
        logger.info("=" * 60)

        basic = result['basic_info']
        logger.info(f"阳历: {basic['solar_date']} {basic['solar_time']}")

        if basic['is_zi_shi_adjusted']:
            logger.info(f"调整后: {basic['adjusted_solar_date']} {basic['adjusted_solar_time']} (子时调整)")

        lunar = basic['lunar_date']
        lunar_year = lunar['year']
        lunar_month_name = lunar.get('month_name', '')
        lunar_day_name = lunar.get('day_name', '')

        if not lunar_month_name:
            lunar_month_name = f"{lunar['month']}月"
        if not lunar_day_name:
            lunar_day_name = f"{lunar['day']}日"

        logger.info(f"农历: {lunar_year}年{lunar_month_name}{lunar_day_name}")
        logger.info(f"性别: {'男' if basic['gender'] == 'male' else '女'}")
        logger.info("")

        pillars = result['bazi_pillars']
        details = result['details']

        self._print_detailed_table(pillars, details)

    def _print_detailed_table(self, pillars, details):
        """打印详细排盘表格"""
        headers = ["日期", "年柱", "月柱", "日柱", "时柱"]

        rows = [
            ["主星"] + [details.get(p, {}).get('main_star', '') for p in ['year', 'month', 'day', 'hour']],
            ["天干"] + [pillars[p]['stem'] for p in ['year', 'month', 'day', 'hour']],
            ["地支"] + [pillars[p]['branch'] for p in ['year', 'month', 'day', 'hour']],
        ]

        hidden_stems_data = [details.get(p, {}).get('hidden_stems', []) for p in ['year', 'month', 'day', 'hour']]
        hidden_stars_data = [details.get(p, {}).get('hidden_stars', []) for p in ['year', 'month', 'day', 'hour']]

        max_hidden_rows = max(len(stems) for stems in hidden_stems_data) if any(hidden_stems_data) else 0
        max_stars_rows = max(len(stars) for stars in hidden_stars_data) if any(hidden_stars_data) else 0

        if max_hidden_rows > 0:
            rows.append(["藏干"] + ["" for _ in range(4)])
            for i in range(max_hidden_rows):
                row_data = []
                for j in range(4):
                    if i < len(hidden_stems_data[j]):
                        row_data.append(hidden_stems_data[j][i])
                    else:
                        row_data.append("")
                rows.append([""] + row_data)

        if max_stars_rows > 0:
            rows.append(["副星"] + ["" for _ in range(4)])
            for i in range(max_stars_rows):
                row_data = []
                for j in range(4):
                    if i < len(hidden_stars_data[j]):
                        row_data.append(hidden_stars_data[j][i])
                    else:
                        row_data.append("")
                rows.append([""] + row_data)

        other_rows = [
            ["星运"] + [details.get(p, {}).get('star_fortune', '') for p in ['year', 'month', 'day', 'hour']],
            ["自坐"] + [details.get(p, {}).get('self_sitting', '') for p in ['year', 'month', 'day', 'hour']],
            ["空亡"] + [details.get(p, {}).get('kongwang', '') for p in ['year', 'month', 'day', 'hour']],
            ["纳音"] + [details.get(p, {}).get('nayin', '') for p in ['year', 'month', 'day', 'hour']]
        ]
        rows.extend(other_rows)

        deities_data = [details.get(p, {}).get('deities', []) for p in ['year', 'month', 'day', 'hour']]
        max_deities_rows = max(len(deities) for deities in deities_data) if any(deities_data) else 0

        if max_deities_rows > 0:
            rows.append(["神煞"] + ["" for _ in range(4)])
            for i in range(max_deities_rows):
                row_data = []
                for j in range(4):
                    if i < len(deities_data[j]):
                        row_data.append(deities_data[j][i])
                    else:
                        row_data.append("")
                rows.append([""] + row_data)

        col_widths = [8, 20, 20, 20, 20]

        header_line = "".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers)))
        logger.info(header_line)
        logger.info("-" * len(header_line))

        for row in rows:
            row_line = "".join(f"{row[i]:<{col_widths[i]}}" for i in range(len(row)))
            logger.info(row_line)

    def print_rizhu_gender_analysis(self):
        """打印日柱性别查询分析结果"""
        logger.info("\n" + "=" * 80)

        if not self.bazi_pillars or not self.details:
            self.calculate()

        from core.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
        analyzer = RizhuGenderAnalyzer(self.bazi_pillars, self.gender)

        analysis_output = analyzer.get_formatted_output()
        logger.info(analysis_output)
