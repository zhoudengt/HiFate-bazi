#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则客户端接口
定义规则匹配客户端的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class IBaziRuleClient(ABC):
    """规则客户端接口"""
    
    @abstractmethod
    def match_rules(self, 
                   solar_date: str, 
                   solar_time: str, 
                   gender: str,
                   rule_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        匹配规则
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            rule_types: 规则类型列表（可选）
        
        Returns:
            dict: 匹配的规则数据
        """
        pass

