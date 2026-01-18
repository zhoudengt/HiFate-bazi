#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键时间节点预测分析器
预测未来重要的运势转折点，识别有利/不利的时间段
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from core.data.constants import STEM_ELEMENTS
from core.data.relations import BRANCH_CHONG, BRANCH_LIUHE, STEM_HE

logger = logging.getLogger(__name__)

# 五行生克关系（用于预测分析）
ELEMENT_RELATIONS = {
    '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
    '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
    '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
    '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
    '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
}


class KeyTimePredictionAnalyzer:
    """关键时间节点预测分析器"""
    
    def __init__(self):
        """初始化分析器"""
        logger.info("✅ 关键时间节点预测分析器初始化完成")
    
    def predict_key_times(
        self,
        bazi_data: Dict[str, Any],
        dayun_sequence: List[Dict[str, Any]],
        liunian_sequence: List[Dict[str, Any]],
        years_ahead: int = 10
    ) -> Dict[str, Any]:
        """
        预测关键时间节点
        
        Args:
            bazi_data: 八字数据
            dayun_sequence: 大运序列
            liunian_sequence: 流年序列
            years_ahead: 预测未来多少年，默认10年
            
        Returns:
            关键时间节点预测结果
        """
        logger.info(f"🔍 开始预测未来{years_ahead}年的关键时间节点")
        
        day_stem = bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', '')
        day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '')
        
        key_times = []
        
        # 1. 预测大运转折点
        dayun_turning_points = self._predict_dayun_turning_points(
            dayun_sequence, years_ahead
        )
        key_times.extend(dayun_turning_points)
        
        # 2. 预测有利流年
        favorable_years = self._predict_favorable_years(
            day_stem, day_branch, liunian_sequence, years_ahead
        )
        key_times.extend(favorable_years)
        
        # 3. 预测不利流年
        unfavorable_years = self._predict_unfavorable_years(
            day_stem, day_branch, liunian_sequence, years_ahead
        )
        key_times.extend(unfavorable_years)
        
        # 4. 预测特殊组合年份
        special_years = self._predict_special_years(
            bazi_data, liunian_sequence, years_ahead
        )
        key_times.extend(special_years)
        
        # 按时间排序
        key_times.sort(key=lambda x: x.get('year', 0))
        
        # 生成预测摘要
        summary = self._generate_prediction_summary(key_times, years_ahead)
        
        result = {
            'prediction_period': years_ahead,
            'key_times': key_times,
            'summary': summary,
            'recommendations': self._generate_recommendations(key_times)
        }
        
        logger.info(f"✅ 预测完成，识别到 {len(key_times)} 个关键时间节点")
        return result
    
    def _predict_dayun_turning_points(
        self,
        dayun_sequence: List[Dict[str, Any]],
        years_ahead: int
    ) -> List[Dict[str, Any]]:
        """预测大运转折点"""
        turning_points = []
        current_year = datetime.now().year
        
        for dayun in dayun_sequence:
            start_year = dayun.get('start_year')
            end_year = dayun.get('end_year')
            
            if not start_year:
                continue
            
            # 只预测未来年份
            if start_year > current_year and start_year <= current_year + years_ahead:
                turning_points.append({
                    'year': start_year,
                    'type': 'dayun_turning',
                    'category': '转折点',
                    'description': f'进入新大运：{dayun.get("stem", "")}{dayun.get("branch", "")}',
                    'importance': 'high',
                    'suggestion': '大运转换，运势将发生重要变化，需要特别关注'
                })
        
        return turning_points
    
    def _predict_favorable_years(
        self,
        day_stem: str,
        day_branch: str,
        liunian_sequence: List[Dict[str, Any]],
        years_ahead: int
    ) -> List[Dict[str, Any]]:
        """预测有利流年"""
        favorable_years = []
        current_year = datetime.now().year
        
        for liunian in liunian_sequence:
            year = liunian.get('year')
            if not year or year <= current_year or year > current_year + years_ahead:
                continue
            
            liunian_stem = liunian.get('stem', '')
            liunian_branch = liunian.get('branch', '')
            
            if not liunian_stem or not liunian_branch:
                continue
            
            # 检查是否有利
            is_favorable = False
            reason = []
            
            # 天干五合
            if STEM_HE.get(day_stem) == liunian_stem:
                is_favorable = True
                reason.append('天干五合')
            
            # 地支六合
            if BRANCH_LIUHE.get(day_branch) == liunian_branch:
                is_favorable = True
                reason.append('地支六合')
            
            # 流年天干生日干
            day_element = STEM_ELEMENTS.get(day_stem, '')
            liunian_element = STEM_ELEMENTS.get(liunian_stem, '')
            if day_element and liunian_element:
                relations = ELEMENT_RELATIONS.get(day_element, {})
                if relations.get('produced_by') == liunian_element:
                    is_favorable = True
                    reason.append('流年生我')
            
            if is_favorable:
                favorable_years.append({
                    'year': year,
                    'type': 'favorable_year',
                    'category': '有利年份',
                    'description': f'{year}年（{liunian_stem}{liunian_branch}）',
                    'reasons': reason,
                    'importance': 'medium',
                    'suggestion': f'此年运势较好，适合把握机会。原因：{", ".join(reason)}'
                })
        
        return favorable_years
    
    def _predict_unfavorable_years(
        self,
        day_stem: str,
        day_branch: str,
        liunian_sequence: List[Dict[str, Any]],
        years_ahead: int
    ) -> List[Dict[str, Any]]:
        """预测不利流年"""
        unfavorable_years = []
        current_year = datetime.now().year
        
        for liunian in liunian_sequence:
            year = liunian.get('year')
            if not year or year <= current_year or year > current_year + years_ahead:
                continue
            
            liunian_stem = liunian.get('stem', '')
            liunian_branch = liunian.get('branch', '')
            
            if not liunian_stem or not liunian_branch:
                continue
            
            # 检查是否不利
            is_unfavorable = False
            reason = []
            
            # 地支六冲
            if BRANCH_CHONG.get(day_branch) == liunian_branch:
                is_unfavorable = True
                reason.append('地支六冲')
            
            # 流年天干克日干
            day_element = STEM_ELEMENTS.get(day_stem, '')
            liunian_element = STEM_ELEMENTS.get(liunian_stem, '')
            if day_element and liunian_element:
                relations = ELEMENT_RELATIONS.get(day_element, {})
                if relations.get('controlled_by') == liunian_element:
                    is_unfavorable = True
                    reason.append('流年克我')
            
            # 伏吟（相同）
            if day_stem == liunian_stem and day_branch == liunian_branch:
                is_unfavorable = True
                reason.append('流年伏吟')
            
            if is_unfavorable:
                unfavorable_years.append({
                    'year': year,
                    'type': 'unfavorable_year',
                    'category': '不利年份',
                    'description': f'{year}年（{liunian_stem}{liunian_branch}）',
                    'reasons': reason,
                    'importance': 'medium',
                    'suggestion': f'此年需要谨慎，避免重大决策。原因：{", ".join(reason)}'
                })
        
        return unfavorable_years
    
    def _predict_special_years(
        self,
        bazi_data: Dict[str, Any],
        liunian_sequence: List[Dict[str, Any]],
        years_ahead: int
    ) -> List[Dict[str, Any]]:
        """预测特殊组合年份"""
        special_years = []
        current_year = datetime.now().year
        
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        
        for liunian in liunian_sequence:
            year = liunian.get('year')
            if not year or year <= current_year or year > current_year + years_ahead:
                continue
            
            liunian_stem = liunian.get('stem', '')
            liunian_branch = liunian.get('branch', '')
            
            if not liunian_stem or not liunian_branch:
                continue
            
            # 检查是否与四柱形成特殊组合
            special_combinations = []
            
            for pillar_type in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(pillar_type, {})
                pillar_stem = pillar.get('stem', '')
                pillar_branch = pillar.get('branch', '')
                
                # 检查三合、三会等特殊组合
                # 这里简化处理，实际可以更详细
                if pillar_stem == liunian_stem and pillar_branch == liunian_branch:
                    special_combinations.append(f'{pillar_type}柱伏吟')
            
            if special_combinations:
                special_years.append({
                    'year': year,
                    'type': 'special_year',
                    'category': '特殊年份',
                    'description': f'{year}年（{liunian_stem}{liunian_branch}）',
                    'special_features': special_combinations,
                    'importance': 'high',
                    'suggestion': f'此年有特殊组合：{", ".join(special_combinations)}，需要特别关注'
                })
        
        return special_years
    
    def _generate_prediction_summary(
        self,
        key_times: List[Dict[str, Any]],
        years_ahead: int
    ) -> Dict[str, Any]:
        """生成预测摘要"""
        turning_points = [t for t in key_times if t.get('type') == 'dayun_turning']
        favorable = [t for t in key_times if t.get('type') == 'favorable_year']
        unfavorable = [t for t in key_times if t.get('type') == 'unfavorable_year']
        special = [t for t in key_times if t.get('type') == 'special_year']
        
        return {
            'total_key_times': len(key_times),
            'turning_points_count': len(turning_points),
            'favorable_years_count': len(favorable),
            'unfavorable_years_count': len(unfavorable),
            'special_years_count': len(special),
            'prediction_period': years_ahead
        }
    
    def _generate_recommendations(
        self,
        key_times: List[Dict[str, Any]]
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 找出最重要的时间节点
        high_importance = [t for t in key_times if t.get('importance') == 'high']
        
        if high_importance:
            recommendations.append(
                f"未来有 {len(high_importance)} 个重要转折点，建议提前做好准备"
            )
        
        # 有利年份建议
        favorable = [t for t in key_times if t.get('type') == 'favorable_year']
        if favorable:
            years = [str(t.get('year')) for t in favorable[:3]]  # 前3个
            recommendations.append(
                f"建议在以下年份把握机会：{', '.join(years)}"
            )
        
        # 不利年份建议
        unfavorable = [t for t in key_times if t.get('type') == 'unfavorable_year']
        if unfavorable:
            years = [str(t.get('year')) for t in unfavorable[:3]]  # 前3个
            recommendations.append(
                f"以下年份需要谨慎：{', '.join(years)}"
            )
        
        return recommendations

