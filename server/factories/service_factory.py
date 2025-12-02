#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务工厂
统一创建服务实例，管理依赖关系
"""

import sys
import os
from typing import Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.app_config import get_config
from server.services.bazi_service_v2 import BaziServiceV2
from server.interfaces.bazi_core_client_interface import IBaziCoreClient
from server.interfaces.bazi_rule_client_interface import IBaziRuleClient


class ServiceFactory:
    """服务工厂类"""
    
    @staticmethod
    def create_bazi_service() -> BaziServiceV2:
        """创建八字服务实例"""
        return BaziServiceV2.create_default()
    
    @staticmethod
    def create_bazi_core_client() -> Optional[IBaziCoreClient]:
        """创建八字核心客户端"""
        config = get_config()
        if config.services.bazi_core_url:
            # 延迟导入
            from server.adapters.bazi_core_client_adapter import BaziCoreClientAdapter
            return BaziCoreClientAdapter(
                base_url=config.services.bazi_core_url,
                timeout=30.0
            )
        return None
    
    @staticmethod
    def create_bazi_rule_client() -> Optional[IBaziRuleClient]:
        """创建规则客户端"""
        config = get_config()
        if config.services.bazi_rule_url:
            # 延迟导入
            from server.adapters.bazi_rule_client_adapter import BaziRuleClientAdapter
            return BaziRuleClientAdapter(
                base_url=config.services.bazi_rule_url,
                timeout=60.0
            )
        return None

