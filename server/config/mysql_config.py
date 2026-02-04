#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 配置模块 - 兼容层

⚠️ 重要说明：
这是一个兼容层，所有功能已迁移到 shared/config/database.py。
新代码请直接使用：from shared.config.database import ...
此文件保留用于向后兼容现有代码。
"""

import logging

logger = logging.getLogger(__name__)

# ============================================================
# 从 shared/config/database 导入所有功能
# ============================================================

from shared.config.database import (
    # 环境检测函数
    get_current_env,
    is_local_dev,
    is_production,
    is_staging,
    IS_LOCAL_DEV,
    IS_PRODUCTION,
    IS_STAGING,
    
    # MySQL 配置
    mysql_config,
    MYSQL_POOL_CONFIG,
    
    # 连接池类
    MySQLConnectionPool,
    
    # 连接管理函数
    get_mysql_connection,
    return_mysql_connection,
    cleanup_idle_mysql_connections,
    get_connection_pool_stats,
    test_mysql_connection,
    refresh_connection_pool,
    
    # SQL 执行函数
    execute_query,
    execute_update,
)

# ============================================================
# 兼容性：保留原有的全局变量和函数名
# ============================================================

# 为了兼容性，也导出这些（重复导出，确保向后兼容）
__all__ = [
    # 环境检测
    'get_current_env',
    'is_local_dev',
    'is_production',
    'is_staging',
    'IS_LOCAL_DEV',
    'IS_PRODUCTION',
    'IS_STAGING',
    
    # 配置
    'mysql_config',
    'MYSQL_POOL_CONFIG',
    
    # 连接池
    'MySQLConnectionPool',
    
    # 连接管理
    'get_mysql_connection',
    'return_mysql_connection',
    'cleanup_idle_mysql_connections',
    'get_connection_pool_stats',
    'test_mysql_connection',
    'refresh_connection_pool',
    
    # SQL 执行
    'execute_query',
    'execute_update',
]

# ============================================================
# 兼容性说明：
# - 原有的 from server.config.env_config import ... 依赖已移除
# - 环境检测逻辑已内置到 shared/config/database.py
# - 所有 API 保持不变，现有代码无需修改
# ============================================================

logger.debug("✓ MySQL 配置模块已加载（兼容层 -> shared/config/database）")
