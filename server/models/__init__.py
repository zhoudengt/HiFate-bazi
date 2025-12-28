#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字数据模型 - 统一的数据结构定义
"""

from server.models.dayun import DayunModel
from server.models.liunian import LiunianModel
from server.models.special_liunian import SpecialLiunianModel
from server.models.bazi_detail import BaziDetailModel

__all__ = [
    'DayunModel',
    'LiunianModel',
    'SpecialLiunianModel',
    'BaziDetailModel',
]

