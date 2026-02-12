#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据组装器 - 从原始计算结果组装各模块数据

从 BaziDataOrchestrator 拆分出的数据组装逻辑，职责单一，不引用 Orchestrator。
编排层调用 BaziDataAssembler 进行数据组装。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.data.constants import BRANCH_ELEMENTS, STEM_ELEMENTS
from server.services.config_service import ConfigService
from server.services.mingge_extractor import extract_mingge_names_from_rules

logger = logging.getLogger(__name__)


class BaziDataAssembler:
    """数据组装器 - 从原始计算结果组装各模块数据"""

    @staticmethod
    def get_dayun_by_mode(
        dayun_sequence: List[Dict],
        current_time: datetime,
        birth_year: int,
        mode: Optional[str] = None,
        count: Optional[int] = None,
        indices: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        根据模式获取大运列表

        Args:
            dayun_sequence: 完整的大运序列
            current_time: 当前时间
            birth_year: 出生年份
            mode: 查询模式 ('count', 'current', 'current_with_neighbors', 'indices')
            count: 数量（仅用于 count 模式）
            indices: 索引列表（用于 indices 模式）

        Returns:
            筛选后的大运列表
        """
        if not dayun_sequence:
            return []

        current_age = current_time.year - birth_year + 1
        current_dayun_index = None

        for idx, dayun in enumerate(dayun_sequence):
            age_range = dayun.get('age_range', {})
            if age_range:
                age_start = age_range.get('start', 0)
                age_end = age_range.get('end', 0)
                if age_start <= current_age <= age_end:
                    current_dayun_index = idx
                    break

        if mode == 'current':
            if current_dayun_index is not None:
                return [dayun_sequence[current_dayun_index]]
            return []

        if mode == 'current_with_neighbors':
            if current_dayun_index is None:
                return []
            result = []
            if current_dayun_index > 0:
                result.append(dayun_sequence[current_dayun_index - 1])
            result.append(dayun_sequence[current_dayun_index])
            if current_dayun_index < len(dayun_sequence) - 1:
                result.append(dayun_sequence[current_dayun_index + 1])
            return result

        if mode == 'indices' and indices:
            result = []
            for idx in indices:
                if 0 <= idx < len(dayun_sequence):
                    result.append(dayun_sequence[idx])
            return result

        if mode == 'count' or mode is None:
            count = count or 8
            return dayun_sequence[:count] if count <= len(dayun_sequence) else dayun_sequence

        return []

    @staticmethod
    def _calculate_element_relations(proportions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """分析五行相生相克关系"""
        element_relations_map = {
            '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
            '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
            '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
            '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
            '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
        }

        relations = {
            'produces': [],
            'controls': [],
            'produced_by': [],
            'controlled_by': []
        }

        for element, data in proportions.items():
            if data.get('count', 0) == 0:
                continue
            element_relation = element_relations_map.get(element, {})

            produces = element_relation.get('produces', '')
            if produces and proportions.get(produces, {}).get('count', 0) > 0:
                relations['produces'].append({
                    'from': element, 'to': produces,
                    'from_count': data['count'], 'to_count': proportions[produces]['count']
                })
            controls = element_relation.get('controls', '')
            if controls and proportions.get(controls, {}).get('count', 0) > 0:
                relations['controls'].append({
                    'from': element, 'to': controls,
                    'from_count': data['count'], 'to_count': proportions[controls]['count']
                })
            produced_by = element_relation.get('produced_by', '')
            if produced_by and proportions.get(produced_by, {}).get('count', 0) > 0:
                relations['produced_by'].append({
                    'from': produced_by, 'to': element,
                    'from_count': proportions[produced_by]['count'], 'to_count': data['count']
                })
            controlled_by = element_relation.get('controlled_by', '')
            if controlled_by and proportions.get(controlled_by, {}).get('count', 0) > 0:
                relations['controlled_by'].append({
                    'from': controlled_by, 'to': element,
                    'from_count': proportions[controlled_by]['count'], 'to_count': data['count']
                })

        return relations

    @staticmethod
    def assemble_wuxing_proportion(
        bazi_data: Dict[str, Any],
        wangshuai_data: Dict[str, Any],
        solar_date: str,
        solar_time: str,
        gender: str
    ) -> Optional[Dict[str, Any]]:
        """
        从已有数据组装五行占比数据
        与 WuxingProportionService.calculate_proportion() 格式一致
        """
        try:
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            details = bazi_data.get('details', {})

            if not bazi_pillars or not isinstance(bazi_pillars, dict):
                logger.warning("[BaziDataAssembler] bazi_pillars 数据无效")
                return None

            element_counts = {'金': 0, '木': 0, '水': 0, '火': 0, '土': 0}
            element_details = {'金': [], '木': [], '水': [], '火': [], '土': []}

            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(pillar_name, {})
                stem = pillar.get('stem', '')
                if stem and stem in STEM_ELEMENTS:
                    element = STEM_ELEMENTS[stem]
                    element_counts[element] += 1
                    element_details[element].append(stem)

            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(pillar_name, {})
                branch = pillar.get('branch', '')
                if branch and branch in BRANCH_ELEMENTS:
                    element = BRANCH_ELEMENTS[branch]
                    element_counts[element] += 1
                    element_details[element].append(branch)

            total = 8
            proportions = {}
            for element in ['金', '木', '水', '火', '土']:
                count = element_counts[element]
                percentage = round(count / total * 100, 2) if total > 0 else 0.0
                proportions[element] = {
                    'count': count,
                    'percentage': percentage,
                    'details': element_details[element]
                }

            ten_gods_info = {}
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar_detail = details.get(pillar_name, {}) or {}
                main_star = pillar_detail.get('main_star', '')
                hidden_stars = pillar_detail.get('hidden_stars', []) or []
                ten_gods_info[pillar_name] = {'main_star': main_star, 'hidden_stars': hidden_stars}

            element_relations = BaziDataAssembler._calculate_element_relations(proportions)
            wangshuai_result = wangshuai_data.get('data', wangshuai_data) if isinstance(wangshuai_data, dict) and 'data' in wangshuai_data else wangshuai_data

            return {
                "success": True,
                "bazi_pillars": bazi_pillars,
                "proportions": proportions,
                "ten_gods": ten_gods_info,
                "wangshuai": wangshuai_result,
                "element_relations": element_relations,
                "bazi_data": bazi_data
            }
        except Exception as e:
            logger.error(f"[BaziDataAssembler] 组装五行占比数据失败: {e}", exc_info=True)
            return None

    @staticmethod
    def assemble_xishen_jishen(
        bazi_data: Dict[str, Any],
        wangshuai_data: Dict[str, Any],
        rules_data: List[Dict[str, Any]],
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: Optional[str] = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        从已有数据组装喜神忌神完整数据
        与 get_xishen_jishen() 格式一致
        """
        try:
            wangshuai_data_inner = wangshuai_data.get('data', wangshuai_data) if isinstance(wangshuai_data, dict) and 'data' in wangshuai_data else wangshuai_data
            final_xi_ji = wangshuai_data_inner.get('final_xi_ji', {})

            if final_xi_ji and final_xi_ji.get('xi_shen_elements'):
                xi_shen_elements_raw = final_xi_ji.get('xi_shen_elements', [])
                ji_shen_elements_raw = final_xi_ji.get('ji_shen_elements', [])
            else:
                xi_shen_elements_raw = wangshuai_data_inner.get('xi_shen_elements', [])
                ji_shen_elements_raw = wangshuai_data_inner.get('ji_shen_elements', [])

            shishen_mingge_names = []
            if rules_data:
                shishen_rules = [r for r in rules_data if r.get('rule_type', '') == 'shishen']
                if shishen_rules:
                    shishen_mingge_names = extract_mingge_names_from_rules(shishen_rules)

            xi_shen_elements = ConfigService.map_elements_to_ids(xi_shen_elements_raw)
            ji_shen_elements = ConfigService.map_elements_to_ids(ji_shen_elements_raw)
            shishen_mingge = ConfigService.map_mingge_to_ids(shishen_mingge_names)

            bazi_pillars = bazi_data.get('bazi_pillars', {})
            day_stem = bazi_pillars.get('day', {}).get('stem', '')
            ten_gods = bazi_data.get('ten_gods', {})
            if not ten_gods:
                details = bazi_data.get('details', {})
                ten_gods = {}
                for pillar_name in ['year', 'month', 'day', 'hour']:
                    pillar_detail = details.get(pillar_name, {}) or {}
                    ten_gods[pillar_name] = {
                        'main_star': pillar_detail.get('main_star', ''),
                        'hidden_stars': pillar_detail.get('hidden_stars', [])
                    }
            element_counts = bazi_data.get('element_counts', {})
            deities = {}
            details = bazi_data.get('details', {})
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar_detail = details.get(pillar_name, {}) or {}
                deities[pillar_name] = pillar_detail.get('deities', [])

            wangshuai_detail = {
                'wangshuai': wangshuai_data_inner.get('wangshuai', ''),
                'total_score': wangshuai_data_inner.get('total_score', 0)
            }
            for key in ['de_ling', 'de_di', 'de_zhu']:
                if key in wangshuai_data_inner:
                    wangshuai_detail[key] = wangshuai_data_inner.get(key)

            response_data = {
                'solar_date': solar_date,
                'solar_time': solar_time,
                'gender': gender,
                'xi_shen_elements': xi_shen_elements,
                'ji_shen_elements': ji_shen_elements,
                'shishen_mingge': shishen_mingge,
                'wangshuai': wangshuai_data_inner.get('wangshuai', ''),
                'total_score': wangshuai_data_inner.get('total_score', 0),
                'bazi_pillars': bazi_pillars,
                'day_stem': day_stem,
                'ten_gods': ten_gods,
                'element_counts': element_counts,
                'deities': deities,
                'wangshuai_detail': wangshuai_detail
            }

            return {"success": True, "data": response_data}
        except Exception as e:
            logger.error(f"[BaziDataAssembler] 组装喜神忌神数据失败: {e}", exc_info=True)
            return None
