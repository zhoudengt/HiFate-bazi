#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流年大运增强分析服务
整合流年吉凶评分、大运转折点、互动分析、关键时间预测等功能
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LiunianEnhancedService:
    """流年大运增强分析服务"""
    
    @staticmethod
    def analyze_liunian_enhanced(
        solar_date: str,
        solar_time: str,
        gender: str,
        target_year: Optional[int] = None,
        years_ahead: int = 10
    ) -> Dict[str, Any]:
        """
        综合流年大运增强分析
        
        Args:
            solar_date: 出生日期
            solar_time: 出生时间
            gender: 性别
            target_year: 目标年份（可选，用于分析特定年份）
            years_ahead: 预测未来多少年，默认10年
            
        Returns:
            综合分析结果
        """
        logger.info(f"🔍 开始流年大运增强分析 - 日期: {solar_date}, 时间: {solar_time}, 性别: {gender}")
        
        try:
            # 1. 计算基础八字数据
            from src.tool.BaziCalculator import BaziCalculator
            calculator = BaziCalculator(solar_date, solar_time, gender)
            bazi_data = calculator.build_rule_input()
            
            # 2. 计算大运流年数据（使用本地计算器）
            from src.bazi_fortune.bazi_calculator_docs import BaziCalculator as FortuneCalculator
            fortune_calc = FortuneCalculator(solar_date, solar_time, gender)
            detail_result = fortune_calc.calculate_dayun_liunian()
            details = detail_result.get('details', {})
            
            dayun_sequence = details.get('dayun_sequence', [])
            liunian_sequence = details.get('liunian_sequence', [])
            current_liunian = details.get('liunian', {})
            
            result = {
                'success': True,
                'bazi_info': {
                    'solar_date': solar_date,
                    'solar_time': solar_time,
                    'gender': gender
                }
            }
            
            # 3. 流年吉凶量化评分（如果指定了目标年份，分析该年份；否则分析当前流年）
            if target_year:
                # 找到目标年份的流年数据
                target_liunian = None
                for liunian in liunian_sequence:
                    if liunian.get('year') == target_year:
                        target_liunian = liunian
                        break
                
                if target_liunian:
                    from src.analyzers.liunian_auspicious_analyzer import LiunianAuspiciousAnalyzer
                    analyzer = LiunianAuspiciousAnalyzer()
                    
                    # 找到对应的大运
                    target_dayun = None
                    for dayun in dayun_sequence:
                        start_year = dayun.get('start_year')
                        end_year = dayun.get('end_year')
                        if start_year and end_year and start_year <= target_year <= end_year:
                            target_dayun = dayun
                            break
                    
                    auspicious_result = analyzer.calculate_auspicious_score(
                        bazi_data, target_liunian, target_dayun
                    )
                    result['target_year_analysis'] = {
                        'year': target_year,
                        'auspicious_score': auspicious_result
                    }
            else:
                # 分析当前流年
                if current_liunian:
                    from src.analyzers.liunian_auspicious_analyzer import LiunianAuspiciousAnalyzer
                    analyzer = LiunianAuspiciousAnalyzer()
                    
                    # 找到当前大运
                    current_year = datetime.now().year
                    current_dayun = None
                    for dayun in dayun_sequence:
                        start_year = dayun.get('start_year')
                        end_year = dayun.get('end_year')
                        if start_year and end_year and start_year <= current_year <= end_year:
                            current_dayun = dayun
                            break
                    
                    auspicious_result = analyzer.calculate_auspicious_score(
                        bazi_data, current_liunian, current_dayun
                    )
                    result['current_liunian_analysis'] = auspicious_result
            
            # 4. 大运转折点识别
            from src.analyzers.dayun_turning_point_analyzer import DayunTurningPointAnalyzer
            turning_point_analyzer = DayunTurningPointAnalyzer()
            turning_points = turning_point_analyzer.identify_turning_points(
                bazi_data, dayun_sequence
            )
            result['turning_points'] = turning_points
            
            # 5. 流年与命局互动分析（分析当前流年或目标年份）
            if target_year:
                target_liunian = None
                for liunian in liunian_sequence:
                    if liunian.get('year') == target_year:
                        target_liunian = liunian
                        break
                
                if target_liunian:
                    from src.analyzers.liunian_interaction_analyzer import LiunianInteractionAnalyzer
                    interaction_analyzer = LiunianInteractionAnalyzer()
                    interaction_result = interaction_analyzer.analyze_interaction(
                        bazi_data, target_liunian
                    )
                    result['target_year_interaction'] = interaction_result
            else:
                if current_liunian:
                    from src.analyzers.liunian_interaction_analyzer import LiunianInteractionAnalyzer
                    interaction_analyzer = LiunianInteractionAnalyzer()
                    interaction_result = interaction_analyzer.analyze_interaction(
                        bazi_data, current_liunian
                    )
                    result['current_liunian_interaction'] = interaction_result
            
            # 6. 关键时间节点预测
            from src.analyzers.key_time_prediction_analyzer import KeyTimePredictionAnalyzer
            prediction_analyzer = KeyTimePredictionAnalyzer()
            key_times = prediction_analyzer.predict_key_times(
                bazi_data, dayun_sequence, liunian_sequence, years_ahead
            )
            result['key_time_predictions'] = key_times
            
            # 7. 生成综合分析摘要
            result['summary'] = LiunianEnhancedService._generate_comprehensive_summary(
                result, turning_points, key_times
            )
            
            logger.info("✅ 流年大运增强分析完成")
            return result
            
        except Exception as e:
            logger.error(f"流年大运增强分析失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _generate_comprehensive_summary(
        result: Dict[str, Any],
        turning_points: List[Dict[str, Any]],
        key_times: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成综合分析摘要"""
        summary = {
            'turning_points_count': len(turning_points),
            'key_times_count': key_times.get('key_times', []).__len__(),
            'favorable_years': [],
            'unfavorable_years': [],
            'important_times': []
        }
        
        # 提取有利和不利年份
        key_times_list = key_times.get('key_times', [])
        for time_point in key_times_list:
            if time_point.get('type') == 'favorable_year':
                summary['favorable_years'].append(time_point.get('year'))
            elif time_point.get('type') == 'unfavorable_year':
                summary['unfavorable_years'].append(time_point.get('year'))
            elif time_point.get('importance') == 'high':
                summary['important_times'].append({
                    'year': time_point.get('year'),
                    'type': time_point.get('type'),
                    'description': time_point.get('description')
                })
        
        return summary

