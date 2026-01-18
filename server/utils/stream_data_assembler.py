#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口数据组装工具

设计原则：
1. 从 UnifiedBaziData 统一数据源组装各接口所需的 input_data
2. 各接口使用相同的数据结构（StreamInputData），只是填充不同字段
3. 不做任何计算，只负责数据转换和组装

使用方式：
    from server.utils.stream_data_assembler import StreamDataAssembler
    from server.services.unified_bazi_data_provider import UnifiedBaziDataProvider
    
    # 获取统一数据
    unified_data = await UnifiedBaziDataProvider.get_unified_data(...)
    
    # 组装为各接口所需的 input_data
    health_input = StreamDataAssembler.assemble_for_health(unified_data, health_result)
    marriage_input = StreamDataAssembler.assemble_for_marriage(unified_data, marriage_result)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from server.models.stream_input_data import UnifiedBaziData, StreamInputData
from server.models.dayun import DayunModel
from server.models.special_liunian import SpecialLiunianModel

logger = logging.getLogger(__name__)


class StreamDataAssembler:
    """
    流式接口数据组装工具
    
    职责：
    1. 将 UnifiedBaziData 转换为各接口所需的 StreamInputData
    2. 确保数据格式统一
    3. 不做任何计算，只负责组装
    """
    
    @staticmethod
    def assemble_for_health(
        unified_data: UnifiedBaziData,
        health_result: Optional[Dict[str, Any]] = None,
        health_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        为健康分析接口组装 input_data
        
        Args:
            unified_data: 统一的八字数据
            health_result: HealthAnalysisService.analyze() 的结果（可选）
            health_rules: 匹配的健康规则（可选）
            
        Returns:
            dict: 健康分析接口的 input_data
        """
        # 1. 命盘体质总论
        mingpan_tizhi_zonglun = StreamDataAssembler._build_mingpan_section(unified_data)
        
        # 2. 大运健康警示
        dayun_jiankang = StreamDataAssembler._build_dayun_health_section(unified_data)
        
        # 3. 五行病理推演（需要 health_result）
        wuxing_bingli = {}
        if health_result:
            wuxing_bingli = {
                'pathology_tendency': health_result.get('pathology_tendency', {}),
                'wuxing_shengke': health_result.get('pathology_tendency', {}).get('wuxing_relations', {}),
                'body_algorithm': health_result.get('body_algorithm', {}),
                'wuxing_balance': health_result.get('wuxing_balance', '')
            }
        
        # 4. 体质调理建议
        tizhi_tiaoli = {
            'xi_ji': {
                'xi_shen': unified_data.wangshuai.xi_shen,
                'ji_shen': unified_data.wangshuai.ji_shen,
                'xi_shen_elements': unified_data.wangshuai.xi_shen_elements,
                'ji_shen_elements': unified_data.wangshuai.ji_shen_elements
            },
            'zangfu_yanghu': health_result.get('zangfu_care', {}) if health_result else {},
            'wuxing_tuning': health_result.get('wuxing_tuning', {}) if health_result else {}
        }
        
        # 5. 组装最终 input_data
        input_data = {
            'mingpan_tizhi_zonglun': mingpan_tizhi_zonglun,
            'dayun_jiankang': dayun_jiankang,
            'wuxing_bingli': wuxing_bingli,
            'tizhi_tiaoli': tizhi_tiaoli
        }
        
        # 6. 添加健康规则
        if health_rules:
            input_data['health_rules'] = {
                'matched_rules': health_rules,
                'rules_count': len(health_rules),
                'rule_judgments': [
                    rule.get('content', {}).get('text', '') 
                    for rule in health_rules 
                    if rule.get('content', {}).get('text')
                ]
            }
        
        return input_data
    
    @staticmethod
    def assemble_for_marriage(
        unified_data: UnifiedBaziData,
        marriage_result: Optional[Dict[str, Any]] = None,
        marriage_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        为婚姻分析接口组装 input_data
        
        Args:
            unified_data: 统一的八字数据
            marriage_result: 婚姻分析结果（可选）
            marriage_rules: 匹配的婚姻规则（可选）
            
        Returns:
            dict: 婚姻分析接口的 input_data
        """
        # 1. 命盘基础
        mingpan_tizhi_zonglun = StreamDataAssembler._build_mingpan_section(unified_data)
        
        # 2. 大运流年
        dayun_jiankang = StreamDataAssembler._build_dayun_health_section(unified_data)
        
        # 3. 婚姻专用数据
        marriage_data = marriage_result or {}
        
        input_data = {
            'mingpan_tizhi_zonglun': mingpan_tizhi_zonglun,
            'dayun_jiankang': dayun_jiankang,
            'marriage_data': marriage_data
        }
        
        if marriage_rules:
            input_data['matched_rules'] = marriage_rules
        
        return input_data
    
    @staticmethod
    def assemble_for_career(
        unified_data: UnifiedBaziData,
        career_result: Optional[Dict[str, Any]] = None,
        career_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        为事业财富分析接口组装 input_data
        """
        mingpan_tizhi_zonglun = StreamDataAssembler._build_mingpan_section(unified_data)
        dayun_jiankang = StreamDataAssembler._build_dayun_health_section(unified_data)
        
        input_data = {
            'mingpan_tizhi_zonglun': mingpan_tizhi_zonglun,
            'dayun_jiankang': dayun_jiankang,
            'career_wealth_data': career_result or {}
        }
        
        if career_rules:
            input_data['matched_rules'] = career_rules
        
        return input_data
    
    @staticmethod
    def assemble_for_general_review(
        unified_data: UnifiedBaziData,
        general_result: Optional[Dict[str, Any]] = None,
        general_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        为总评分析接口组装 input_data
        """
        mingpan_tizhi_zonglun = StreamDataAssembler._build_mingpan_section(unified_data)
        dayun_jiankang = StreamDataAssembler._build_dayun_health_section(unified_data)
        
        input_data = {
            'mingpan_tizhi_zonglun': mingpan_tizhi_zonglun,
            'dayun_jiankang': dayun_jiankang,
            'general_review_data': general_result or {}
        }
        
        if general_rules:
            input_data['matched_rules'] = general_rules
        
        return input_data
    
    @staticmethod
    def assemble_for_children_study(
        unified_data: UnifiedBaziData,
        children_result: Optional[Dict[str, Any]] = None,
        children_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        为子女学业分析接口组装 input_data
        """
        mingpan_tizhi_zonglun = StreamDataAssembler._build_mingpan_section(unified_data)
        dayun_jiankang = StreamDataAssembler._build_dayun_health_section(unified_data)
        
        input_data = {
            'mingpan_tizhi_zonglun': mingpan_tizhi_zonglun,
            'dayun_jiankang': dayun_jiankang,
            'children_study_data': children_result or {}
        }
        
        if children_rules:
            input_data['matched_rules'] = children_rules
        
        return input_data
    
    @staticmethod
    def _build_mingpan_section(unified_data: UnifiedBaziData) -> Dict[str, Any]:
        """
        构建命盘体质总论部分
        
        包含：四柱、日主、五行、旺衰等基础信息
        """
        # 提取日主信息
        day_pillar = unified_data.bazi_pillars.day
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        
        # 计算日主五行
        from core.data.constants import STEM_ELEMENTS
        day_element = STEM_ELEMENTS.get(day_stem, '')
        
        return {
            'bazi_pillars': {
                'year': unified_data.bazi_pillars.year,
                'month': unified_data.bazi_pillars.month,
                'day': unified_data.bazi_pillars.day,
                'hour': unified_data.bazi_pillars.hour
            },
            'day_master': {
                'stem': day_stem,
                'branch': day_branch,
                'element': day_element
            },
            'elements': unified_data.element_counts,
            'wangshuai': unified_data.wangshuai.wangshuai,
            'wangshuai_degree': unified_data.wangshuai.wangshuai_degree,
            'xi_shen_elements': unified_data.wangshuai.xi_shen_elements,
            'ji_shen_elements': unified_data.wangshuai.ji_shen_elements
        }
    
    @staticmethod
    def _build_dayun_health_section(unified_data: UnifiedBaziData) -> Dict[str, Any]:
        """
        构建大运健康警示部分
        
        包含：当前大运、关键大运、特殊流年（按大运分组）
        """
        # 1. 当前大运
        current_dayun_data = None
        if unified_data.current_dayun:
            current_dayun_data = {
                'step': unified_data.current_dayun.step,
                'stem': unified_data.current_dayun.stem,
                'branch': unified_data.current_dayun.branch,
                'ganzhi': unified_data.current_dayun.ganzhi,
                'year_start': unified_data.current_dayun.year_start,
                'year_end': unified_data.current_dayun.year_end,
                'age_display': unified_data.current_dayun.age_display
            }
        
        # 2. 所有大运
        all_dayuns = [
            {
                'step': d.step,
                'stem': d.stem,
                'branch': d.branch,
                'ganzhi': d.ganzhi,
                'year_start': d.year_start,
                'year_end': d.year_end,
                'age_display': d.age_display
            }
            for d in unified_data.dayun_sequence
        ]
        
        # 3. 特殊流年按大运分组
        special_liunians_by_dayun = StreamDataAssembler._organize_special_by_dayun(
            unified_data.special_liunians,
            unified_data.dayun_sequence
        )
        
        # 4. 识别关键大运（有特殊流年的大运）
        key_dayuns = []
        for dayun in unified_data.dayun_sequence:
            dayun_special = special_liunians_by_dayun.get(dayun.step, {})
            if dayun_special.get('special_liunians'):
                key_dayuns.append({
                    'step': dayun.step,
                    'stem': dayun.stem,
                    'branch': dayun.branch,
                    'ganzhi': dayun.ganzhi,
                    'year_start': dayun.year_start,
                    'year_end': dayun.year_end,
                    'special_count': len(dayun_special.get('special_liunians', []))
                })
        
        return {
            'current_dayun': current_dayun_data,
            'all_dayuns': all_dayuns,
            'key_dayuns': key_dayuns,
            'special_liunians_by_dayun': special_liunians_by_dayun
        }
    
    @staticmethod
    def _organize_special_by_dayun(
        special_liunians: List[SpecialLiunianModel],
        dayun_sequence: List[DayunModel]
    ) -> Dict[int, Dict[str, Any]]:
        """
        将特殊流年按大运分组
        
        Returns:
            dict: {
                dayun_step: {
                    'dayun_info': {...},
                    'special_liunians': [...]
                }
            }
        """
        result = {}
        
        # 初始化每个大运的分组
        for dayun in dayun_sequence:
            result[dayun.step] = {
                'dayun_info': {
                    'step': dayun.step,
                    'ganzhi': dayun.ganzhi,
                    'year_start': dayun.year_start,
                    'year_end': dayun.year_end
                },
                'special_liunians': []
            }
        
        # 将特殊流年分配到对应大运
        for sl in special_liunians:
            dayun_step = sl.dayun_step
            if dayun_step is not None and dayun_step in result:
                result[dayun_step]['special_liunians'].append({
                    'year': sl.year,
                    'ganzhi': sl.ganzhi,
                    'relations': sl.relations,
                    'age_display': sl.age_display
                })
        
        return result
