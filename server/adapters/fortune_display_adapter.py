#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大运流年流月适配器 - 用于7个前端接口的格式转换
确保响应格式完全一致，接口层完全不动
"""

from typing import Dict, Any, Optional
from server.models.bazi_detail import BaziDetailModel
from server.adapters.dayun_adapter import DayunAdapter
from server.adapters.liunian_adapter import LiunianAdapter
from datetime import datetime


class FortuneDisplayAdapter:
    """大运流年流月适配器 - 用于7个前端接口的格式转换"""
    
    @staticmethod
    def to_legacy_format(fortune_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将统一数据服务返回的数据转换为旧格式（用于7个前端接口）
        确保响应格式完全一致，接口层完全不动
        
        Args:
            fortune_data: 统一数据服务返回的数据（BaziDisplayService.get_fortune_display 的返回格式）
            
        Returns:
            Dict[str, Any]: 旧格式的数据（与重构前完全一致）
        """
        # 直接返回，因为 BaziDisplayService.get_fortune_display 已经返回旧格式
        # 这个适配器主要用于未来可能的格式转换需求
        return fortune_data
    
    @staticmethod
    def from_model(fortune_data: BaziDetailModel, 
                   formatted_pillars: Optional[Dict[str, Any]] = None,
                   current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        从 BaziDetailModel 转换为旧格式（用于7个前端接口）
        
        Args:
            fortune_data: 完整八字详细数据模型
            formatted_pillars: 格式化后的四柱数据（可选）
            current_time: 当前时间（可选）
            
        Returns:
            Dict[str, Any]: 旧格式的数据（与 BaziDisplayService.get_fortune_display 格式一致）
        """
        # 格式化大运列表
        formatted_dayun_list = []
        for dayun in fortune_data.dayun_sequence:
            formatted = DayunAdapter.to_legacy_format(dayun)
            if fortune_data.current_dayun and dayun.step == fortune_data.current_dayun.step:
                formatted['is_current'] = True
            formatted_dayun_list.append(formatted)
        
        # 格式化流年列表
        formatted_liunian_list = []
        for liunian in fortune_data.liunian_sequence:
            formatted = LiunianAdapter.to_legacy_format(liunian)
            if fortune_data.current_liunian and liunian.year == fortune_data.current_liunian.year:
                formatted['is_current'] = True
            formatted_liunian_list.append(formatted)
        
        # 格式化流月列表（从当前流年获取）
        formatted_liuyue_list = []
        target_year_for_liuyue = None
        if fortune_data.current_liunian and fortune_data.current_liunian.liuyue_sequence:
            target_year_for_liuyue = fortune_data.current_liunian.year
            current_month = datetime.now().month if not current_time else current_time.month
            for liuyue in fortune_data.current_liunian.liuyue_sequence:
                formatted = FortuneDisplayAdapter._format_liuyue_item(liuyue)
                if isinstance(liuyue, dict) and liuyue.get('month') == current_month:
                    formatted['is_current'] = True
                formatted_liuyue_list.append(formatted)
        
        # 构建响应数据
        result = {
            "success": True,
            "pillars": formatted_pillars or {},
            "dayun": {
                "current": DayunAdapter.to_legacy_format(fortune_data.current_dayun) if fortune_data.current_dayun else {},
                "list": formatted_dayun_list,
                "qiyun": {
                    "date": fortune_data.qiyun.get('date', '') if fortune_data.qiyun else '',
                    "age_display": fortune_data.qiyun.get('age_display', '') if fortune_data.qiyun else '',
                    "description": fortune_data.qiyun.get('description', '') if fortune_data.qiyun else ''
                },
                "jiaoyun": {
                    "date": fortune_data.jiaoyun.get('date', '') if fortune_data.jiaoyun else '',
                    "age_display": fortune_data.jiaoyun.get('age_display', '') if fortune_data.jiaoyun else '',
                    "description": fortune_data.jiaoyun.get('description', '') if fortune_data.jiaoyun else ''
                }
            },
            "liunian": {
                "current": LiunianAdapter.to_legacy_format(fortune_data.current_liunian) if fortune_data.current_liunian else None,
                "list": formatted_liunian_list
            },
            "liuyue": {
                "current": formatted_liuyue_list[0] if formatted_liuyue_list else {},
                "list": formatted_liuyue_list,
                "target_year": target_year_for_liuyue
            },
            "details": {
                "dayun_sequence": [DayunAdapter.to_dict(dayun) for dayun in fortune_data.dayun_sequence]
            }
        }
        
        return result
    
    @staticmethod
    def _format_liuyue_item(liuyue: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化单个流月项（与 BaziDisplayService._format_liuyue_item 格式一致）
        
        Args:
            liuyue: 流月数据（字典格式）
            
        Returns:
            Dict[str, Any]: 格式化后的流月数据
        """
        from src.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
        
        stem = liuyue.get('stem', '')
        branch = liuyue.get('branch', '')
        ganzhi = stem + branch if stem and branch else ''
        
        return {
            "month": liuyue.get('month', 0),
            "solar_term": liuyue.get('solar_term', ''),
            "term_date": liuyue.get('term_date', ''),
            "ganzhi": ganzhi,
            "stem": {
                "char": stem,
                "wuxing": STEM_ELEMENTS.get(stem, '')
            },
            "branch": {
                "char": branch,
                "wuxing": BRANCH_ELEMENTS.get(branch, '')
            },
            "nayin": liuyue.get('nayin', ''),
            "is_current": False  # 由调用方设置
        }

