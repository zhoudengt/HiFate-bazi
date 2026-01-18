#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调候与喜忌神综合分析器

核心理论：
1. 旺衰喜忌是基础（生扶还是克泄）
2. 调候是修正（气候平衡）
3. 当调候五行与旺衰喜忌一致时，该五行为「第一喜神」
4. 当调候五行与旺衰喜忌冲突时，需要权衡取舍

传统命理原则：
- 夏月炎热，喜水来调候（降温）
- 冬月寒冷，喜火来调候（取暖）
- 春秋气候适中，无需特别调候
- 调候得当者，命局层次提高
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class TiaohouXijiAnalyzer:
    """调候与喜忌神综合分析器"""
    
    @staticmethod
    def determine_final_xi_ji(
        wangshuai_result: Dict[str, Any],
        tiaohou_result: Dict[str, Any],
        bazi_elements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        综合旺衰喜忌和调候需求，确定最终喜忌神
        
        Args:
            wangshuai_result: 旺衰分析结果，包含 xi_ji, xi_ji_elements
            tiaohou_result: 调候分析结果，包含 tiaohou_element, season
            bazi_elements: 八字五行信息，包含 element_counts 等
        
        Returns:
            {
                'final_xi_shen': [...],  # 最终喜神列表（优先级排序）
                'final_ji_shen': [...],  # 最终忌神列表
                'first_xi_shen': [...],  # 第一喜神（调候喜忌一致）
                'xi_shen_elements': [...],  # 喜神对应的五行
                'ji_shen_elements': [...],  # 忌神对应的五行
                'tiaohou_priority': 'high' | 'medium' | 'low',  # 调候优先级
                'analysis': str,  # 综合分析说明
                'recommendations': [...]  # 建议
            }
        """
        # 获取基础数据
        wangshuai = wangshuai_result.get('wangshuai', '平衡')
        xi_ji = wangshuai_result.get('xi_ji', {})
        xi_ji_elements = wangshuai_result.get('xi_ji_elements', {})
        
        base_xi_shen = xi_ji.get('xi_shen', [])
        base_ji_shen = xi_ji.get('ji_shen', [])
        base_xi_elements = xi_ji_elements.get('xi_shen', [])
        base_ji_elements = xi_ji_elements.get('ji_shen', [])
        
        tiaohou_element = tiaohou_result.get('tiaohou_element')
        season = tiaohou_result.get('season', '春秋')
        
        element_counts = bazi_elements.get('element_counts', {})
        
        logger.info(f"🌡️ 开始综合判断 - 旺衰:{wangshuai}, 季节:{season}, 调候五行:{tiaohou_element}")
        
        # 判断调候优先级
        tiaohou_priority = TiaohouXijiAnalyzer._calculate_tiaohou_priority(
            tiaohou_element, element_counts, season
        )
        
        # 如果不需要调候（春秋季节），直接返回旺衰喜忌
        if not tiaohou_element:
            return {
                'final_xi_shen': base_xi_shen,
                'final_ji_shen': base_ji_shen,
                'first_xi_shen': [],
                'xi_shen_elements': base_xi_elements,
                'ji_shen_elements': base_ji_elements,
                'tiaohou_priority': 'none',
                'analysis': f"{season}季节，气候适中，无需特别调候。主要依据旺衰判断喜忌。",
                'recommendations': [
                    f"喜用五行：{', '.join(base_xi_elements)}",
                    f"忌讳五行：{', '.join(base_ji_elements)}"
                ]
            }
        
        # 综合判断调候与喜忌的关系
        result = TiaohouXijiAnalyzer._integrate_tiaohou_xiji(
            base_xi_shen, base_ji_shen,
            base_xi_elements, base_ji_elements,
            tiaohou_element, tiaohou_priority,
            wangshuai, season, element_counts
        )
        
        logger.info(f"✅ 综合判断完成 - 第一喜神: {result['first_xi_shen']}, "
                   f"调候优先级: {result['tiaohou_priority']}")
        
        return result
    
    @staticmethod
    def _calculate_tiaohou_priority(
        tiaohou_element: Optional[str],
        element_counts: Dict[str, int],
        season: str
    ) -> str:
        """
        计算调候的优先级
        
        原则：
        - 命局缺少调候五行 → 高优先级（急需）
        - 命局有少量调候五行 → 中优先级（需要）
        - 命局有充足调候五行 → 低优先级（已满足）
        
        Returns:
            'high' | 'medium' | 'low' | 'none'
        """
        if not tiaohou_element:
            return 'none'
        
        count = element_counts.get(tiaohou_element, 0)
        
        if count == 0:
            priority = 'high'
            reason = f"命局缺少{tiaohou_element}，{season}急需调候"
        elif count == 1:
            priority = 'medium'
            reason = f"命局{tiaohou_element}较弱，{season}需要加强"
        else:
            priority = 'low'
            reason = f"命局{tiaohou_element}充足，{season}调候已满足"
        
        logger.info(f"   调候优先级: {priority} - {reason}")
        return priority
    
    @staticmethod
    def _integrate_tiaohou_xiji(
        base_xi_shen: List[str],
        base_ji_shen: List[str],
        base_xi_elements: List[str],
        base_ji_elements: List[str],
        tiaohou_element: str,
        tiaohou_priority: str,
        wangshuai: str,
        season: str,
        element_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        整合调候与喜忌神的关系
        
        核心逻辑：
        1. 调候五行在喜神五行中 → 「第一喜神」（最重要）
        2. 调候五行在忌神五行中 → 根据优先级权衡
           - 高优先级：调候优先，适当调整忌神
           - 中/低优先级：保持原有喜忌
        3. 调候五行不在喜忌中 → 作为补充喜神
        """
        # 检查调候五行在喜神还是忌神中
        tiaohou_in_xi = tiaohou_element in base_xi_elements
        tiaohou_in_ji = tiaohou_element in base_ji_elements
        
        # 获取调候五行对应的十神
        tiaohou_shishen = TiaohouXijiAnalyzer._get_shishen_by_element(
            tiaohou_element, base_xi_shen, base_xi_elements, base_ji_shen, base_ji_elements
        )
        
        # 情况1：调候五行在喜神中 → 最佳情况
        if tiaohou_in_xi:
            first_xi_shen = tiaohou_shishen if tiaohou_shishen else []
            
            # 将调候五行对应的十神提到最前面
            final_xi_shen = list(base_xi_shen)
            for god in first_xi_shen:
                if god in final_xi_shen:
                    final_xi_shen.remove(god)
                    final_xi_shen.insert(0, god)
            
            # 将调候五行提到最前面
            final_xi_elements = list(base_xi_elements)
            if tiaohou_element in final_xi_elements:
                final_xi_elements.remove(tiaohou_element)
                final_xi_elements.insert(0, tiaohou_element)
            
            analysis = (
                f"{season}生，需要{tiaohou_element}调候。"
                f"命局{wangshuai}，喜用{tiaohou_element}。"
                f"调候喜忌一致，{tiaohou_element}为第一喜神。"
            )
            
            recommendations = [
                f"第一喜神：{tiaohou_element}（{', '.join(first_xi_shen)}）- 既调候又助身",
                f"其他喜神：{', '.join([e for e in final_xi_elements if e != tiaohou_element])}",
                f"忌讳五行：{', '.join(base_ji_elements)}"
            ]
            
            return {
                'final_xi_shen': final_xi_shen,
                'final_ji_shen': base_ji_shen,
                'first_xi_shen': first_xi_shen,
                'xi_shen_elements': final_xi_elements,
                'ji_shen_elements': base_ji_elements,
                'tiaohou_priority': tiaohou_priority,
                'analysis': analysis,
                'recommendations': recommendations
            }
        
        # 情况2：调候五行在忌神中 → 需要权衡
        elif tiaohou_in_ji:
            if tiaohou_priority == 'high':
                # 高优先级：调候极其重要，需要调整忌神
                first_xi_shen = tiaohou_shishen if tiaohou_shishen else []
                
                # 从忌神中移除调候五行对应的十神
                final_ji_shen = [g for g in base_ji_shen if g not in first_xi_shen]
                final_ji_elements = [e for e in base_ji_elements if e != tiaohou_element]
                
                # 将调候五行加入喜神
                final_xi_shen = first_xi_shen + list(base_xi_shen)
                final_xi_elements = [tiaohou_element] + list(base_xi_elements)
                
                analysis = (
                    f"{season}生，急需{tiaohou_element}调候（命局缺少）。"
                    f"虽然{wangshuai}忌{tiaohou_element}，但调候优先。"
                    f"适当使用{tiaohou_element}以平衡气候。"
                )
                
                recommendations = [
                    f"第一要务：补充{tiaohou_element}（{', '.join(first_xi_shen)}）用于调候",
                    f"注意：{tiaohou_element}适量即可，不宜过多",
                    f"其他喜神：{', '.join(base_xi_elements)}",
                    f"主要忌神：{', '.join(final_ji_elements)}"
                ]
            else:
                # 中/低优先级：保持原有喜忌
                first_xi_shen = []
                final_xi_shen = list(base_xi_shen)
                final_ji_shen = list(base_ji_shen)
                final_xi_elements = list(base_xi_elements)
                final_ji_elements = list(base_ji_elements)
                
                analysis = (
                    f"{season}生，需要{tiaohou_element}调候。"
                    f"但命局{wangshuai}忌{tiaohou_element}，且命局已有{element_counts.get(tiaohou_element, 0)}个。"
                    f"调候需求不急迫，主要依据旺衰判断喜忌。"
                )
                
                recommendations = [
                    f"喜用五行：{', '.join(final_xi_elements)}",
                    f"忌讳五行：{', '.join(final_ji_elements)}",
                    f"调候建议：命局{tiaohou_element}已足够，无需额外补充"
                ]
            
            return {
                'final_xi_shen': final_xi_shen,
                'final_ji_shen': final_ji_shen,
                'first_xi_shen': first_xi_shen,
                'xi_shen_elements': final_xi_elements,
                'ji_shen_elements': final_ji_elements,
                'tiaohou_priority': tiaohou_priority,
                'analysis': analysis,
                'recommendations': recommendations
            }
        
        # 情况3：调候五行不在喜忌中（中性） → 作为补充
        else:
            first_xi_shen = []
            
            if tiaohou_priority == 'high':
                # 调候五行作为补充喜神
                final_xi_shen = list(base_xi_shen)
                final_xi_elements = [tiaohou_element] + list(base_xi_elements)
                
                analysis = (
                    f"{season}生，急需{tiaohou_element}调候（命局缺少）。"
                    f"{tiaohou_element}对{wangshuai}命局影响中性。"
                    f"建议适当补充{tiaohou_element}以调节气候。"
                )
                
                recommendations = [
                    f"调候建议：适当补充{tiaohou_element}以平衡气候",
                    f"喜用五行：{', '.join(base_xi_elements)}",
                    f"忌讳五行：{', '.join(base_ji_elements)}"
                ]
            else:
                # 保持原有喜忌
                final_xi_shen = list(base_xi_shen)
                final_xi_elements = list(base_xi_elements)
                
                analysis = (
                    f"{season}生，{tiaohou_element}有调候作用。"
                    f"命局{wangshuai}，{tiaohou_element}影响中性。"
                    f"主要依据旺衰判断喜忌。"
                )
                
                recommendations = [
                    f"喜用五行：{', '.join(final_xi_elements)}",
                    f"忌讳五行：{', '.join(base_ji_elements)}",
                    f"调候：{tiaohou_element}可适当使用"
                ]
            
            return {
                'final_xi_shen': final_xi_shen,
                'final_ji_shen': base_ji_shen,
                'first_xi_shen': first_xi_shen,
                'xi_shen_elements': final_xi_elements,
                'ji_shen_elements': base_ji_elements,
                'tiaohou_priority': tiaohou_priority,
                'analysis': analysis,
                'recommendations': recommendations
            }
    
    @staticmethod
    def _get_shishen_by_element(
        element: str,
        xi_shen: List[str],
        xi_elements: List[str],
        ji_shen: List[str],
        ji_elements: List[str]
    ) -> List[str]:
        """
        根据五行反查对应的十神
        
        注意：一个五行可能对应多个十神
        例如：水可能对应偏印、正印
        """
        # 从喜神中查找
        result = []
        for i, e in enumerate(xi_elements):
            if e == element and i < len(xi_shen):
                god = xi_shen[i]
                if god not in result:
                    result.append(god)
        
        # 如果喜神中没有，从忌神中查找
        if not result:
            for i, e in enumerate(ji_elements):
                if e == element and i < len(ji_shen):
                    god = ji_shen[i]
                    if god not in result:
                        result.append(god)
        
        return result

