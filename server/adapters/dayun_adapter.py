#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大运数据适配器 - 统一的数据格式转换
"""

from typing import Dict, Any, List
from server.models.dayun import DayunModel


class DayunAdapter:
    """大运数据适配器 - 统一的数据格式转换"""
    
    @staticmethod
    def to_dict(dayun: DayunModel) -> Dict[str, Any]:
        """
        将 DayunModel 转换为字典格式（旧格式）
        
        Args:
            dayun: 大运模型
            
        Returns:
            Dict[str, Any]: 字典格式的大运数据
        """
        return {
            "step": dayun.step,
            "stem": dayun.stem,
            "branch": dayun.branch,
            "ganzhi": dayun.ganzhi,
            "year_start": dayun.year_start,
            "year_end": dayun.year_end,
            "age_range": dayun.age_range,
            "age_display": dayun.age_display,
            "nayin": dayun.nayin,
            "main_star": dayun.main_star,
            "hidden_stems": dayun.hidden_stems or [],
            "hidden_stars": dayun.hidden_stars or [],
            "star_fortune": dayun.star_fortune,
            "self_sitting": dayun.self_sitting,
            "kongwang": dayun.kongwang,
            "deities": dayun.deities or [],
            "details": dayun.details or {}
        }
    
    @staticmethod
    def to_legacy_format(dayun: DayunModel) -> Dict[str, Any]:
        """
        将 DayunModel 转换为旧格式（用于7个前端接口）
        
        Args:
            dayun: 大运模型
            
        Returns:
            Dict[str, Any]: 旧格式的大运数据（与 BaziDisplayService._format_dayun_item 格式一致）
        """
        from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
        
        return {
            "index": dayun.step,
            "ganzhi": dayun.ganzhi,
            "stem": {
                "char": dayun.stem,
                "wuxing": STEM_ELEMENTS.get(dayun.stem, '')
            },
            "branch": {
                "char": dayun.branch,
                "wuxing": BRANCH_ELEMENTS.get(dayun.branch, '')
            },
            "age_range": dayun.age_range or {"start": 0, "end": 0},
            "age_display": dayun.age_display or "",
            "year_range": {
                "start": dayun.year_start or 0,
                "end": dayun.year_end or 0
            },
            "nayin": dayun.nayin or "",
            "main_star": dayun.main_star or "",
            "hidden_stems": dayun.hidden_stems or [],
            "hidden_stars": dayun.hidden_stars or [],
            "star_fortune": dayun.star_fortune or "",
            "self_sitting": dayun.self_sitting or "",
            "kongwang": dayun.kongwang or "",
            "deities": dayun.deities or [],
            "is_current": False  # 由调用方设置
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> DayunModel:
        """
        从字典格式创建 DayunModel
        
        Args:
            data: 字典格式的大运数据
            
        Returns:
            DayunModel: 大运模型
        """
        return DayunModel(
            step=data.get('step', 0),
            stem=data.get('stem', ''),
            branch=data.get('branch', ''),
            ganzhi=data.get('ganzhi', f"{data.get('stem', '')}{data.get('branch', '')}"),
            year_start=data.get('year_start'),
            year_end=data.get('year_end'),
            age_range=data.get('age_range'),
            age_display=data.get('age_display'),
            nayin=data.get('nayin'),
            main_star=data.get('main_star'),
            hidden_stems=data.get('hidden_stems', []),
            hidden_stars=data.get('hidden_stars', []),
            star_fortune=data.get('star_fortune'),
            self_sitting=data.get('self_sitting'),
            kongwang=data.get('kongwang'),
            deities=data.get('deities', []),
            details=data.get('details', {})
        )

