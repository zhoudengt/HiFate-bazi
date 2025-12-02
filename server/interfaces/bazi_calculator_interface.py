#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字计算器接口
定义本地八字计算的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IBaziCalculator(ABC):
    """八字计算器接口"""
    
    @abstractmethod
    def calculate(self) -> Dict[str, Any]:
        """
        计算八字
        
        Returns:
            dict: 八字计算结果
        """
        pass

