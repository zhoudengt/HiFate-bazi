#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字计算服务层 V2 - 改进版
使用依赖注入和接口抽象，降低耦合度
"""

import logging
import sys
import os
from typing import Optional, Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.interfaces.bazi_core_client_interface import IBaziCoreClient
from server.interfaces.bazi_calculator_interface import IBaziCalculator
from server.config.app_config import get_config

logger = logging.getLogger(__name__)


class BaziServiceV2:
    """八字计算服务类 V2（改进版：使用依赖注入）"""
    
    def __init__(self,
                 core_client: Optional[IBaziCoreClient] = None,
                 calculator_factory=None):
        """
        初始化服务（依赖注入）
        
        Args:
            core_client: 八字核心客户端（接口，可选）
            calculator_factory: 计算器工厂函数（可选）
        """
        self._core_client = core_client
        self._calculator_factory = calculator_factory or self._default_calculator_factory
        self._config = get_config()
    
    @staticmethod
    def _default_calculator_factory(solar_date: str, solar_time: str, gender: str) -> IBaziCalculator:
        """默认计算器工厂"""
        # 延迟导入
        from server.adapters.bazi_calculator_adapter import BaziCalculatorAdapter
        return BaziCalculatorAdapter(solar_date, solar_time, gender)
    
    def calculate_bazi_full(self, solar_date: str, solar_time: str, gender: str) -> dict:
        """
        完整计算八字信息（改进版）
        
        Args:
            solar_date: 阳历日期，格式：YYYY-MM-DD
            solar_time: 出生时间，格式：HH:MM
            gender: 性别，'male' 或 'female'
        
        Returns:
            dict: 格式化的八字数据
        """
        bazi_result = None
        
        # 1. 优先尝试调用远程服务（如果配置了客户端）
        if self._core_client:
            try:
                bazi_result = self._core_client.calculate_bazi(solar_date, solar_time, gender)
                logger.debug("BaziServiceV2 使用远程服务计算八字")
            except Exception as exc:
                if self._config.services.bazi_core_strict:
                    raise
                logger.debug(f"远程服务调用失败，回退到本地计算: {exc}")
        
        # 2. 如果未调用远程或失败，使用本地计算
        if bazi_result is None:
            calculator = self._calculator_factory(solar_date, solar_time, gender)
            bazi_result = calculator.calculate()
        else:
            # 补充缺失字段（使用本地计算）
            try:
                from core.calculators.BaziCalculator import BaziCalculator
                local_calc = BaziCalculator(solar_date, solar_time, gender)
                local_calc._calculate_with_lunar()
                local_calc._calculate_ten_gods()
                local_calc._calculate_hidden_stems()
                local_calc._calculate_star_fortune()
                
                local_details = local_calc.details
                remote_details = bazi_result.get('details', {})
                
                for pillar_type in ['year', 'month', 'day', 'hour']:
                    if pillar_type in remote_details and pillar_type in local_details:
                        if not remote_details[pillar_type].get('hidden_stems'):
                            remote_details[pillar_type]['hidden_stems'] = local_details[pillar_type].get('hidden_stems', [])
                        if not remote_details[pillar_type].get('hidden_stars'):
                            remote_details[pillar_type]['hidden_stars'] = local_details[pillar_type].get('hidden_stars', [])
                        if not remote_details[pillar_type].get('star_fortune'):
                            remote_details[pillar_type]['star_fortune'] = local_details[pillar_type].get('star_fortune', '')
                        if not remote_details[pillar_type].get('self_sitting'):
                            remote_details[pillar_type]['self_sitting'] = local_details[pillar_type].get('self_sitting', '')
            except Exception as e:
                logger.warning(f"本地计算补充字段失败: {e}")
        
        if not bazi_result:
            raise ValueError("八字计算失败，请检查输入参数")
        
        # 3. 获取日柱
        bazi_pillars = bazi_result.get('bazi_pillars', {})
        if not isinstance(bazi_pillars, dict):
            raise TypeError(f"bazi_result['bazi_pillars'] 必须是字典类型，但实际是: {type(bazi_pillars)}")
        
        day_pillar = bazi_pillars.get('day', {})
        if not isinstance(day_pillar, dict):
            raise TypeError(f"bazi_result['bazi_pillars']['day'] 必须是字典类型，但实际是: {type(day_pillar)}")
        
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        rizhu = f"{day_stem}{day_branch}"
        
        # 4. 格式化输出（复用原有格式化逻辑）
        from server.services.bazi_service import BaziService
        return {
            "bazi": BaziService._format_bazi_result(bazi_result),
            "rizhu": rizhu,
            "matched_rules": []
        }
    
    @classmethod
    def create_default(cls) -> 'BaziServiceV2':
        """
        创建默认服务实例（工厂方法）
        自动根据配置创建客户端
        """
        config = get_config()
        core_client = None
        
        # 如果配置了远程服务，创建客户端（延迟导入）
        if config.services.bazi_core_url:
            from server.adapters.bazi_core_client_adapter import BaziCoreClientAdapter
            core_client = BaziCoreClientAdapter(
                base_url=config.services.bazi_core_url,
                timeout=30.0
            )
        
        return cls(core_client=core_client)

