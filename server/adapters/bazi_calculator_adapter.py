#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字计算器适配器
将现有的 BaziCalculator 适配为接口实现
"""

import sys
import os
from typing import Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.interfaces.bazi_calculator_interface import IBaziCalculator
from core.calculators.BaziCalculator import BaziCalculator as LocalBaziCalculator


class BaziCalculatorAdapter(IBaziCalculator):
    """八字计算器适配器（实现接口）"""
    
    def __init__(self, solar_date: str, solar_time: str, gender: str):
        """
        初始化适配器
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
        """
        self._calculator = LocalBaziCalculator(solar_date, solar_time, gender)
    
    def calculate(self) -> Dict[str, Any]:
        """计算八字（实现接口）"""
        return self._calculator.calculate()

