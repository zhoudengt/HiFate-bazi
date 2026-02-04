#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
十神计算模块

提供十神（主星、副星）的计算功能。
"""

from typing import List

# 从核心数据模块导入常量
from core.data.stems_branches import STEM_ELEMENTS, STEM_YINYANG, HIDDEN_STEMS

from .element_relations import get_element_relation

# 十神名称定义
TEN_GOD_NAMES = {
    'bijian': '比肩',
    'jiecai': '劫财',
    'shishen': '食神',
    'shangguan': '伤官',
    'piancai': '偏财',
    'zhengcai': '正财',
    'qisha': '七杀',
    'zhengguan': '正官',
    'pianyin': '偏印',
    'zhengyin': '正印',
}


def get_main_star(day_stem: str, target_stem: str, pillar_type: str, gender: str = 'male') -> str:
    """
    计算主星（十神）
    
    与HiFate逻辑一致
    
    Args:
        day_stem: 日干
        target_stem: 目标天干
        pillar_type: 柱类型（year/month/day/hour/hidden）
        gender: 性别
        
    Returns:
        str: 十神名称
    """
    if pillar_type == 'day':
        return '元男' if gender == 'male' else '元女'

    day_element = STEM_ELEMENTS.get(day_stem, '')
    target_element = STEM_ELEMENTS.get(target_stem, '')
    day_yinyang = STEM_YINYANG.get(day_stem, '')
    target_yinyang = STEM_YINYANG.get(target_stem, '')

    if not day_element or not target_element:
        return '未知'

    relation_type = get_element_relation(day_element, target_element)
    is_same_yinyang = (day_yinyang == target_yinyang)

    if relation_type == 'same':
        return '比肩' if is_same_yinyang else '劫财'
    elif relation_type == 'me_producing':
        return '食神' if is_same_yinyang else '伤官'
    elif relation_type == 'me_controlling':
        return '偏财' if is_same_yinyang else '正财'
    elif relation_type == 'controlling_me':
        return '七杀' if is_same_yinyang else '正官'
    elif relation_type == 'producing_me':
        return '偏印' if is_same_yinyang else '正印'

    return '未知'


def get_branch_ten_gods(day_stem: str, branch: str, gender: str = 'male') -> List[str]:
    """
    计算地支藏干的十神（副星）
    
    与HiFate逻辑一致
    
    Args:
        day_stem: 日干
        branch: 地支
        gender: 性别
        
    Returns:
        List[str]: 十神列表
    """
    hidden_stems = HIDDEN_STEMS.get(branch, [])
    branch_gods = []

    for hidden_stem in hidden_stems:
        stem_char = hidden_stem[0] if len(hidden_stem) > 0 else hidden_stem
        ten_god = get_main_star(day_stem, stem_char, 'hidden', gender)
        branch_gods.append(ten_god)

    return branch_gods
