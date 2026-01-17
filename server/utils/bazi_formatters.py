#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字结果格式化工具类
统一管理八字结果的格式化逻辑，避免在多个位置重复实现
"""

from datetime import datetime
from typing import Any, Dict, Optional


class BaziResultFormatter:
    """八字结果格式化工具类"""
    
    @staticmethod
    def format_current_time(current_time: Any) -> str:
        """
        格式化当前时间
        
        Args:
            current_time: 当前时间（datetime 对象或字符串）
        
        Returns:
            str: 格式化后的时间字符串
        """
        if isinstance(current_time, datetime):
            return current_time.strftime('%Y-%m-%d %H:%M:%S')
        elif current_time:
            return str(current_time)
        else:
            return ''
    
    @staticmethod
    def format_basic_info(basic_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化基本信息
        
        Args:
            basic_info: 基本信息字典
        
        Returns:
            Dict[str, Any]: 格式化后的基本信息
        """
        current_time = basic_info.get('current_time')
        current_time_str = BaziResultFormatter.format_current_time(current_time)
        
        return {
            "solar_date": basic_info.get('solar_date', ''),
            "solar_time": basic_info.get('solar_time', ''),
            "lunar_date": basic_info.get('lunar_date', {}),
            "gender": basic_info.get('gender', ''),
            "current_time": current_time_str,
            "adjusted_solar_date": basic_info.get('adjusted_solar_date', ''),
            "adjusted_solar_time": basic_info.get('adjusted_solar_time', ''),
            "is_zi_shi_adjusted": basic_info.get('is_zi_shi_adjusted', False),
        }
    
    @staticmethod
    def format_pillars(bazi_pillars: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化四柱信息
        
        Args:
            bazi_pillars: 四柱字典
            details: 详情字典
        
        Returns:
            Dict[str, Any]: 格式化后的四柱信息
        """
        formatted_pillars = {}
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_details = details.get(pillar_type, {})
            formatted_pillars[pillar_type] = {
                "stem": bazi_pillars.get(pillar_type, {}).get('stem', ''),
                "branch": bazi_pillars.get(pillar_type, {}).get('branch', ''),
                "main_star": pillar_details.get('main_star', ''),
                "hidden_stars": pillar_details.get('hidden_stars', []),
                "sub_stars": pillar_details.get('sub_stars', pillar_details.get('hidden_stars', [])),
                "hidden_stems": pillar_details.get('hidden_stems', []),
                "star_fortune": pillar_details.get('star_fortune', ''),
                "self_sitting": pillar_details.get('self_sitting', ''),
                "kongwang": pillar_details.get('kongwang', ''),
                "nayin": pillar_details.get('nayin', ''),
                "deities": pillar_details.get('deities', []),
            }
        return formatted_pillars
    
    @staticmethod
    def format_basic_result(
        solar_date: str,
        solar_time: str,
        adjusted_solar_date: str,
        adjusted_solar_time: str,
        lunar_date: Dict[str, Any],
        gender: str,
        is_zi_shi_adjusted: bool,
        bazi_pillars: Dict[str, Any],
        details: Dict[str, Any],
        ten_gods_stats: Dict[str, Any],
        elements: Dict[str, Any],
        element_counts: Dict[str, Any],
        relationships: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        格式化基础八字结果（统一实现 _format_result 的逻辑）
        
        Args:
            solar_date: 阳历日期
            solar_time: 阳历时间
            adjusted_solar_date: 调整后的阳历日期
            adjusted_solar_time: 调整后的阳历时间
            lunar_date: 农历日期
            gender: 性别
            is_zi_shi_adjusted: 是否子时调整
            bazi_pillars: 四柱信息
            details: 详情信息
            ten_gods_stats: 十神统计
            elements: 五行信息
            element_counts: 五行计数
            relationships: 关系信息
        
        Returns:
            Dict[str, Any]: 格式化后的结果
        """
        return {
            'basic_info': {
                'solar_date': solar_date,
                'solar_time': solar_time,
                'adjusted_solar_date': adjusted_solar_date,
                'adjusted_solar_time': adjusted_solar_time,
                'lunar_date': lunar_date,
                'gender': gender,
                'is_zi_shi_adjusted': is_zi_shi_adjusted,
            },
            'bazi_pillars': bazi_pillars,
            'details': details,
            'ten_gods_stats': ten_gods_stats,
            'elements': elements,
            'element_counts': element_counts,
            'relationships': relationships,
        }
    
    @staticmethod
    def format_detail_result(detail_result: Dict[str, Any], bazi_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化详细八字结果（统一实现 format_detail_result 的逻辑）
        
        Args:
            detail_result: BaziCalculator.get_dayun_liunian_result() 返回的结果
            bazi_result: BaziCalculator.calculate() 返回的结果
        
        Returns:
            Dict[str, Any]: 格式化后的详细八字数据
        """
        basic_info = detail_result.get('basic_info', {})
        bazi_pillars = detail_result.get('bazi_pillars', {})
        details = detail_result.get('details', {})
        
        # 格式化基本信息
        formatted_basic_info = BaziResultFormatter.format_basic_info(basic_info)
        
        # 格式化四柱信息
        formatted_pillars = BaziResultFormatter.format_pillars(bazi_pillars, details)
        
        # 格式化大运流年信息
        dayun_info = details.get('dayun', {})
        liunian_info = details.get('liunian', {})
        qiyun_info = details.get('qiyun', {})
        jiaoyun_info = details.get('jiaoyun', {})
        
        def _format_sequence(seq_key: str) -> list:
            return details.get(seq_key, [])
        
        return {
            "basic_info": formatted_basic_info,
            "bazi_pillars": formatted_pillars,
            "details": details,
            "ten_gods_stats": bazi_result.get('ten_gods_stats', {}),
            "elements": bazi_result.get('elements', {}),
            "element_counts": bazi_result.get('element_counts', {}),
            "relationships": bazi_result.get('relationships', {}),
            "dayun_info": {
                "current_dayun": dayun_info,
                "next_dayun": {},
                "qiyun_date": qiyun_info.get('date', ''),
                "qiyun_age": qiyun_info.get('age_display', ''),
                "qiyun": qiyun_info,
                "jiaoyun_date": jiaoyun_info.get('date', ''),
                "jiaoyun_age": jiaoyun_info.get('age_display', ''),
                "jiaoyun": jiaoyun_info,
            },
            "liunian_info": {
                "current_liunian": liunian_info,
                "next_liunian": {},
            },
            "dayun_sequence": _format_sequence('dayun_sequence'),
            "liunian_sequence": _format_sequence('liunian_sequence'),
            "liuyue_sequence": _format_sequence('liuyue_sequence'),
            "liuri_sequence": _format_sequence('liuri_sequence'),
            "liushi_sequence": _format_sequence('liushi_sequence'),
        }
