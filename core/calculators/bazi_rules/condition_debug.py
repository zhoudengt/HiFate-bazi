#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则条件调试 Mixin

从 bazi_calculator.py 提取的条件调试相关方法。
用于规则匹配时输出详细的条件判定信息，辅助排查规则命中/未命中原因。
"""

import json


class BaziConditionDebugMixin:
    """条件调试辅助方法，以 Mixin 方式注入 WenZhenBazi"""

    def _collect_condition_values(self, condition, data, acc=None):
        if acc is None:
            acc = []
        if not condition or not isinstance(condition, dict):
            return acc

        for key, value in condition.items():
            if key == "all":
                for sub in value or []:
                    self._collect_condition_values(sub, data, acc)
            elif key == "any":
                for sub in value or []:
                    self._collect_condition_values(sub, data, acc)
            elif key == "not":
                if isinstance(value, dict):
                    self._collect_condition_values(value, data, acc)
            elif key == "gender":
                basic_info = data.get('basic_info', {})
                if not isinstance(basic_info, dict):
                    basic_info = {}
                gender = basic_info.get('gender', '')
                acc.append(f"gender={gender}")
            elif key == "liunian_relation":
                fortune = data.get('fortune', {}) or {}
                if not isinstance(fortune, dict):
                    fortune = {}
                liunian = fortune.get('current_liunian', {}) or {}
                if not isinstance(liunian, dict):
                    liunian = {}
                part = value.get('part', 'stem') if isinstance(value, dict) else 'stem'
                acc.append(f"liunian.{part}={liunian.get(part, '') if isinstance(liunian, dict) else ''}")
                target = value.get('target') if isinstance(value, dict) else None
                if target:
                    bazi_pillars = data.get('bazi_pillars', {})
                    if not isinstance(bazi_pillars, dict):
                        bazi_pillars = {}
                    pillar = bazi_pillars.get(target, {})
                    if not isinstance(pillar, dict):
                        pillar = {}
                    part_key = 'stem' if part == 'stem' else 'branch'
                    acc.append(f"{target}.{part_key}={pillar.get(part_key, '') if isinstance(pillar, dict) else ''}")
            elif key == "liunian_deities":
                fortune = data.get('fortune', {}) or {}
                if not isinstance(fortune, dict):
                    fortune = {}
                liunian = fortune.get('current_liunian', {}) or {}
                if not isinstance(liunian, dict):
                    liunian = {}
                deities = liunian.get('deities', []) if isinstance(liunian, dict) else []
                if not isinstance(deities, list):
                    deities = []
                acc.append(f"liunian.deities={','.join(deities)}")
            elif key == "main_star_in_day":
                details = data.get('details', {})
                if not isinstance(details, dict):
                    details = {}
                day_detail = details.get('day', {})
                if not isinstance(day_detail, dict):
                    day_detail = {}
                star = day_detail.get('main_star', '') if isinstance(day_detail, dict) else ''
                acc.append(f"day.main_star={star}")
            elif key == "main_star_in_pillar":
                if isinstance(value, dict):
                    pillar = value.get('pillar')
                    details = data.get('details', {})
                    if not isinstance(details, dict):
                        details = {}
                    pillar_detail = details.get(pillar or '', {})
                    if not isinstance(pillar_detail, dict):
                        pillar_detail = {}
                    star = pillar_detail.get('main_star', '') if isinstance(pillar_detail, dict) else ''
                    expected = value.get('eq') or value.get('in')
                    acc.append(f"{pillar}.main_star={star} (期望={expected})")
            elif key in ("ten_gods_main", "ten_gods_sub", "ten_gods_total"):
                stats_key_map = {
                    "ten_gods_main": "main",
                    "ten_gods_sub": "sub",
                    "ten_gods_total": "totals"
                }
                ten_gods_stats = data.get('ten_gods_stats', {})
                if not isinstance(ten_gods_stats, dict):
                    if isinstance(ten_gods_stats, str):
                        try:
                            ten_gods_stats = json.loads(ten_gods_stats)
                        except (json.JSONDecodeError, TypeError):
                            ten_gods_stats = {}
                    else:
                        ten_gods_stats = {}

                stats_map = ten_gods_stats.get(stats_key_map[key], {})
                if not isinstance(stats_map, dict):
                    if isinstance(stats_map, str):
                        try:
                            stats_map = json.loads(stats_map)
                        except (json.JSONDecodeError, TypeError):
                            stats_map = {}
                    else:
                        stats_map = {}

                names = []
                specified_pillars = None
                if isinstance(value, dict):
                    names = value.get('names') or []
                    specified_pillars = value.get('pillars')
                if not names:
                    names = list(stats_map.keys()) if isinstance(stats_map, dict) else []
                parts = []
                for name in names:
                    entry = stats_map.get(name, {'count': 0, 'pillars': {}}) if isinstance(stats_map, dict) else {'count': 0, 'pillars': {}}
                    if not isinstance(entry, dict):
                        if isinstance(entry, str):
                            try:
                                entry = json.loads(entry)
                            except (json.JSONDecodeError, TypeError):
                                entry = {'count': 0, 'pillars': {}}
                        else:
                            entry = {'count': 0, 'pillars': {}}

                    all_pillars = entry.get('pillars', {}) if isinstance(entry, dict) else {}
                    if not isinstance(all_pillars, dict):
                        all_pillars = {}

                    if specified_pillars:
                        filtered_pillars = {}
                        for p in specified_pillars:
                            if p in all_pillars:
                                filtered_pillars[p] = all_pillars[p]
                        filtered_count = sum(filtered_pillars.values())
                        pillar_detail = ", ".join(f"{p}:{cnt}" for p, cnt in filtered_pillars.items()) or "无"
                        parts.append(f"{name} -> count={filtered_count} [{pillar_detail}]")
                    else:
                        pillar_detail = ", ".join(f"{p}:{cnt}" for p, cnt in all_pillars.items()) or "无"
                        parts.append(f"{name} -> count={entry.get('count', 0)} [{pillar_detail}]")
                requirement = self._format_requirement(value if isinstance(value, dict) else None)
                acc.append(f"{key} {requirement}".strip() + " | " + "; ".join(parts))
            elif key == "day_branch_in":
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                day_pillar = bazi_pillars.get('day', {})
                if not isinstance(day_pillar, dict):
                    day_pillar = {}
                branch = day_pillar.get('branch', '') if isinstance(day_pillar, dict) else ''
                acc.append(f"day.branch={branch} (期望∈{value})")
            elif key == "day_branch_equals":
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                day_pillar = bazi_pillars.get('day', {})
                if not isinstance(day_pillar, dict):
                    day_pillar = {}
                branch = day_pillar.get('branch', '') if isinstance(day_pillar, dict) else ''
                acc.append(f"day.branch={branch} (期望={value})")
            elif key == "day_branch_element_in":
                elements = data.get('elements', {})
                if not isinstance(elements, dict):
                    if isinstance(elements, str):
                        try:
                            elements = json.loads(elements)
                        except (json.JSONDecodeError, TypeError):
                            elements = {}
                    else:
                        elements = {}
                day_element_info = elements.get('day', {})
                if not isinstance(day_element_info, dict):
                    if isinstance(day_element_info, str):
                        try:
                            day_element_info = json.loads(day_element_info)
                        except (json.JSONDecodeError, TypeError):
                            day_element_info = {}
                    else:
                        day_element_info = {}
                element = day_element_info.get('branch_element', '') if isinstance(day_element_info, dict) else ''
                acc.append(f"day.branch_element={element} (期望∈{value})")
            elif key == "pillar_element" and isinstance(value, dict):
                pillar = value.get('pillar')
                part = value.get('part', 'branch')
                elements = data.get('elements', {})
                if not isinstance(elements, dict):
                    if isinstance(elements, str):
                        try:
                            elements = json.loads(elements)
                        except (json.JSONDecodeError, TypeError):
                            elements = {}
                    else:
                        elements = {}
                pillar_element_info = elements.get(pillar or '', {})
                if not isinstance(pillar_element_info, dict):
                    if isinstance(pillar_element_info, str):
                        try:
                            pillar_element_info = json.loads(pillar_element_info)
                        except (json.JSONDecodeError, TypeError):
                            pillar_element_info = {}
                    else:
                        pillar_element_info = {}
                element = pillar_element_info.get(f"{part}_element", '') if isinstance(pillar_element_info, dict) else ''
                expected = value.get('in') or value.get('equals')
                acc.append(f"{pillar}.{part}_element={element} (期望={expected})")
            elif key == "element_total" and isinstance(value, dict):
                element_counts = data.get('element_counts', {})
                if not isinstance(element_counts, dict):
                    element_counts = {}

                names = value.get('names') or list(element_counts.keys()) if isinstance(element_counts, dict) else []
                contributions = self._describe_element_sources(data)
                if not isinstance(contributions, dict):
                    contributions = {}

                parts = []
                for name in names:
                    detail_sources_list = contributions.get(name, []) if isinstance(contributions, dict) else []
                    if not isinstance(detail_sources_list, list):
                        detail_sources_list = []
                    detail_sources = ", ".join(detail_sources_list) or "无"
                    count_value = element_counts.get(name, 0) if isinstance(element_counts, dict) else 0
                    parts.append(f"{name}:{count_value} [{detail_sources}]")
                requirement = self._format_requirement(value)
                acc.append(f"element_total {requirement}".strip() + " | " + "; ".join(parts))
            elif key == "element_relation":
                relationships = data.get('relationships', {})
                if not isinstance(relationships, dict):
                    if isinstance(relationships, str):
                        try:
                            relationships = json.loads(relationships)
                        except (json.JSONDecodeError, TypeError):
                            relationships = {}
                    else:
                        relationships = {}
                relations = relationships.get('element_relations', {}) if isinstance(relationships, dict) else {}
                acc.append("element_relations -> " + str(relations) + f" (期望={value})")
            elif key == "pillar_in" and isinstance(value, dict):
                pillar = value.get('pillar')
                part = value.get('part', 'branch')
                actual = self._get_pillar_part_value_for_debug(data, pillar, part)
                expected = value.get('values') or value.get('in')
                acc.append(f"pillar_in[{pillar}.{part}]={actual} (期望∈{expected})")
            elif key == "pillar_equals" and isinstance(value, dict):
                pillar = value.get('pillar')
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                pillar_data = bazi_pillars.get(pillar or '', {})
                if not isinstance(pillar_data, dict):
                    pillar_data = {}
                actual = f"{pillar_data.get('stem', '')}{pillar_data.get('branch', '')}"
                acc.append(f"{pillar}.pillar={actual} (期望={value.get('values')})")
            elif key == "stems_count" and isinstance(value, dict):
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                stems = []
                for p in ['year', 'month', 'day', 'hour']:
                    pd = bazi_pillars.get(p, {})
                    if isinstance(pd, dict):
                        stems.append(pd.get('stem', ''))
                    else:
                        stems.append('')
                stem_counts = {}
                for s in stems:
                    stem_counts[s] = stem_counts.get(s, 0) + 1
                requirement = self._format_requirement(value)
                acc.append(f"stems={stems}; 统计={stem_counts} {requirement}".strip())
            elif key == "branches_count" and isinstance(value, dict):
                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}
                branches = []
                for p in ['year', 'month', 'day', 'hour']:
                    pd = bazi_pillars.get(p, {})
                    if isinstance(pd, dict):
                        branches.append(pd.get('branch', ''))
                    else:
                        branches.append('')
                branch_counts = {}
                for b in branches:
                    branch_counts[b] = branch_counts.get(b, 0) + 1
                requirement = self._format_requirement(value)
                acc.append(f"branches={branches}; 统计={branch_counts} {requirement}".strip())
            elif key == "pillar_relation" and isinstance(value, dict):
                pillar_a = value.get('pillar_a')
                pillar_b = value.get('pillar_b')
                part = value.get('part', 'branch')
                va = self._get_pillar_part_value_for_debug(data, pillar_a, part)
                vb = self._get_pillar_part_value_for_debug(data, pillar_b, part)
                relation = value.get('relation')
                acc.append(f"relation[{pillar_a}.{part},{pillar_b}.{part}]={va},{vb} (期望={relation})")
            elif key == "ten_god_combines" and isinstance(value, dict):
                god = value.get('god', '')
                source = value.get('source', 'any')
                pillars_list = value.get('pillars', [])
                target_pillars = value.get('target_pillars', [])
                target_part = value.get('target_part', 'stem')
                relation = value.get('relation', 'he')

                details = data.get('details', {})
                if not isinstance(details, dict):
                    if isinstance(details, str):
                        try:
                            details = json.loads(details)
                        except (json.JSONDecodeError, TypeError):
                            details = {}
                    else:
                        details = {}

                bazi_pillars = data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    bazi_pillars = {}

                found_info = []
                for p in pillars_list:
                    detail = details.get(p, {}) if isinstance(details, dict) else {}
                    if not isinstance(detail, dict):
                        if isinstance(detail, str):
                            try:
                                detail = json.loads(detail)
                            except (json.JSONDecodeError, TypeError):
                                detail = {}
                        else:
                            detail = {}

                    candidate_stars = []
                    if source in {'main', 'any'}:
                        main_star = detail.get('main_star') if isinstance(detail, dict) else None
                        if main_star:
                            candidate_stars.append(f"主星:{main_star}")
                    if source in {'sub', 'any'}:
                        sub_stars = []
                        if isinstance(detail, dict):
                            sub_stars = detail.get('sub_stars') or detail.get('hidden_stars') or []
                        if not isinstance(sub_stars, list):
                            sub_stars = []
                        if sub_stars:
                            candidate_stars.append(f"副星:{','.join(sub_stars)}")

                    main_star_list = []
                    if isinstance(detail, dict):
                        ms = detail.get('main_star')
                        if ms:
                            main_star_list = [ms]

                    sub_stars_list = []
                    if isinstance(detail, dict):
                        sub_stars_list = detail.get('sub_stars') or detail.get('hidden_stars') or []
                        if not isinstance(sub_stars_list, list):
                            sub_stars_list = []

                    if god in main_star_list + sub_stars_list:
                        pd = bazi_pillars.get(p, {}) if isinstance(bazi_pillars, dict) else {}
                        if not isinstance(pd, dict):
                            pd = {}
                        source_value = pd.get(target_part) if target_part in ('stem', 'branch') and isinstance(pd, dict) else None
                        if source_value:
                            found_info.append(f"{p}柱({source_value})")

                target_info = []
                for tp in target_pillars:
                    td = bazi_pillars.get(tp, {}) if isinstance(bazi_pillars, dict) else {}
                    if not isinstance(td, dict):
                        td = {}
                    target_value = td.get(target_part) if target_part in ('stem', 'branch') and isinstance(td, dict) else None
                    if target_value:
                        target_info.append(f"{tp}柱({target_value})")

                relation_name = {'he': '天干合', 'liuhe': '地支六合', 'chong': '冲', 'xing': '刑', 'hai': '害', 'po': '破'}.get(relation, relation)
                acc.append(f"ten_god_combines: 查找{god}({source}) -> 在{pillars_list}柱中查找 -> 找到: {', '.join(found_info) if found_info else '无'} -> 目标{target_part}({','.join(target_info)}) -> 关系:{relation_name}")
            elif key in ("deities_in_year", "deities_in_month", "deities_in_day", "deities_in_hour"):
                pillar_map = {
                    "deities_in_year": "year",
                    "deities_in_month": "month",
                    "deities_in_day": "day",
                    "deities_in_hour": "hour"
                }
                pillar = pillar_map.get(key)
                if pillar:
                    details = data.get('details', {})
                    if not isinstance(details, dict):
                        if isinstance(details, str):
                            try:
                                details = json.loads(details)
                            except (json.JSONDecodeError, TypeError):
                                details = {}
                        else:
                            details = {}

                    pillar_details = details.get(pillar, {}) if isinstance(details, dict) else {}
                    if not isinstance(pillar_details, dict):
                        if isinstance(pillar_details, str):
                            try:
                                pillar_details = json.loads(pillar_details)
                            except (json.JSONDecodeError, TypeError):
                                pillar_details = {}
                        else:
                            pillar_details = {}

                    deities = pillar_details.get('deities', []) if isinstance(pillar_details, dict) else []
                    if not isinstance(deities, list):
                        deities = [deities] if deities else []

                    expected_deities = value if isinstance(value, list) else [value]
                    found_deities = [d for d in expected_deities if d in deities]
                    missing_deities = [d for d in expected_deities if d not in deities]

                    if found_deities:
                        found_str = f"找到: {', '.join(found_deities)}"
                    else:
                        found_str = "未找到"

                    if missing_deities:
                        missing_str = f"缺少: {', '.join(missing_deities)}"
                    else:
                        missing_str = ""

                    all_deities_str = f"该柱所有神煞: {', '.join(deities) if deities else '无'}"
                    acc.append(f"{key}: {found_str} {missing_str} | {all_deities_str}")
            elif key == "branch_adjacent" and isinstance(value, dict):
                pairs = value.get('pairs', [])
                bazi_pillars = data.get('bazi_pillars', {})
                branches = [
                    bazi_pillars.get('year', {}).get('branch', ''),
                    bazi_pillars.get('month', {}).get('branch', ''),
                    bazi_pillars.get('day', {}).get('branch', ''),
                    bazi_pillars.get('hour', {}).get('branch', '')
                ]

                found_pairs = []
                for pair in pairs:
                    if len(pair) == 2:
                        a, b = pair[0], pair[1]
                        for i in range(len(branches) - 1):
                            if (branches[i] == a and branches[i + 1] == b) or (branches[i] == b and branches[i + 1] == a):
                                found_pairs.append(f"{branches[i]}{branches[i + 1]}")
                                break

                if found_pairs:
                    found_str = f"找到紧挨的地支对: {', '.join(found_pairs)}"
                else:
                    found_str = "未找到紧挨的地支对"

                expected_pairs_str = ", ".join([f"{p[0]}{p[1]}" for p in pairs])
                branches_str = "".join(branches)
                acc.append(f"{key}: {found_str} | 期望: {expected_pairs_str} | 实际地支序列: {branches_str}")
            elif key == "branch_offset" and isinstance(value, dict):
                source = value.get('source', '')
                target = value.get('target', '')
                offset = value.get('offset', 0)

                bazi_pillars = data.get('bazi_pillars', {})
                source_branch = bazi_pillars.get(source, {}).get('branch', '')
                target_branch = bazi_pillars.get(target, {}).get('branch', '')

                if source_branch and target_branch:
                    branch_sequence = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
                    try:
                        source_index = branch_sequence.index(source_branch)
                        target_index = branch_sequence.index(target_branch)
                        actual_offset = target_index - source_index
                        if actual_offset > 6:
                            actual_offset -= 12
                        elif actual_offset < -6:
                            actual_offset += 12

                        expected_index = (source_index + offset) % len(branch_sequence)
                        expected_branch = branch_sequence[expected_index]

                        pillar_names = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}
                        source_name = pillar_names.get(source, source)
                        target_name = pillar_names.get(target, target)

                        if actual_offset == offset:
                            match_str = "✓ 满足"
                        else:
                            match_str = "✗ 不满足"

                        acc.append(f"{key}: {match_str} | {source_name}支={source_branch}(索引{source_index}) + offset({offset}) = 期望{expected_branch}(索引{expected_index}) | 实际{target_name}支={target_branch}(索引{target_index}, 实际偏移{actual_offset})")
                    except ValueError:
                        acc.append(f"{key}: 错误 - 无法找到地支索引")
                else:
                    acc.append(f"{key}: 错误 - 缺少{source}支或{target}支")
            else:
                acc.append(f"{key}:当前值暂无调试信息")
        return acc

    def _get_pillar_part_value_for_debug(self, data, pillar, part):
        if not pillar:
            return None

        if part == 'stem':
            bazi_pillars = data.get('bazi_pillars', {})
            if not isinstance(bazi_pillars, dict):
                bazi_pillars = {}
            pillar_info = bazi_pillars.get(pillar, {})
            if not isinstance(pillar_info, dict):
                pillar_info = {}
            return pillar_info.get('stem', '') if isinstance(pillar_info, dict) else ''

        if part == 'branch':
            bazi_pillars = data.get('bazi_pillars', {})
            if not isinstance(bazi_pillars, dict):
                bazi_pillars = {}
            pillar_info = bazi_pillars.get(pillar, {})
            if not isinstance(pillar_info, dict):
                pillar_info = {}
            return pillar_info.get('branch', '') if isinstance(pillar_info, dict) else ''

        if part == 'nayin':
            details = data.get('details', {})
            if not isinstance(details, dict):
                if isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except (json.JSONDecodeError, TypeError):
                        details = {}
                else:
                    details = {}
            pillar_detail = details.get(pillar, {}) if isinstance(details, dict) else {}
            if not isinstance(pillar_detail, dict):
                if isinstance(pillar_detail, str):
                    try:
                        pillar_detail = json.loads(pillar_detail)
                    except (json.JSONDecodeError, TypeError):
                        pillar_detail = {}
                else:
                    pillar_detail = {}
            return pillar_detail.get('nayin', '') if isinstance(pillar_detail, dict) else ''

        if part == 'kongwang':
            details = data.get('details', {})
            if not isinstance(details, dict):
                if isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except (json.JSONDecodeError, TypeError):
                        details = {}
                else:
                    details = {}
            pillar_detail = details.get(pillar, {}) if isinstance(details, dict) else {}
            if not isinstance(pillar_detail, dict):
                if isinstance(pillar_detail, str):
                    try:
                        pillar_detail = json.loads(pillar_detail)
                    except (json.JSONDecodeError, TypeError):
                        pillar_detail = {}
                else:
                    pillar_detail = {}
            return pillar_detail.get('kongwang', '') if isinstance(pillar_detail, dict) else ''

        if part == 'pillar':
            bazi_pillars = data.get('bazi_pillars', {})
            if not isinstance(bazi_pillars, dict):
                bazi_pillars = {}
            pillar_data = bazi_pillars.get(pillar, {})
            if not isinstance(pillar_data, dict):
                pillar_data = {}
            return f"{pillar_data.get('stem', '')}{pillar_data.get('branch', '')}"

        details = data.get('details', {})
        if not isinstance(details, dict):
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except (json.JSONDecodeError, TypeError):
                    details = {}
            else:
                details = {}
        pillar_detail = details.get(pillar, {}) if isinstance(details, dict) else {}
        if not isinstance(pillar_detail, dict):
            if isinstance(pillar_detail, str):
                try:
                    pillar_detail = json.loads(pillar_detail)
                except (json.JSONDecodeError, TypeError):
                    pillar_detail = {}
            else:
                pillar_detail = {}
        return pillar_detail.get(part, '') if isinstance(pillar_detail, dict) else ''

    def _format_requirement(self, spec):
        if not spec or not isinstance(spec, dict):
            return ""
        parts = []
        if spec.get('names'):
            parts.append(f"names={spec['names']}")
        if spec.get('eq') is not None:
            parts.append(f"= {spec['eq']}")
        if spec.get('min') is not None:
            parts.append(f"≥ {spec['min']}")
        if spec.get('max') is not None:
            parts.append(f"≤ {spec['max']}")
        if spec.get('pillars'):
            parts.append(f"pillars={spec['pillars']}")
        return "(" + ", ".join(parts) + ")" if parts else ""

    def _describe_element_sources(self, data):
        elements = data.get('elements', {}) or {}
        if not isinstance(elements, dict):
            if isinstance(elements, str):
                try:
                    elements = json.loads(elements)
                except (json.JSONDecodeError, TypeError):
                    elements = {}
            else:
                elements = {}

        contributions = {}
        for pillar, info in elements.items():
            if not isinstance(info, dict):
                if isinstance(info, str):
                    try:
                        info = json.loads(info)
                    except (json.JSONDecodeError, TypeError):
                        info = {}
                else:
                    info = {}

            stem = info.get('stem') if isinstance(info, dict) else None
            stem_el = info.get('stem_element') if isinstance(info, dict) else None
            if stem_el and stem:
                contributions.setdefault(stem_el, []).append(f"{pillar}.stem({stem})")
            branch = info.get('branch') if isinstance(info, dict) else None
            branch_el = info.get('branch_element') if isinstance(info, dict) else None
            if branch_el and branch:
                contributions.setdefault(branch_el, []).append(f"{pillar}.branch({branch})")
        return contributions
