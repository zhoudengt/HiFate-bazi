#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL 安全防护系统
要求：所有 SQL 查询必须使用参数化查询，禁止直接拼接 SQL
"""

import re
import sys
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 延迟导入，避免循环导入
def _get_logger():
    from server.utils.unified_logger import get_unified_logger
    return get_unified_logger()


class SQLSecurityChecker:
    """
    SQL 安全检查器
    检测可能的 SQL 注入漏洞
    """
    
    # SQL 注入危险模式
    DANGEROUS_PATTERNS = [
        r';\s*(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)',
        r'--\s*',
        r'/\*.*?\*/',
        r"'.*?'.*?OR.*?'.*?'",
        r'UNION.*?SELECT',
        r"OR\s+1\s*=\s*1",
        r"AND\s+1\s*=\s*1",
    ]
    
    @classmethod
    def check_sql_string(cls, sql: str) -> Tuple[bool, Optional[str]]:
        """
        检查 SQL 字符串是否包含危险模式
        
        Args:
            sql: SQL 字符串
            
        Returns:
            (is_safe, warning_message)
        """
        sql_upper = sql.upper()
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                warning = f"检测到潜在的 SQL 注入模式: {pattern}"
                logger = _get_logger()
                from server.utils.unified_logger import LogLevel
                logger.log_function(
                    'SQLSecurityChecker',
                    'check_sql_string',
                    warning,
                    input_data={'sql': sql[:200]},  # 只记录前200字符
                    level=LogLevel.WARNING
                )
                return False, warning
        
        return True, None
    
    @classmethod
    def check_params(cls, sql: str, params: Optional[Union[Tuple, Dict, List]]) -> Tuple[bool, Optional[str]]:
        """
        检查 SQL 参数是否正确使用
        
        Args:
            sql: SQL 字符串
            params: SQL 参数
            
        Returns:
            (is_safe, warning_message)
        """
        # 检查是否使用参数化查询
        if params is None or (isinstance(params, (tuple, list, dict)) and len(params) == 0):
            # 检查 SQL 中是否直接拼接了变量
            if re.search(r'%s|%d|%f|%\(', sql):
                warning = "SQL 字符串包含格式化占位符，但未提供参数，可能存在 SQL 注入风险"
                logger = _get_logger()
                from server.utils.unified_logger import LogLevel
                logger.log_function(
                    'SQLSecurityChecker',
                    'check_params',
                    warning,
                    input_data={'sql': sql[:200]},
                    level=LogLevel.WARNING
                )
                return False, warning
        
        # 检查参数值中是否包含危险内容
        if params:
            params_list = []
            if isinstance(params, dict):
                params_list = list(params.values())
            elif isinstance(params, (tuple, list)):
                params_list = list(params)
            
            for param in params_list:
                if isinstance(param, str):
                    for pattern in cls.DANGEROUS_PATTERNS:
                        if re.search(pattern, param, re.IGNORECASE):
                            warning = f"参数值包含潜在的 SQL 注入模式: {pattern}"
                            logger = _get_logger()
                            from server.utils.unified_logger import LogLevel
                            logger.log_function(
                                'SQLSecurityChecker',
                                'check_params',
                                warning,
                                input_data={'sql': sql[:200], 'param': param[:100]},
                                level=LogLevel.WARNING
                            )
                            return False, warning
        
        return True, None


class SecureSQLExecutor:
    """
    安全 SQL 执行器
    包装数据库操作，确保使用参数化查询
    """
    
    def __init__(self, connection):
        """
        初始化安全 SQL 执行器
        
        Args:
            connection: 数据库连接对象
        """
        self.connection = connection
        self.checker = SQLSecurityChecker()
    
    def execute_query(self,
                     sql: str,
                     params: Optional[Union[Tuple, Dict, List]] = None,
                     request_id: Optional[str] = None,
                     service: str = 'Database',
                     function: str = 'execute_query') -> List[Dict[str, Any]]:
        """
        安全执行查询
        
        Args:
            sql: SQL 查询语句
            params: 查询参数
            request_id: 请求ID
            service: 服务名称
            function: 函数名称
            
        Returns:
            查询结果
            
        Raises:
            ValueError: 如果检测到 SQL 注入风险
        """
        import time
        start_time = time.time()
        logger = _get_logger()
        
        # 记录 SQL 执行（脱敏参数）
        logger.log_request(
            service,
            function,
            request_id=request_id,
            input_data={
                'sql': sql[:500],  # 只记录前500字符
                'params_count': len(params) if params else 0,
                'params_type': type(params).__name__ if params else None
            }
        )
        
        # 安全检查
        is_safe, warning = self.checker.check_sql_string(sql)
        if not is_safe:
            error = ValueError(f"SQL 安全检查失败: {warning}")
            logger.log_error(service, function, error, request_id=request_id)
            raise error
        
        if params:
            is_safe, warning = self.checker.check_params(sql, params)
            if not is_safe:
                error = ValueError(f"SQL 参数检查失败: {warning}")
                logger.log_error(service, function, error, request_id=request_id)
                raise error
        
        try:
            # 执行查询
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()
            cursor.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录查询结果
            logger.log_response(
                service,
                function,
                request_id=request_id,
                output_data={
                    'row_count': len(results) if results else 0,
                    'has_results': bool(results)
                },
                duration_ms=duration_ms
            )
            
            return results
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_error(
                service,
                function,
                e,
                request_id=request_id,
                input_data={'sql': sql[:200]},
                duration_ms=duration_ms
            )
            raise
    
    def execute_update(self,
                      sql: str,
                      params: Optional[Union[Tuple, Dict, List]] = None,
                      request_id: Optional[str] = None,
                      service: str = 'Database',
                      function: str = 'execute_update') -> int:
        """
        安全执行更新
        
        Args:
            sql: SQL 更新语句
            params: 更新参数
            request_id: 请求ID
            service: 服务名称
            function: 函数名称
            
        Returns:
            影响的行数
            
        Raises:
            ValueError: 如果检测到 SQL 注入风险
        """
        import time
        start_time = time.time()
        logger = _get_logger()
        
        # 记录 SQL 执行
        logger.log_request(
            service,
            function,
            request_id=request_id,
            input_data={
                'sql': sql[:500],
                'params_count': len(params) if params else 0
            }
        )
        
        # 安全检查
        is_safe, warning = self.checker.check_sql_string(sql)
        if not is_safe:
            error = ValueError(f"SQL 安全检查失败: {warning}")
            logger.log_error(service, function, error, request_id=request_id)
            raise error
        
        if params:
            is_safe, warning = self.checker.check_params(sql, params)
            if not is_safe:
                error = ValueError(f"SQL 参数检查失败: {warning}")
                logger.log_error(service, function, error, request_id=request_id)
                raise error
        
        try:
            # 执行更新
            cursor = self.connection.cursor()
            affected = cursor.execute(sql, params)
            self.connection.commit()
            cursor.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录更新结果
            logger.log_response(
                service,
                function,
                request_id=request_id,
                output_data={'affected_rows': affected},
                duration_ms=duration_ms
            )
            
            return affected
            
        except Exception as e:
            self.connection.rollback()
            duration_ms = (time.time() - start_time) * 1000
            logger.log_error(
                service,
                function,
                e,
                request_id=request_id,
                input_data={'sql': sql[:200]},
                duration_ms=duration_ms
            )
            raise


def secure_execute_query(connection,
                        sql: str,
                        params: Optional[Union[Tuple, Dict, List]] = None,
                        request_id: Optional[str] = None,
                        service: str = 'Database',
                        function: str = 'execute_query') -> List[Dict[str, Any]]:
    """
    安全执行查询（便捷函数）
    
    Args:
        connection: 数据库连接
        sql: SQL 查询语句
        params: 查询参数
        request_id: 请求ID
        service: 服务名称
        function: 函数名称
        
    Returns:
        查询结果
    """
    executor = SecureSQLExecutor(connection)
    return executor.execute_query(sql, params, request_id, service, function)


def secure_execute_update(connection,
                         sql: str,
                         params: Optional[Union[Tuple, Dict, List]] = None,
                         request_id: Optional[str] = None,
                         service: str = 'Database',
                         function: str = 'execute_update') -> int:
    """
    安全执行更新（便捷函数）
    
    Args:
        connection: 数据库连接
        sql: SQL 更新语句
        params: 更新参数
        request_id: 请求ID
        service: 服务名称
        function: 函数名称
        
    Returns:
        影响的行数
    """
    executor = SecureSQLExecutor(connection)
    return executor.execute_update(sql, params, request_id, service, function)

