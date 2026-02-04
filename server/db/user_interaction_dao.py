#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户交互数据访问层 - MySQL
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from shared.config.database import get_mysql_connection, return_mysql_connection
from server.config.database_config import MYSQL_CONFIG

logger = logging.getLogger(__name__)


class UserInteractionDAO:
    """用户交互数据访问对象（MySQL）"""
    
    @staticmethod
    def save_record(
        record_id: str,
        user_id: str,
        session_id: Optional[str],
        function_type: str,
        function_name: str,
        frontend_api: str,
        llm_api: Optional[str],
        round_number: int,
        frontend_input_summary: str,
        input_data_summary: str,
        llm_output_summary: str,
        mongo_doc_id: Optional[str],
        api_response_time_ms: Optional[int],
        llm_first_token_time_ms: Optional[int],
        llm_total_time_ms: Optional[int],
        token_count: Optional[int],
        model_name: Optional[str],
        model_version: Optional[str],
        bot_id: Optional[str],
        status: str = 'success',
        error_message: Optional[str] = None
    ) -> bool:
        """
        保存功能使用记录到MySQL
        
        Returns:
            bool: 是否保存成功
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO function_usage_records (
                        record_id, user_id, session_id, function_type, function_name,
                        frontend_api, llm_api, round_number,
                        frontend_input_summary, input_data_summary, llm_output_summary,
                        mongo_doc_id,
                        api_response_time_ms, llm_first_token_time_ms, llm_total_time_ms,
                        token_count, model_name, model_version, bot_id,
                        status, error_message
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s
                    )
                """
                cursor.execute(sql, (
                    record_id, user_id, session_id, function_type, function_name,
                    frontend_api, llm_api, round_number,
                    frontend_input_summary, input_data_summary, llm_output_summary,
                    mongo_doc_id,
                    api_response_time_ms, llm_first_token_time_ms, llm_total_time_ms,
                    token_count, model_name, model_version, bot_id,
                    status, error_message
                ))
                conn.commit()
                logger.debug(f"[UserInteractionDAO] 记录保存成功: record_id={record_id}")
                return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"[UserInteractionDAO] 保存记录失败: {e}", exc_info=True)
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def get_record_by_id(record_id: str) -> Optional[Dict[str, Any]]:
        """根据记录ID获取记录"""
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = "SELECT * FROM function_usage_records WHERE record_id = %s"
                cursor.execute(sql, (record_id,))
                result = cursor.fetchone()
                return result
        except Exception as e:
            logger.error(f"[UserInteractionDAO] 获取记录失败: {e}", exc_info=True)
            return None
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def get_records_by_user(user_id: str, limit: int = 100) -> list:
        """根据用户ID获取记录列表"""
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT * FROM function_usage_records 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                cursor.execute(sql, (user_id, limit))
                results = cursor.fetchall()
                return results
        except Exception as e:
            logger.error(f"[UserInteractionDAO] 获取用户记录失败: {e}", exc_info=True)
            return []
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def get_records_by_function(function_type: str, limit: int = 100) -> list:
        """根据功能类型获取记录列表"""
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT * FROM function_usage_records 
                    WHERE function_type = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                cursor.execute(sql, (function_type, limit))
                results = cursor.fetchall()
                return results
        except Exception as e:
            logger.error(f"[UserInteractionDAO] 获取功能记录失败: {e}", exc_info=True)
            return []
        finally:
            if conn:
                return_mysql_connection(conn)

