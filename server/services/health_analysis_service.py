#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康分析服务
基于五行理论分析身体健康状况
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class HealthAnalysisService:
    """健康分析服务"""
    
    # 五行与五脏对应关系
    ELEMENT_ORGAN_MAP = {
        '木': '肝',
        '火': '心',
        '土': '脾',
        '金': '肺',
        '水': '肾'
    }
    
    # 五行与五脏的详细对应
    ORGAN_ELEMENT_DETAIL = {
        '肝': {
            'element': '木',
            'description': '肝主疏泄，主藏血，开窍于目',
            'health_functions': ['疏泄', '藏血', '主筋', '开窍于目']
        },
        '心': {
            'element': '火',
            'description': '心主血脉，主神明，开窍于舌',
            'health_functions': ['主血脉', '主神明', '开窍于舌']
        },
        '脾': {
            'element': '土',
            'description': '脾主运化，主统血，开窍于口',
            'health_functions': ['运化', '统血', '主肌肉', '开窍于口']
        },
        '肺': {
            'element': '金',
            'description': '肺主气，主宣发肃降，开窍于鼻',
            'health_functions': ['主气', '主宣发肃降', '主皮毛', '开窍于鼻']
        },
        '肾': {
            'element': '水',
            'description': '肾主藏精，主水，主纳气，开窍于耳',
            'health_functions': ['藏精', '主水', '主骨', '开窍于耳']
        }
    }
    
    @staticmethod
    def analyze(
        bazi_data: Dict[str, Any],
        element_counts: Dict[str, int],
        wangshuai_data: Dict[str, Any],
        xi_ji_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        综合分析健康状况
        
        Args:
            bazi_data: 八字数据
            element_counts: 五行统计
            wangshuai_data: 旺衰数据
            xi_ji_data: 喜忌数据
            
        Returns:
            dict: 健康分析结果
        """
        logger.info("🔍 健康分析服务: 开始分析")
        
        try:
            # 1. 五行五脏对应分析
            body_algorithm = HealthAnalysisService.calculate_body_algorithm(
                element_counts, wangshuai_data
            )
            
            # 2. 病理倾向分析
            pathology_tendency = HealthAnalysisService.analyze_pathology_tendency(
                element_counts, wangshuai_data
            )
            
            # 3. 五行调和方案
            wuxing_tuning = HealthAnalysisService.generate_wuxing_tuning(
                xi_ji_data, element_counts
            )
            
            # 4. 脏腑养护建议
            zangfu_care = HealthAnalysisService.generate_zangfu_care(
                body_algorithm, xi_ji_data
            )
            
            # 5. 五行平衡情况
            wuxing_balance = HealthAnalysisService.analyze_wuxing_balance(element_counts)
            
            result = {
                'success': True,
                'body_algorithm': body_algorithm,
                'pathology_tendency': pathology_tendency,
                'wuxing_tuning': wuxing_tuning,
                'zangfu_care': zangfu_care,
                'wuxing_balance': wuxing_balance
            }
            
            logger.info("✅ 健康分析服务: 分析成功")
            return result
            
        except Exception as e:
            logger.error(f"❌ 健康分析服务: 分析失败 - {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def calculate_body_algorithm(
        element_counts: Dict[str, int],
        wangshuai_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算五行与五脏对应关系
        
        肝属木、心属火、脾属土、肺属金、肾属水
        
        Args:
            element_counts: 五行统计 {'木': 2, '火': 1, ...}
            wangshuai_data: 旺衰数据
            
        Returns:
            dict: 五行五脏对应分析
        """
        organ_analysis = {}
        total_elements = sum(element_counts.values()) if element_counts else 1
        
        # 分析每个五脏对应的五行强弱
        for organ, element in HealthAnalysisService.ELEMENT_ORGAN_MAP.items():
            element_count = element_counts.get(element, 0)
            element_proportion = (element_count / total_elements * 100) if total_elements > 0 else 0
            
            # 判断强弱（平均值为 20%，超过 25% 为偏强，低于 15% 为偏弱）
            if element_proportion >= 25:
                strength = '偏强'
                health_status = '相对旺盛'
            elif element_proportion >= 15:
                strength = '平衡'
                health_status = '相对正常'
            else:
                strength = '偏弱'
                health_status = '相对不足'
            
            organ_info = HealthAnalysisService.ORGAN_ELEMENT_DETAIL.get(organ, {})
            
            organ_analysis[organ] = {
                'element': element,
                'count': element_count,
                'proportion': round(element_proportion, 1),
                'strength': strength,
                'health_status': health_status,
                'description': organ_info.get('description', ''),
                'health_functions': organ_info.get('health_functions', [])
            }
        
        return {
            'organ_analysis': organ_analysis,
            'summary': '根据五行分布判断各脏腑的强弱情况'
        }
    
    @staticmethod
    def analyze_pathology_tendency(
        element_counts: Dict[str, int],
        wangshuai_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析病理倾向
        
        基于五行失衡推导健康风险
        
        Args:
            element_counts: 五行统计
            wangshuai_data: 旺衰数据
            
        Returns:
            dict: 病理倾向分析
        """
        total_elements = sum(element_counts.values()) if element_counts else 1
        pathology_list = []
        
        # 分析每个五行的病理倾向
        for element, organ in HealthAnalysisService.ELEMENT_ORGAN_MAP.items():
            element_count = element_counts.get(element, 0)
            element_proportion = (element_count / total_elements * 100) if total_elements > 0 else 0
            
            if element_proportion >= 30:  # 过旺
                pathology_list.append({
                    'organ': organ,
                    'element': element,
                    'tendency': '过旺',
                    'risk': f'{organ}功能亢进，可能导致相关疾病',
                    'suggestions': [f'注意{organ}的调养，避免过度消耗']
                })
            elif element_proportion <= 10:  # 过弱
                pathology_list.append({
                    'organ': organ,
                    'element': element,
                    'tendency': '过弱',
                    'risk': f'{organ}功能不足，易出现相关疾病',
                    'suggestions': [f'重点补益{organ}，增强其功能']
                })
        
        # 五行生克关系的病理影响
        wuxing_relations = HealthAnalysisService._analyze_element_relations(element_counts)
        
        return {
            'pathology_list': pathology_list,
            'wuxing_relations': wuxing_relations,
            'summary': '基于五行失衡分析可能的健康风险'
        }
    
    @staticmethod
    def _analyze_element_relations(element_counts: Dict[str, int]) -> Dict[str, Any]:
        """
        分析五行生克关系对健康的影响
        
        Args:
            element_counts: 五行统计
            
        Returns:
            dict: 五行关系分析
        """
        # 五行生克关系
        element_relations_map = {
            '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
            '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
            '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
            '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
            '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
        }
        
        relations_analysis = []
        
        for element, organ in HealthAnalysisService.ELEMENT_ORGAN_MAP.items():
            element_count = element_counts.get(element, 0)
            if element_count == 0:
                continue
            
            relation_info = element_relations_map.get(element, {})
            controlled_by = relation_info.get('controlled_by', '')
            
            # 如果被克过多，可能导致该脏腑受损
            if controlled_by:
                controlling_count = element_counts.get(controlled_by, 0)
                if controlling_count > element_count * 1.5:  # 克我者过强
                    controlling_organ = HealthAnalysisService.ELEMENT_ORGAN_MAP.get(controlled_by, '')
                    relations_analysis.append({
                        'organ': organ,
                        'element': element,
                        'issue': f'被{controlling_organ}({controlled_by})克制过强',
                        'risk': f'{organ}功能可能受损',
                        'suggestion': f'注意{controlling_organ}与{organ}的平衡'
                    })
        
        return {
            'relations': relations_analysis,
            'summary': '五行生克关系对脏腑健康的影响'
        }
    
    @staticmethod
    def generate_wuxing_tuning(
        xi_ji_data: Dict[str, Any],
        element_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        生成五行调和方案
        
        根据喜忌五行推荐调理方向
        
        Args:
            xi_ji_data: 喜忌数据
            element_counts: 五行统计
            
        Returns:
            dict: 五行调和方案
        """
        xi_shen_elements = xi_ji_data.get('xi_ji_elements', {}).get('xi_shen', [])
        ji_shen_elements = xi_ji_data.get('xi_ji_elements', {}).get('ji_shen', [])
        
        tuning_suggestions = []
        
        # 根据喜神推荐补益方向
        for element in xi_shen_elements:
            organ = HealthAnalysisService.ELEMENT_ORGAN_MAP.get(element, '')
            if organ:
                tuning_suggestions.append({
                    'element': element,
                    'organ': organ,
                    'direction': '补益',
                    'reason': f'{element}为喜用神，补益{organ}有利于整体平衡',
                    'methods': [
                        f'饮食：多食{organ}对应的食物',
                        f'运动：{organ}相关的运动锻炼',
                        f'作息：顺应{organ}的生理节律'
                    ]
                })
        
        # 根据忌神推荐克制方向
        for element in ji_shen_elements:
            organ = HealthAnalysisService.ELEMENT_ORGAN_MAP.get(element, '')
            if organ:
                tuning_suggestions.append({
                    'element': element,
                    'organ': organ,
                    'direction': '克制',
                    'reason': f'{element}为忌神，{organ}过强需克制',
                    'methods': [
                        f'避免过度刺激{organ}',
                        f'注意{organ}的调养节制',
                        f'通过相克五行平衡{organ}'
                    ]
                })
        
        return {
            'tuning_suggestions': tuning_suggestions,
            'summary': '基于喜忌五行的调理建议'
        }
    
    @staticmethod
    def generate_zangfu_care(
        body_algorithm: Dict[str, Any],
        xi_ji_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成脏腑养护建议
        
        基于五脏强弱给出养护建议
        
        Args:
            body_algorithm: 五行五脏对应分析结果
            xi_ji_data: 喜忌数据
            
        Returns:
            dict: 脏腑养护建议
        """
        organ_analysis = body_algorithm.get('organ_analysis', {})
        care_suggestions = []
        
        # 根据每个脏腑的强弱给出养护建议
        for organ, analysis in organ_analysis.items():
            strength = analysis.get('strength', '')
            element = analysis.get('element', '')
            health_status = analysis.get('health_status', '')
            
            if strength == '偏弱':
                care_suggestions.append({
                    'organ': organ,
                    'element': element,
                    'priority': '高',
                    'care_focus': '补益',
                    'suggestions': [
                        f'{organ}功能相对不足，需要重点补益',
                        f'通过补{element}来增强{organ}的功能',
                        f'饮食：选择{organ}对应的补益食物',
                        f'运动：适度{organ}相关的运动',
                        f'作息：保证充足睡眠，顺应{organ}的生理节律'
                    ]
                })
            elif strength == '偏强':
                care_suggestions.append({
                    'organ': organ,
                    'element': element,
                    'priority': '中',
                    'care_focus': '平衡',
                    'suggestions': [
                        f'{organ}功能相对旺盛，注意平衡',
                        f'避免过度刺激{organ}',
                        f'通过相克五行平衡{organ}的功能',
                        f'保持{organ}的正常生理功能，避免功能亢进'
                    ]
                })
            else:
                care_suggestions.append({
                    'organ': organ,
                    'element': element,
                    'priority': '低',
                    'care_focus': '维护',
                    'suggestions': [
                        f'{organ}功能相对正常，保持现状',
                        f'维持{organ}的健康状态',
                        f'注意{organ}的日常养护'
                    ]
                })
        
        return {
            'care_suggestions': care_suggestions,
            'summary': '基于脏腑强弱的养护建议'
        }
    
    @staticmethod
    def analyze_wuxing_balance(element_counts: Dict[str, int]) -> str:
        """
        分析五行平衡情况
        
        Args:
            element_counts: 五行统计
            
        Returns:
            str: 平衡情况描述
        """
        total_elements = sum(element_counts.values()) if element_counts else 1
        proportions = {}
        
        for element in ['木', '火', '土', '金', '水']:
            count = element_counts.get(element, 0)
            proportions[element] = (count / total_elements * 100) if total_elements > 0 else 0
        
        # 判断平衡性
        max_prop = max(proportions.values())
        min_prop = min(proportions.values())
        diff = max_prop - min_prop
        
        if diff <= 10:
            return '五行相对平衡'
        elif diff <= 20:
            return '五行略有偏差'
        elif diff <= 30:
            return '五行明显失衡'
        else:
            return '五行严重失衡'

