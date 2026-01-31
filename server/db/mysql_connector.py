#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 连接器模块
"""

import pymysql
import logging

logger = logging.getLogger(__name__)
from pymysql.cursors import DictCursor
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

from server.config.mysql_config import mysql_config, get_mysql_connection, return_mysql_connection


class MySQLConnector:
    """MySQL 数据库连接器（支持连接池）"""
    
    def __init__(self):
        self.config = mysql_config
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器，支持连接池）"""
        conn = get_mysql_connection()
        try:
            yield conn
        finally:
            # 使用连接池时，返回到池中；否则关闭连接
            return_mysql_connection(conn)
    
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        执行查询语句
        
        Args:
            sql: SQL 语句
            params: 参数元组
            
        Returns:
            list: 查询结果（字典列表）
        """
        with self.get_connection() as conn:
            # 对于只读查询，启用autocommit并设置READ COMMITTED隔离级别，避免表元数据锁
            if sql.strip().upper().startswith('SELECT'):
                conn.autocommit(True)
                with conn.cursor() as cursor:
                    cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                
                # 只读查询立即提交，释放表元数据锁
                if sql.strip().upper().startswith('SELECT'):
                    conn.commit()
                
                return result
    
    def execute_update(self, sql: str, params: tuple = None) -> int:
        """
        执行更新语句
        
        Args:
            sql: SQL 语句
            params: 参数元组
            
        Returns:
            int: 影响的行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                conn.commit()
                return affected
    
    def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行语句
        
        Args:
            sql: SQL 语句
            params_list: 参数列表
            
        Returns:
            int: 影响的行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected = cursor.executemany(sql, params_list)
                conn.commit()
                return affected
    
    def create_database_if_not_exists(self, database_name: str = None):
        """创建数据库（如果不存在）"""
        db_name = database_name or self.config['database']
        
        # 临时使用不指定数据库的连接
        temp_config = self.config.copy()
        temp_config.pop('database', None)
        
        conn = pymysql.connect(**temp_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                conn.commit()
                logger.info(f"✓ 数据库 {db_name} 创建成功或已存在")
        finally:
            conn.close()


def get_db_connection():
    """获取数据库连接器实例"""
    return MySQLConnector()








































