#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五行生克关系模块

提供五行生克关系的常量定义和计算函数。
"""

from typing import Literal

# 五行关系类型
RelationType = Literal['same', 'me_producing', 'me_controlling', 'producing_me', 'controlling_me', 'unknown']

# 五行生克关系定义
ELEMENT_RELATIONS = {
    '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
    '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
    '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
    '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
    '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
}


def get_element_relation(day_element: str, target_element: str) -> RelationType:
    """
    判断五行生克关系
    
    Args:
        day_element: 日主五行（木/火/土/金/水）
        target_element: 目标五行
        
    Returns:
        RelationType: 关系类型
        - 'same': 同元素
        - 'me_producing': 我生
        - 'me_controlling': 我克
        - 'producing_me': 生我
        - 'controlling_me': 克我
        - 'unknown': 未知
    """
    if day_element == target_element:
        return 'same'

    if day_element not in ELEMENT_RELATIONS:
        return 'unknown'
    
    relations = ELEMENT_RELATIONS[day_element]

    if target_element == relations['produces']:
        return 'me_producing'
    elif target_element == relations['controls']:
        return 'me_controlling'
    elif target_element == relations['produced_by']:
        return 'producing_me'
    elif target_element == relations['controlled_by']:
        return 'controlling_me'

    return 'unknown'


def get_producing_element(element: str) -> str:
    """获取被生的元素"""
    return ELEMENT_RELATIONS.get(element, {}).get('produces', '')


def get_controlled_element(element: str) -> str:
    """获取被克的元素"""
    return ELEMENT_RELATIONS.get(element, {}).get('controls', '')


def get_producing_from_element(element: str) -> str:
    """获取生我的元素"""
    return ELEMENT_RELATIONS.get(element, {}).get('produced_by', '')


def get_controlled_by_element(element: str) -> str:
    """获取克我的元素"""
    return ELEMENT_RELATIONS.get(element, {}).get('controlled_by', '')
