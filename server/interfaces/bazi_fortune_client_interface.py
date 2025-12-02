#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运势客户端接口
定义运势计算客户端的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class IBaziFortuneClient(ABC):
    """运势客户端接口"""
    
    @abstractmethod
    def calculate_detail(self,
                        solar_date: str,
                        solar_time: str,
                        gender: str,
                        current_time: Optional[str] = None) -> Dict[str, Any]:
        """
        计算详细运势
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            current_time: 当前时间（可选）
        
        Returns:
            dict: 运势计算结果
        """
        pass

