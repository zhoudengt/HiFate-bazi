#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据格式适配器 - 统一的数据格式转换
"""

from server.adapters.dayun_adapter import DayunAdapter
from server.adapters.liunian_adapter import LiunianAdapter
from server.adapters.special_liunian_adapter import SpecialLiunianAdapter
from server.adapters.fortune_display_adapter import FortuneDisplayAdapter

__all__ = [
    'DayunAdapter',
    'LiunianAdapter',
    'SpecialLiunianAdapter',
    'FortuneDisplayAdapter',
]

