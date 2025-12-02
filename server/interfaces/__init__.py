# -*- coding: utf-8 -*-
"""
接口抽象层
定义服务接口，实现依赖倒置原则
"""

from .bazi_core_client_interface import IBaziCoreClient
from .bazi_rule_client_interface import IBaziRuleClient
from .bazi_fortune_client_interface import IBaziFortuneClient
from .bazi_calculator_interface import IBaziCalculator

__all__ = [
    'IBaziCoreClient',
    'IBaziRuleClient',
    'IBaziFortuneClient',
    'IBaziCalculator',
]

