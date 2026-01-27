#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压力测试任务模块
"""

from .bazi_tasks import BaziTasks
from .fortune_tasks import FortuneTasks
from .health_tasks import HealthTasks

__all__ = ["BaziTasks", "FortuneTasks", "HealthTasks"]
