#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字核心客户端接口
定义八字计算客户端的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IBaziCoreClient(ABC):
    """八字核心客户端接口"""
    
    @abstractmethod
    def calculate_bazi(self, solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        """
        计算八字
        
        Args:
            solar_date: 阳历日期，格式：YYYY-MM-DD
            solar_time: 出生时间，格式：HH:MM
            gender: 性别，'male' 或 'female'
        
        Returns:
            dict: 八字计算结果
        """
        pass

