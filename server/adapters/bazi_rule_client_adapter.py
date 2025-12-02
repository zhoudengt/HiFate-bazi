#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则客户端适配器
将现有的 BaziRuleClient 适配为接口实现
"""

import sys
import os
from typing import Dict, Any, Optional, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.interfaces.bazi_rule_client_interface import IBaziRuleClient


class BaziRuleClientAdapter(IBaziRuleClient):
    """规则客户端适配器（实现接口）"""
    
    def __init__(self, base_url: str, timeout: float = 60.0):
        """
        初始化适配器
        
        Args:
            base_url: 服务地址
            timeout: 超时时间
        """
        # 延迟导入，避免导入时依赖 gRPC
        from src.clients.bazi_rule_client_grpc import BaziRuleClient as GrpcBaziRuleClient
        self._client = GrpcBaziRuleClient(base_url=base_url, timeout=timeout)
    
    def match_rules(self, 
                   solar_date: str, 
                   solar_time: str, 
                   gender: str,
                   rule_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """匹配规则（实现接口）"""
        return self._client.match_rules(solar_date, solar_time, gender, rule_types)

