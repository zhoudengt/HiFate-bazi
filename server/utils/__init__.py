# -*- coding: utf-8 -*-
"""
服务器工具模块
"""

from .cache import bazi_cache, BaziCache

# 统一日志系统
try:
    from .unified_logger import (
        get_unified_logger,
        log_request,
        log_response,
        log_error,
        log_function,
        trace_function,
        LogLevel
    )
    UNIFIED_LOGGER_AVAILABLE = True
except ImportError:
    UNIFIED_LOGGER_AVAILABLE = False

# 敏感信息管理
try:
    from .secret_manager import (
        get_secret_manager,
        get_coze_token,
        get_coze_bot_id,
        get_mysql_password,
        get_jwt_secret
    )
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False

# SQL 安全防护
try:
    from .sql_security import (
        secure_execute_query,
        secure_execute_update,
        SecureSQLExecutor,
        SQLSecurityChecker
    )
    SQL_SECURITY_AVAILABLE = True
except ImportError:
    SQL_SECURITY_AVAILABLE = False

__all__ = [
    'bazi_cache', 'BaziCache',
]

if UNIFIED_LOGGER_AVAILABLE:
    __all__.extend([
        'get_unified_logger',
        'log_request',
        'log_response',
        'log_error',
        'log_function',
        'trace_function',
        'LogLevel'
    ])

if SECRET_MANAGER_AVAILABLE:
    __all__.extend([
        'get_secret_manager',
        'get_coze_token',
        'get_coze_bot_id',
        'get_mysql_password',
        'get_jwt_secret'
    ])

if SQL_SECURITY_AVAILABLE:
    __all__.extend([
        'secure_execute_query',
        'secure_execute_update',
        'SecureSQLExecutor',
        'SQLSecurityChecker'
    ])








































