# src/tool/__init__.py
"""
八字计算工具包
包含八字计算器、农历转换器和详细打印器
"""

from .BaziCalculator import BaziCalculator
from .LunarConverter import LunarConverter

__all__ = ['BaziCalculator', 'LunarConverter', 'BaziDetailPrinter']


def __getattr__(name):
    if name == 'BaziDetailPrinter':
        from .BaziDetailPrinter import BaziDetailPrinter  # pylint: disable=import-outside-toplevel
        return BaziDetailPrinter
    raise AttributeError(f"module 'src.tool' has no attribute '{name}'")