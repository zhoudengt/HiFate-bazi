#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility shim for legacy imports.

Historically `src/tool/BaziCalculator.py`定义了 `BaziCalculator` 类。
在微服务拆分过程中，统一使用 `src/bazi_calculator.WenZhenBazi`
作为实际实现。此文件仅保留向后兼容的导出，避免修改大量调用方。
"""

from core.calculators.bazi_calculator import WenZhenBazi as BaziCalculator  # noqa: F401

__all__ = ["BaziCalculator"]
