#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流年数据适配器 - 统一的数据格式转换
"""

from typing import Dict, Any, List
from server.models.liunian import LiunianModel


class LiunianAdapter:
    """流年数据适配器 - 统一的数据格式转换"""
    
    @staticmethod
    def to_dict(liunian: LiunianModel) -> Dict[str, Any]:
        """
        将 LiunianModel 转换为字典格式（旧格式）
        
        Args:
            liunian: 流年模型
            
        Returns:
            Dict[str, Any]: 字典格式的流年数据
        """
        return {
            "year": liunian.year,
            "stem": liunian.stem,
            "branch": liunian.branch,
            "ganzhi": liunian.ganzhi,
            "age": liunian.age,
            "age_display": liunian.age_display,
            "nayin": liunian.nayin,
            "main_star": liunian.main_star,
            "hidden_stems": liunian.hidden_stems or [],
            "hidden_stars": liunian.hidden_stars or [],
            "star_fortune": liunian.star_fortune,
            "self_sitting": liunian.self_sitting,
            "kongwang": liunian.kongwang,
            "deities": liunian.deities or [],
            "relations": liunian.relations or [],
            "liuyue_sequence": liunian.liuyue_sequence or [],
            "details": liunian.details or {}
        }
    
    @staticmethod
    def to_legacy_format(liunian: LiunianModel) -> Dict[str, Any]:
        """
        将 LiunianModel 转换为旧格式（用于7个前端接口）
        
        Args:
            liunian: 流年模型
            
        Returns:
            Dict[str, Any]: 旧格式的流年数据（与 BaziDisplayService._format_liunian_item 格式一致）
        """
        from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
        
        return {
            "year": liunian.year,
            "age": liunian.age or 0,
            "age_display": liunian.age_display or "",
            "ganzhi": liunian.ganzhi,
            "stem": {
                "char": liunian.stem,
                "wuxing": STEM_ELEMENTS.get(liunian.stem, '')
            },
            "branch": {
                "char": liunian.branch,
                "wuxing": BRANCH_ELEMENTS.get(liunian.branch, '')
            },
            "nayin": liunian.nayin or "",
            "main_star": liunian.main_star or "",
            "hidden_stems": liunian.hidden_stems or [],
            "hidden_stars": liunian.hidden_stars or [],
            "star_fortune": liunian.star_fortune or "",
            "self_sitting": liunian.self_sitting or "",
            "kongwang": liunian.kongwang or "",
            "deities": liunian.deities or [],
            "relations": liunian.relations or [],
            "is_current": False  # 由调用方设置
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> LiunianModel:
        """
        从字典格式创建 LiunianModel
        
        Args:
            data: 字典格式的流年数据
            
        Returns:
            LiunianModel: 流年模型
        """
        return LiunianModel(
            year=data.get('year', 0),
            stem=data.get('stem', ''),
            branch=data.get('branch', ''),
            ganzhi=data.get('ganzhi', f"{data.get('stem', '')}{data.get('branch', '')}"),
            age=data.get('age'),
            age_display=data.get('age_display'),
            nayin=data.get('nayin'),
            main_star=data.get('main_star'),
            hidden_stems=data.get('hidden_stems', []),
            hidden_stars=data.get('hidden_stars', []),
            star_fortune=data.get('star_fortune'),
            self_sitting=data.get('self_sitting'),
            kongwang=data.get('kongwang'),
            deities=data.get('deities', []),
            relations=data.get('relations', []),
            liuyue_sequence=data.get('liuyue_sequence', []),
            details=data.get('details', {})
        )

