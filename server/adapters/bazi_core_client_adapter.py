#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字核心客户端适配器
将现有的 BaziCoreClient 适配为接口实现
"""

import sys
import os
from typing import Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.interfaces.bazi_core_client_interface import IBaziCoreClient


class BaziCoreClientAdapter(IBaziCoreClient):
    """八字核心客户端适配器（实现接口）"""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        初始化适配器
        
        Args:
            base_url: 服务地址
            timeout: 超时时间
        """
        # 延迟导入，避免导入时依赖 gRPC
        from src.clients.bazi_core_client_grpc import BaziCoreClient as GrpcBaziCoreClient
        self._client = GrpcBaziCoreClient(base_url=base_url, timeout=timeout)
    
    def calculate_bazi(self, solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        """计算八字（实现接口）"""
        return self._client.calculate_bazi(solar_date, solar_time, gender)

