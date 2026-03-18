#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命理推理引擎包

在计算层（排盘/旺衰/十神/神煞）与LLM之间插入确定性推理层。
推理引擎从计算结果出发，通过规则化因果链条推导出具体结论，
LLM只负责将推理结论写成自然语言。
"""

from core.inference.models import InferenceInput, CausalChain, InferenceResult
from core.inference.base_engine import BaseInferenceEngine

__all__ = [
    'InferenceInput',
    'CausalChain',
    'InferenceResult',
    'BaseInferenceEngine',
]
