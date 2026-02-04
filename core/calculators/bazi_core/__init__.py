#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字核心计算模块

提供八字计算的核心功能：
- 五行关系计算
- 十神计算
- 农历转换
"""

from .element_relations import (
    ELEMENT_RELATIONS,
    get_element_relation,
)
from .ten_gods import (
    get_main_star,
    get_branch_ten_gods,
    TEN_GOD_NAMES,
)

__all__ = [
    'ELEMENT_RELATIONS',
    'get_element_relation',
    'get_main_star',
    'get_branch_ten_gods',
    'TEN_GOD_NAMES',
]
