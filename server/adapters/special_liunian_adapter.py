#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特殊流年数据适配器 - 统一的数据格式转换
"""

from typing import Dict, Any, List
from server.models.special_liunian import SpecialLiunianModel
from server.adapters.liunian_adapter import LiunianAdapter


class SpecialLiunianAdapter:
    """特殊流年数据适配器 - 统一的数据格式转换"""
    
    @staticmethod
    def to_dict(special_liunian: SpecialLiunianModel) -> Dict[str, Any]:
        """
        将 SpecialLiunianModel 转换为字典格式（旧格式）
        
        Args:
            special_liunian: 特殊流年模型
            
        Returns:
            Dict[str, Any]: 字典格式的特殊流年数据
        """
        result = LiunianAdapter.to_dict(special_liunian)
        result['dayun_step'] = special_liunian.dayun_step
        result['dayun_ganzhi'] = special_liunian.dayun_ganzhi
        return result
    
    @staticmethod
    def to_legacy_format(special_liunian: SpecialLiunianModel) -> Dict[str, Any]:
        """
        将 SpecialLiunianModel 转换为旧格式（用于5个分析接口）
        
        Args:
            special_liunian: 特殊流年模型
            
        Returns:
            Dict[str, Any]: 旧格式的特殊流年数据
        """
        result = LiunianAdapter.to_legacy_format(special_liunian)
        result['dayun_step'] = special_liunian.dayun_step
        result['dayun_ganzhi'] = special_liunian.dayun_ganzhi
        return result
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> SpecialLiunianModel:
        """
        从字典格式创建 SpecialLiunianModel
        
        Args:
            data: 字典格式的特殊流年数据
            
        Returns:
            SpecialLiunianModel: 特殊流年模型
        """
        # 先创建基础流年模型
        liunian_data = data.copy()
        dayun_step = liunian_data.pop('dayun_step', None)
        dayun_ganzhi = liunian_data.pop('dayun_ganzhi', None)
        
        # 创建特殊流年模型
        return SpecialLiunianModel(
            year=liunian_data.get('year', 0),
            stem=liunian_data.get('stem', ''),
            branch=liunian_data.get('branch', ''),
            ganzhi=liunian_data.get('ganzhi', f"{liunian_data.get('stem', '')}{liunian_data.get('branch', '')}"),
            age=liunian_data.get('age'),
            age_display=liunian_data.get('age_display'),
            nayin=liunian_data.get('nayin'),
            main_star=liunian_data.get('main_star'),
            hidden_stems=liunian_data.get('hidden_stems', []),
            hidden_stars=liunian_data.get('hidden_stars', []),
            star_fortune=liunian_data.get('star_fortune'),
            self_sitting=liunian_data.get('self_sitting'),
            kongwang=liunian_data.get('kongwang'),
            deities=liunian_data.get('deities', []),
            relations=liunian_data.get('relations', []),
            liuyue_sequence=liunian_data.get('liuyue_sequence', []),
            details=liunian_data.get('details', {}),
            dayun_step=dayun_step,
            dayun_ganzhi=dayun_ganzhi
        )

