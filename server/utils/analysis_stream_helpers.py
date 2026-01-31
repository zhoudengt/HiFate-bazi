# -*- coding: utf-8 -*-
"""
分析流式接口共用逻辑 - 统一数据获取

【已迁移】配置已迁移到 server/orchestrators/modules_config.py
本文件保留作为兼容层，转发到新位置

marriage/health/children/career_wealth 主路径通过 BaziDataOrchestrator 获取数据
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# 已迁移：从 modules_config.py 导入
# ============================================================================

from server.orchestrators.modules_config import (
    STREAM_MODULES as STREAM_ANALYSIS_MODULES,
    get_modules_config
)
