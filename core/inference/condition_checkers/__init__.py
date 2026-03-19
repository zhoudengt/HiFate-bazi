#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条件检查函数包。

导入本包会触发所有 checker 的 @register 注册。
新增领域只需在此增加 import。
"""

from core.inference.condition_checkers import common      # noqa: F401
from core.inference.condition_checkers import marriage     # noqa: F401
