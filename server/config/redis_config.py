#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 配置模块 - 兼容层

⚠️ 重要说明：
这是一个兼容层，所有功能已迁移到 shared/config/redis.py。
新代码请直接使用：from shared.config.redis import ...
此文件保留用于向后兼容现有代码。
"""

import logging

logger = logging.getLogger(__name__)

# ============================================================
# 从 shared/config/redis 导入所有功能
# ============================================================

from shared.config.redis import (
    # 配置
    REDIS_CONFIG,
    
    # 全局变量
    redis_pool,
    redis_client,
    
    # 初始化函数
    init_redis,
    
    # 客户端获取函数
    get_redis_client,
    get_redis_pool,
    get_redis_client_with_retry,
    
    # 健康检查
    check_redis_health,
    
    # 统计信息
    get_redis_pool_stats,
    
    # 刷新连接
    refresh_redis_connection,
)

# ============================================================
# 兼容性：保留原有的全局变量和函数名
# ============================================================

__all__ = [
    # 配置
    'REDIS_CONFIG',
    
    # 全局变量
    'redis_pool',
    'redis_client',
    
    # 函数
    'init_redis',
    'get_redis_client',
    'get_redis_pool',
    'get_redis_client_with_retry',
    'check_redis_health',
    'get_redis_pool_stats',
    'refresh_redis_connection',
]

# ============================================================
# 兼容性说明：
# - 所有功能已迁移到 shared/config/redis.py
# - 所有 API 保持不变，现有代码无需修改
# ============================================================

logger.debug("✓ Redis 配置模块已加载（兼容层 -> shared/config/redis）")
